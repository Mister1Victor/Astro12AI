import os
import re
import time
import asyncio
import aiohttp
from typing import Dict

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.enums import ChatAction, ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, MenuButtonCommands, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from langchain_core.prompts import ChatPromptTemplate
# ✅ СТАЛО (как в вашем исходном рабочем main.py):
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

from backend.logger import get_logger
from backend.config import settings
from backend.validators import validate_settings

from core.prompts.system_prompt import SYSTEM_PROMPT
from core.prompts.tarot_prompt import TAROT_SYSTEM_PROMPT
from core.rag.engine import AstroRetriever
from core.rag.context import context_statistics
from core.llm.model import create_llm
from core.knowledge.loader import load_knowledge_base

# ===== ТАРО (новый модуль) =====
from core.tarot.loader import load_all_decks
from core.tarot.service import TarotService
from core.tarot import keyboards as tarot_kb
from core.tarot import render as tarot_render

load_dotenv()
ENV = os.getenv("ENV", "production").lower()
logger = get_logger()
logger.info("=== ИНИЦИАЛИЗАЦИЯ ПРОДАКШН АСТРО-БОТА (АСТРОЛОГИЯ + ТАРО) ===")

# Render автоматически прокидывает RENDER_EXTERNAL_URL
SELF_URL = os.getenv("RENDER_EXTERNAL_URL",
                     "https://astro-bot-b8m8.onrender.com")
KEEP_ALIVE_INTERVAL = 3600
APP_STARTED_AT = time.time()


# ============================================================
# СОСТОЯНИЯ FSM (для режимов "Вопрос")
# ============================================================
class AppStates(StatesGroup):
    waiting_astro_question = State()
    waiting_tarot_question = State()


# ============================================================
# 1. ЗАГРУЗКА БАЗЫ ЗНАНИЙ (АСТРОЛОГИЯ) + ТАРО
# ============================================================
documents = load_knowledge_base()
logger.info(f"🔥 Успешно создано фрагментов (Астрология): {len(documents)}")
astro_retriever = AstroRetriever(documents)
llm = create_llm()

model_name = getattr(settings, "MODEL_NAME", "Неизвестная модель")
logger.info(f"🤖 Используемая ИИ-модель: {model_name}")

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}")
])
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(astro_retriever, question_answer_chain)

# ТАРО: загрузка всех колод
tarot_decks = load_all_decks()
tarot = TarotService(tarot_decks)

bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Последний запрос пользователя (для "Перефразировать")
user_last_queries: Dict[int, str] = {}

ZODIAC_MAP = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы", "Can": "Рак",
    "Leo": "Лев", "Vir": "Дева", "Lib": "Весы", "Sco": "Скорпион",
    "Sgr": "Стрелец", "Cap": "Козерог", "Aqr": "Водолей", "Psc": "Рыбы"
}


# ============================================================
# ПАРСИНГ АСТРОЛОГИЧЕСКИХ ЗАПРОСОВ (ZET) — без изменений
# ============================================================
def parse_astrological_input(text: str) -> str:
    parsed_parts = []

    aspect_pattern = (
        r"([а-яА-Я\w\s\-]+?)\s+"
        r"([а-яА-Я\w\-]+)\s*"
        r"([><])\s*"
        r"[\d°\d\'\"]+\s*"
        r"([><])\s*"
        r"(\d+)([a-zA-Z]{3})\d+\s*-\s*"
        r"(\d+)([a-zA-Z]{3})\d+"
    )
    match = re.search(aspect_pattern, text)
    if match:
        try:
            aspect_type = match.group(1).strip()
            planets = match.group(2).strip()
            b1, b2 = match.group(3), match.group(4)
            p1_sign = ZODIAC_MAP.get(match.group(6), match.group(6))
            p2_sign = ZODIAC_MAP.get(match.group(8), match.group(8))
            if b1 == ">" and b2 == "<":
                direction = "СХОДЯЩИЙСЯ (орбис уменьшается, событие грядёт)"
            elif b1 == "<" and b2 == ">":
                direction = "РАСХОДЯЩИЙСЯ (орбис увеличивается, пик позади)"
            else:
                direction = "ТОЧНЫЙ"
            parsed_parts.append(
                f"Аспект: {aspect_type} между {planets}. Характер: {direction}. "
                f"Первая планета в знаке {p1_sign}, вторая в знаке {p2_sign}."
            )
        except (IndexError, AttributeError) as e:
            logger.warning(f"⚠️ Ошибка парсинга аспекта: {e}")
            parsed_parts.append(text.strip())

    cusp_pattern = (
        r"\b(II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|I)\s+"
        r"[\d°\d\'\".,\s]+\s*"
        r"([a-zA-Z]{3})\b"
    )
    cusp_matches = re.findall(cusp_pattern, text)
    if cusp_matches:
        roman_to_arabic = {
            "I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6",
            "VII": "7", "VIII": "8", "IX": "9", "X": "10", "XI": "11", "XII": "12"
        }
        for roman, sign_code in cusp_matches:
            house_num = roman_to_arabic[roman]
            sign_name = ZODIAC_MAP.get(sign_code, sign_code)
            parsed_parts.append(f"{house_num} дом в знаке {sign_name}.")

    if not parsed_parts:
        return text.strip()
    return " ".join(parsed_parts)


# ============================================================
# АСТРОЛОГИЯ: вызов RAG (без изменений логики)
# ============================================================
async def get_ai_interpretation(query: str) -> str:
    logger.info("=" * 60)
    logger.info(f"📥 ВХОДНОЙ ЗАПРОС (АСТРО): {query[:200]}...")
    start_time = time.time()

    for attempt in range(3):
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: rag_chain.invoke({"input": query}))
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"⏱️ Время выполнения запроса: {elapsed} сек")

            if "context" in response:
                stats = context_statistics(response["context"])
                logger.info("📚 КОНТЕКСТ RAG:\n" + stats)

            answer_msg = response.get("answer")
            if answer_msg and hasattr(answer_msg, "usage_metadata") and answer_msg.usage_metadata:
                u = answer_msg.usage_metadata
                logger.info(
                    f"📊 ТОКЕНЫ: вход={u.get('input_tokens')}, выход={u.get('output_tokens')}")

            answer_text = response.get("answer", "")
            if isinstance(answer_text, str):
                logger.info(f"📝 Длина ответа: {len(answer_text)} символов")
                return answer_text
            logger.warning(f"⚠️ Unexpected answer type: {type(answer_text)}")
            return str(answer_text)

        except Exception as e:
            logger.warning(f"⚠️ Ошибка вызова ИИ (попытка {attempt+1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(3)
            else:
                logger.error(f"❌ Все попытки исчерпаны: {e}")

    return "❌ Извините, шлюз ИИ-интерпретации перегружен. Повторите запрос через 5–10 минут."


# ============================================================
# ТАРО: вызов ИИ напрямую (без астро-RAG)
# ============================================================
async def get_tarot_ai_interpretation(question: str, drawn, deck_name: str) -> str:
    """Интерпретация расклада Таро через LLM (прямой вызов, без астро-контекста)."""
    positions = ["Прошлое", "Настоящее", "Будущее"]
    cards_desc = []
    for i, (card, rev) in enumerate(drawn):
        pos = positions[i] if i < len(positions) else f"Позиция {i+1}"
        orient = "перевёрнутое" if rev else "прямое"
        meaning = card.get_meaning(rev)
        cards_desc.append(f"{pos}: {card.name} ({orient}) — {meaning}")
    cards_text = "\n".join(cards_desc)

    human = (
        f"Вопрос клиента: {question}\n\n"
        f"Вытянутые карты (колода «{deck_name}»):\n{cards_text}\n\n"
        f"Дай связную, глубокую интерпретацию этого расклада в контексте вопроса."
    )

    for attempt in range(3):
        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: llm.invoke(
                    [("system", TAROT_SYSTEM_PROMPT), ("human", human)])
            )
            text = getattr(resp, "content", "") or str(resp)
            logger.info(f"🎴 ТАРО ответ: {len(text)} символов")
            return text
        except Exception as e:
            logger.warning(f"⚠️ Ошибка ТАРО-ИИ (попытка {attempt+1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(3)
    return "❌ Не удалось получить толкование. Попробуйте ещё раз."


# ============================================================
# УТИЛИТЫ ОТПРАВКИ
# ============================================================
def split_text_for_telegram(text: str, limit: int = 4000):
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
            current = ""
        if len(paragraph) <= limit:
            current = paragraph
            continue
        for sentence in re.split(r"(?<=[.!?]) ", paragraph):
            candidate = f"{current} {sentence}" if current else sentence
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    parts.append(current)
                current = sentence
    if current:
        parts.append(current)
    return parts


async def safe_answer(message: types.Message, text: str, **kwargs):
    """Отправка с фолбэком при ошибке Markdown."""
    try:
        await message.answer(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest:
        await message.answer(text, **kwargs)


async def safe_edit_text(message: types.Message, text: str, **kwargs):
    """Редактирование с защитой от ошибок (например, сообщение-фото)."""
    try:
        await message.edit_text(text, **kwargs)
        return True
    except TelegramBadRequest as e:
        logger.warning(f"⚠️ edit_text не удался: {e}")
        return False


def get_rephrase_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Перефразировать ответ", callback_data="rephrase")
    kb.adjust(1)
    return kb.as_markup()


# ============================================================
# АСТРОЛОГИЯ: обработка запроса (вынесено из handle_user_input)
# ============================================================
async def process_astro_request(message: types.Message, raw_text: str):
    """Полная обработка астрологического запроса: фильтры + RAG + отправка."""
    raw_lower = raw_text.lower()

    # Фильтр данных рождения
    if re.search(r"\d{2}\.\d{2}\.\d{4}", raw_lower) or any(
        w in raw_lower for w in ["родился", "родилась", "город", "время"]
    ):
        await message.answer(
            "⚠️ Уведомление Школы «12 Планет»\n\n"
            "Вы ввели данные рождения. Наш бот специализируется на интерпретации положений, "
            "а не на расчёте карты. Постройте карту в ZET или Sotis и пришлите положение "
            "планеты/аспект текстом.",
            parse_mode="Markdown"
        )
        return

    # Фильтр запрещённых объектов
    forbidden_objects = [
        "лилит", "черная луна", "селен", "белая луна",
        "раху", "кету", "лунные узлы", "северный узел", "южный узел",
        "астероид", "хирон", "паллада", "юнона", "веста", "прозерпин",
        "звезд", "туманност", "жребий", "парс", "фиктивн", "экзальтац", "падени", "обител", "изгнан",
    ]
    if any(w in raw_lower for w in forbidden_objects):
        await message.answer(
            "⚠️ Уведомление Школы «12 Планет»\n\n"
            "Вы упомянули объекты, не входящие в методологию Школы (астероиды, фиктивные точки, "
            "жребии, Раху/Кету, экзальтации/падения). Переформулируйте вопрос о планетах, знаках и домах.",
            parse_mode="Markdown"
        )
        return

    # Фильтр коротких запросов
    if len(raw_text.strip()) < 10:
        await message.answer("🔮 Пожалуйста, опишите астрологический показатель подробнее.")
        return

    # Основной сценарий
    processed_query = parse_astrological_input(raw_text)

    # Условная "Задача" (build_task_hint уже есть в вашем engine.py)
    if hasattr(astro_retriever, "build_task_hint"):
        task_hint = astro_retriever.build_task_hint(processed_query)
    else:
        task_hint = "Комплексный анализ по всем фундаментальным сферам"
    final_task = f"Показатель: {processed_query}\nЗадача: {task_hint}."

    user_last_queries[message.from_user.id] = final_task

    await message.answer("🔮 Школа Астрологии 12 Планет анализирует... Формируется ответ...")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    interpretation = await get_ai_interpretation(final_task)
    logger.info(f"📝 Длина ответа: {len(interpretation)} символов")

    if not interpretation or len(interpretation.strip()) < 20:
        await message.answer("⚠️ Модель вернула пустой ответ. Попробуйте перефразировать запрос.")
        return

    chunks = split_text_for_telegram(interpretation)
    sent_texts = set()
    for chunk in chunks:
        chunk_stripped = chunk.strip()
        if chunk_stripped and chunk_stripped not in sent_texts:
            await safe_answer(message, chunk_stripped, reply_markup=get_rephrase_keyboard())
            sent_texts.add(chunk_stripped)


# ============================================================
# /start — ГЛАВНОЕ МЕНЮ (Таро / Астрология 12 / Карта Дня)
# ============================================================
@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "🔮 Приветствую в пространстве Школы Астрологии «12 Планет»!\n\n"
        "Я интерпретирую положения планет, знаков, домов и расклады Таро "
        "строго по закрытой базе знаний Школы.\n\n"
        "🎯 Выберите раздел:"
    )
    await message.answer(welcome_text, reply_markup=tarot_kb.main_menu_keyboard())


# ============================================================
# ГЛАВНОЕ МЕНЮ: переходы
# ============================================================
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if not await safe_edit_text(
        callback.message, "🏠 Главное меню:", reply_markup=tarot_kb.main_menu_keyboard()
    ):
        await callback.message.answer("🏠 Главное меню:", reply_markup=tarot_kb.main_menu_keyboard())


@dp.callback_query(F.data == "menu_tarot")
async def menu_tarot(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    text = "🎴 <b>ТАРО</b>\n\nВыберите раздел:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.tarot_menu_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.tarot_menu_keyboard())


@dp.callback_query(F.data == "menu_astro")
async def menu_astro(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AppStates.waiting_astro_question)
    await callback.answer()
    text = (
        "🪐 <b>АСТРОЛОГИЯ 12</b>\n\n"
        "Напишите вопрос или вставьте строку из ZET, например:\n"
        "<code>Квадрат Сатурн-Нептун &gt; 91°19'&lt; 20Vir16 - 21Sgr36</code>\n\n"
        "Или просто текстом: «Что означает Сатурн в Деве в 4 доме?»"
    )
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.back_to_main_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.back_to_main_keyboard())


# ============================================================
# КАРТА ДНЯ
# ============================================================
@dp.callback_query(F.data == "menu_card_of_day")
async def menu_card_of_day(callback: types.CallbackQuery):
    await callback.answer()
    decks = tarot.list_decks()
    if not decks:
        await safe_edit_text(callback.message, "⚠️ Колоды не загружены. Добавьте колоды в data/tarot/decks/.")
        return
    if len(decks) == 1:
        await _show_cod_shuffle_screen(callback.message, decks[0])
    else:
        text = "🃏 <b>КАРТА ДНЯ</b>\n\nВыберите колоду:"
        if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                    reply_markup=tarot_kb.cod_decks_keyboard(decks)):
            await callback.message.answer(text, parse_mode="HTML",
                                          reply_markup=tarot_kb.cod_decks_keyboard(decks))


@dp.callback_query(F.data.startswith("cod_deck:"))
async def cod_select_deck(callback: types.CallbackQuery):
    deck_id = callback.data.split(":", 1)[1]
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return
    await _show_cod_shuffle_screen(callback.message, deck)


async def _show_cod_shuffle_screen(msg: types.Message, deck):
    """Экран Карты Дня с кнопкой перемешивания."""
    text = (
        f"🃏 <b>КАРТА ДНЯ</b>\n"
        f"Колода: {deck.name} ({deck.cards_count} карт)\n\n"
        f"Нажмите кнопку, чтобы перемешать колоду и вытянуть случайную карту."
    )
    kb = tarot_kb.card_of_day_keyboard(deck.deck_id)
    if not await safe_edit_text(msg, text, parse_mode="HTML", reply_markup=kb):
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("cod_shuffle:"))
async def cod_shuffle(callback: types.CallbackQuery):
    """ПЕРЕМЕШИВАНИЕ И СЛУЧАЙНАЯ КАРТА ДНЯ."""
    deck_id = callback.data.split(":", 1)[1]
    deck = tarot.get_deck(deck_id)
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return

    await callback.answer("🔀 Перемешиваю колоду...")

    # Перемешиваем (лог-факт) и тянем случайную карту
    tarot.shuffle(deck_id)
    card, is_reversed = tarot.card_of_the_day(deck_id)
    if not card:
        await callback.answer("Не удалось вытянуть карту", show_alert=True)
        return

    caption = tarot_render.format_card_of_day(card, is_reversed, deck)
    kb = tarot_kb.card_result_keyboard(deck_id)
    img = tarot_render.resolve_image(deck, card)

    # Если текущее сообщение уже фото — редактируем его
    if callback.message.content_type == ContentType.PHOTO and img:
        try:
            media = InputMediaPhoto(
                media=FSInputFile(img), caption=caption[:1024])
            await callback.message.edit_media(media, reply_markup=kb)
            return
        except TelegramBadRequest as e:
            logger.warning(f"⚠️ edit_media не удался: {e}")

    # Иначе — отправляем новое сообщение (фото или текст)
    if img:
        await callback.message.answer_photo(FSInputFile(img), caption=caption[:1024], reply_markup=kb)
    else:
        await callback.message.answer(caption, reply_markup=kb)


# ============================================================
# ТАРО: КОЛОДЫ (просмотр)
# ============================================================
@dp.callback_query(F.data == "tarot_decks")
async def tarot_decks(callback: types.CallbackQuery):
    await callback.answer()
    decks = tarot.list_decks()
    if not decks:
        await safe_edit_text(callback.message, "⚠️ Колоды не загружены.")
        return
    text = "📚 <b>КОЛОДЫ</b>\n\nВыберите колоду для просмотра:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.decks_list_keyboard(decks)):
        await callback.message.answer(text, parse_mode="HTML",
                                      reply_markup=tarot_kb.decks_list_keyboard(decks))


@dp.callback_query(F.data.startswith("deck_view:"))
async def deck_view(callback: types.CallbackQuery):
    deck_id = callback.data.split(":", 1)[1]
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return
    author = f"\nАвтор: {deck.author}" if deck.author else ""
    text = (
        f"🎴 <b>{deck.name}</b>{author}\n"
        f"Карт: {deck.cards_count}\n\n"
        f"{deck.description}\n\n"
        f"Выберите категорию:"
    )
    kb = tarot_kb.deck_categories_keyboard(deck_id)
    if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("deck_arcana:"))
async def deck_arcana(callback: types.CallbackQuery):
    _, deck_id, group = callback.data.split(":", 2)
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return

    if group == "major":
        cards = deck.major_arcana()
    else:
        cards = deck.minor_by_suit(group)

    title = tarot_kb.SUIT_NAMES.get(group, group)
    kb = tarot_kb.deck_cards_keyboard(deck_id, cards, title)
    text = f"🎴 <b>{deck.name}</b>\n{title} · выберите карту:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("deck_card:"))
async def deck_card(callback: types.CallbackQuery):
    _, deck_id, card_id = callback.data.split(":", 2)
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return
    card = deck.get_card(card_id)
    if not card:
        await callback.answer("Карта не найдена", show_alert=True)
        return

    caption = tarot_render.format_card_detail(card)
    img = tarot_render.resolve_image(deck, card)
    kb = tarot_kb.back_to_deck_keyboard(deck_id)

    if img:
        await callback.message.answer_photo(FSInputFile(img), caption=caption[:1024], reply_markup=kb)
    else:
        if not await safe_edit_text(callback.message, caption, reply_markup=kb):
            await callback.message.answer(caption, reply_markup=kb)


# ============================================================
# ТАРО: РАСКЛАДЫ
# ============================================================
@dp.callback_query(F.data == "tarot_spreads")
async def tarot_spreads(callback: types.CallbackQuery):
    await callback.answer()
    text = "📖 <b>РАСКЛАДЫ</b>\n\nВыберите расклад:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.spreads_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.spreads_keyboard())


@dp.callback_query(F.data.startswith("spread:"))
async def spread(callback: types.CallbackQuery):
    stype = callback.data.split(":", 1)[1]
    deck = tarot.get_deck()
    await callback.answer("🎴 Тяну карты...")
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return

    if stype == "one":
        card, is_rev = tarot.card_of_the_day(deck.deck_id)
        if not card:
            await callback.answer("Не удалось вытянуть карту", show_alert=True)
            return
        caption = tarot_render.format_card_of_day(card, is_rev, deck)
        img = tarot_render.resolve_image(deck, card)
        kb = tarot_kb.back_to_main_keyboard()
        if img:
            await callback.message.answer_photo(FSInputFile(img), caption=caption[:1024], reply_markup=kb)
        else:
            await callback.message.answer(caption, reply_markup=kb)

    elif stype == "three":
        drawn = tarot.draw_cards(3, deck.deck_id)
        caption = tarot_render.format_three_cards(drawn, deck)
        kb = tarot_kb.back_to_main_keyboard()
        for chunk in split_text_for_telegram(caption, 3900):
            await callback.message.answer(chunk, reply_markup=kb)


# ============================================================
# ТАРО: ВОПРОС (FSM)
# ============================================================
@dp.callback_query(F.data == "tarot_question")
async def tarot_question(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AppStates.waiting_tarot_question)
    await callback.answer()
    text = (
        "❓ <b>ВОПРОС ТАРО</b>\n\n"
        "Напишите ваш вопрос — я вытяну карты и дам толкование."
    )
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.back_to_main_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.back_to_main_keyboard())


@dp.message(StateFilter(AppStates.waiting_tarot_question), F.text)
async def handle_tarot_question(message: types.Message, state: FSMContext):
    await state.clear()
    question = message.text.strip()
    if len(question) < 5:
        await message.answer("🔮 Пожалуйста, опишите вопрос подробнее.")
        return

    await message.answer("🔮 Тяну карты и формирую толкование...")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    deck = tarot.get_deck()
    if not deck:
        await message.answer("⚠️ Колоды не загружены.")
        return

    drawn = tarot.draw_cards(3, deck.deck_id)
    cards_caption = tarot_render.format_three_cards(drawn, deck)
    interpretation = await get_tarot_ai_interpretation(question, drawn, deck.name)

    # Сначала карты, потом толкование
    for chunk in split_text_for_telegram(cards_caption, 3900):
        await message.answer(chunk)
    if interpretation:
        for chunk in split_text_for_telegram(interpretation, 3900):
            await message.answer(chunk)


# ============================================================
# АСТРОЛОГИЯ: вопрос через FSM + обычный текст (backward compat)
# ============================================================
@dp.message(StateFilter(AppStates.waiting_astro_question), F.text)
async def handle_astro_question(message: types.Message, state: FSMContext):
    await state.clear()
    await process_astro_request(message, message.text)


@dp.message(F.text)
async def handle_default_text(message: types.Message, state: FSMContext):
    """Текст без состояния → трактуем как астрологический запрос (как раньше)."""
    await process_astro_request(message, message.text)


# ============================================================
# ПЕРЕФРАЗИРОВАНИЕ (Астрология) — без изменений
# ============================================================
@dp.callback_query(F.data == "rephrase")
async def handle_rephrase(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_last_queries:
        await callback.answer("⚠️ История запроса устарела. Задайте новый вопрос.", show_alert=True)
        return
    await callback.answer("🔄 Генерирую новый вариант...")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)

    saved_task = user_last_queries[user_id]
    rephrase_prompt = (
        f"{saved_task}\n\n[ИНСТРУКЦИЯ: Перефразируй предыдущий ответ. Сохрани все смыслы и выводы, "
        f"но используй другие формулировки и структуру.]"
    )
    new_interpretation = await get_ai_interpretation(rephrase_prompt)
    for chunk in split_text_for_telegram(new_interpretation):
        await safe_answer(callback.message, chunk, reply_markup=get_rephrase_keyboard())


# ============================================================
# НЕ-ТЕКСТ
# ============================================================
@dp.message()
async def handle_non_text_input(message: types.Message):
    await message.answer(
        "⚠️ Я работаю только с текстовыми запросами.\n\n"
        "Опишите показатель словами или пришлите строку аспекта из ZET."
    )


# ============================================================
# WEB-СЕРВЕР / KEEP-ALIVE / UI — без изменений
# ============================================================
async def handle_health_check(request):
    uptime_min = round((time.time() - APP_STARTED_AT) / 60, 1)
    html = f"""
    <html>
    <head><meta charset="utf-8"><title>12 Планет — Астро-бот + Таро</title></head>
    <body style="font-family:sans-serif;text-align:center;padding-top:60px;">
        <h2>✅ Сервис работает</h2>
        <h3>Школа Астрологии «12 Планет» — ИИ-интерпретатор + Таро</h3>
        <p>Аптайм: {uptime_min} мин.</p>
        <h3>Вернитесь в Telegram и отправьте /start.</h3>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def keep_alive_pinger():
    await asyncio.sleep(30)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        while True:
            try:
                async with session.get(SELF_URL) as resp:
                    logger.info(f"🔁 Self-ping OK: {resp.status}")
            except Exception as e:
                logger.info(f"⚠️ Self-ping не удался: {e}")
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def setup_bot_ui():
    await bot.set_my_commands([
        BotCommand(command="start",
                   description="🔄 Перезапустить / главное меню"),
    ])
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def main():
    validate_settings()
    if not settings.IS_DEVELOPMENT:
        await start_web_server()
        asyncio.create_task(keep_alive_pinger())

    await bot.delete_webhook(drop_pending_updates=True)
    await setup_bot_ui()

    logger.info("🚀 Бот запущен (Астрология + Таро)")
    logger.info("=" * 60)
    logger.info("Astro12AI + TAROT")
    logger.info(f"ENV: {settings.ENV}")
    logger.info(f"ИИ-модель: {model_name}")
    logger.info(f"Knowledge chunks: {len(documents)}")
    logger.info(f"Tarot decks: {len(load_all_decks())}")
    logger.info("=" * 60)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
