"""
Astro12AI + TAROT
Астро-бот Школы «12 Планет» с модулем Таро.

Разделы:
- Астрология 12: интерпретация показателей (планеты, знаки, дома, аспекты)
- Таро: Колоды, Расклады, Вопрос (3 типа раскладов)
- Карта Дня: случайная карта с перемешиванием

Возможности Таро:
- Несколько колод (Райдер-Уэйт, Таро Тота, авторская)
- Выбор колоды перед каждым раскладом
- Визуальные образы карт (альбомы) во всех раскладах
- Названия карт в конкретной колоде + астрологический символизм
- Настройка перевёрнутых карт (запоминается при первом входе)
"""

import os
import re
import time
import asyncio
import aiohttp
from typing import Dict, List

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

# ===== ТАРО =====
from core.tarot.loader import load_all_decks
from core.tarot.service import TarotService, CELTIC_CROSS_POSITIONS, CHOICE_POSITIONS
from core.tarot import keyboards as tarot_kb
from core.tarot import render as tarot_render

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
load_dotenv()
ENV = os.getenv("ENV", "production").lower()
logger = get_logger()
logger.info("=== ИНИЦИАЛИЗАЦИЯ ПРОДАКШН АСТРО-БОТА (АСТРОЛОГИЯ + ТАРО) ===")

SELF_URL = os.getenv("RENDER_EXTERNAL_URL",
                     "https://astro-bot-b8m8.onrender.com")
KEEP_ALIVE_INTERVAL = 3600
APP_STARTED_AT = time.time()

ZODIAC_MAP = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы", "Can": "Рак",
    "Leo": "Лев", "Vir": "Дева", "Lib": "Весы", "Sco": "Скорпион",
    "Sgr": "Стрелец", "Cap": "Козерог", "Aqr": "Водолей", "Psc": "Рыбы"
}

# Авторские колоды Школы: для них в таро-промпт подкладываем материалы Школы астрологии
SCHOOL_DECK_IDS = {"author_deck_146", "author_deck"}


def _is_school_deck(deck_id=None, deck_name=None) -> bool:
    """Определяет авторскую колоду Школы по id ИЛИ по названию (надёжно)."""
    if deck_id and deck_id in SCHOOL_DECK_IDS:
        return True
    if deck_name and "12 Планет" in deck_name:
        return True
    return False

# ============================================================
# FSM СОСТОЯНИЯ
# ============================================================


class AppStates(StatesGroup):
    waiting_astro_question = State()
    waiting_tarot_reversed_setting = State()
    # НОВОЕ: ожидание текста вопроса для раскладов «Три карты» и «Кельтский крест»
    waiting_tarot_question_text = State()
    waiting_choice_essence = State()
    waiting_choice_option_a = State()
    waiting_choice_option_b = State()
# 🆕 Состояния ожидания повтора после ошибки ИИ
    waiting_tarot_retry = State()
    waiting_tarot_retry_choice = State()


# ============================================================
# ИНИЦИАЛИЗАЦИЯ ЯДРА (строго до bot/dp)
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

# Таро
tarot_decks = load_all_decks()
tarot = TarotService(tarot_decks)

# Бот и диспетчер (СТРОГО ДО всех @dp.*)
bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_last_queries: Dict[int, str] = {}
# 🆕 Последний таро-запрос пользователя для повтора с теми же картами
user_last_tarot: Dict[int, dict] = {}

# ============================================================
# ПАРСИНГ АСТРОЛОГИЧЕСКИХ ЗАПРОСОВ (ZET)
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
                direction = "СХОДЯЩИЙСЯ (орбис уменьшается, аспект ещё не стал точным, событие грядёт)"
            elif b1 == "<" and b2 == ">":
                direction = "РАСХОДЯЩИЙСЯ (орбис увеличивается, аспект уже прошёл точность)"
            else:
                direction = "ТОЧНЫЙ (аспект в точном значении)"

            parsed_parts.append(
                f"Аспект: {aspect_type} между {planets}. "
                f"Характер аспекта: {direction}. "
                f"Первая планета в знаке {p1_sign}, вторая планета в знаке {p2_sign}."
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
# АСТРОЛОГИЯ: вызов RAG (безопасный)
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
                try:
                    stats = context_statistics(response["context"])
                    if not isinstance(stats, str):
                        stats = str(stats)
                    logger.info("📚 КОНТЕКСТ RAG:\n" + stats)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось вывести статистику: {e}")

            answer_msg = response.get("answer")
            if answer_msg and hasattr(answer_msg, "usage_metadata") and answer_msg.usage_metadata:
                try:
                    u = answer_msg.usage_metadata
                    if isinstance(u, dict):
                        logger.info(
                            f"📊 ТОКЕНЫ: вход={u.get('input_tokens')}, выход={u.get('output_tokens')}")
                except Exception:
                    pass

            answer = response.get("answer")
            if answer is None:
                logger.warning("⚠️ Ответ пуст (None)")
                continue
            if hasattr(answer, "content"):
                answer_text = answer.content
            elif isinstance(answer, str):
                answer_text = answer
            else:
                answer_text = str(answer)
            if isinstance(answer_text, dict):
                answer_text = answer_text.get("text") or answer_text.get(
                    "answer") or str(answer_text)
            if not isinstance(answer_text, str):
                answer_text = str(answer_text)

            logger.info(f"📝 Длина ответа: {len(answer_text)} символов")
            if not answer_text.strip():
                logger.warning("⚠️ Пустой текст ответа — повторяем")
                continue
            return answer_text

        except Exception as e:
            error_msg = str(e).lower()
            # Обработка rate limit (429) от Groq free tier
            if "429" in error_msg or "rate_limit" in error_msg or "too many requests" in error_msg:
                logger.warning(f"⚠️ Groq rate limit (429): {e}")
                return ("⏳ **Сервис ИИ временно перегружен**\n\n"
                        "Бесплатный лимит Groq исчерпан. Попробуйте ещё раз через 1-2 минуты, "
                        "когда счётчик токенов обновится.")

            logger.warning(
                f"⚠️ Ошибка вызова ИИ (попытка {attempt + 1}/3): {e}")
            if attempt < 2:
                logger.info(f"⏳ Повторная попытка через 3 секунды...")
                await asyncio.sleep(3 * (attempt + 1))
            else:
                logger.error(
                    f"❌ Все 3 попытки исчерпаны. Последняя ошибка: {e}")

    return "❌ Извините, шлюз ИИ-интерпретации перегружен. Повторите запрос через 5–10 минут."


# ============================================================
# ТАРО: вызов ИИ (без астро-контекста)
# ============================================================
# Авторские колоды Школы: для них в таро-промпт подкладываем материалы Школы.
# (Если константа уже есть выше — не дублируйте, оставьте одну.)
SCHOOL_DECK_IDS = {"author_deck_146", "author_deck"}


def _is_school_deck(deck_id=None, deck_name=None) -> bool:
    """Определяет авторскую колоду Школы по id ИЛИ по названию (надёжно)."""
    if deck_id and deck_id in SCHOOL_DECK_IDS:
        return True
    if deck_name and "12 Планет" in deck_name:
        return True
    return False


async def get_tarot_ai_interpretation(question: str, drawn, deck_name: str,
                                      position_kinds=None, deck_id=None) -> str:
    """
    Интерпретация расклада через LLM.
    position_kinds: список видов позиций ('positive'/'negative'/'day'/'neutral').
    deck_id: если колода авторская (Школа) — в промпт добавляются материалы Школы
    (ключевые слова планет и знаков), как в астрологических вопросах.
    Возвращает None при ошибке 429 (для кнопки повтора).
    """
    logger.info("=" * 60)
    logger.info(f"🎴 ТАРО ЗАПРОС: {question[:200]}...")
    start_time = time.time()

    cards_desc = []
    for i, (card, rev) in enumerate(drawn):
        orient = "перевёрнутое" if rev else "прямое"
        astro = f" [{card.astrology}]" if card.astrology else ""
        kind = "neutral"
        if position_kinds and i < len(position_kinds):
            kind = position_kinds[i]
        meaning = tarot_render.card_context_for_position(card, rev, kind)
        cards_desc.append(
            f"Позиция {i + 1}: {card.name} ({orient}{astro}) —\n{meaning}")
    cards_text = "\n".join(cards_desc)

    # 🏫 Материалы Школы астрологии — только для авторских колод
    school_block = ""
    if _is_school_deck(deck_id, deck_name):
        entities_src = " ".join(
            f"{card.name} {card.astrology or ''}" for card, _ in drawn)
        school_block = astro_retriever.build_authority_context(entities_src)
        logger.info(
            f"🏫 Авторская колода «{deck_name}»: извлечено из карт: {entities_src[:120]}...")
        if school_block:
            logger.info(
                "🏫 Таро(авторская колода): приложен контекст Школы (планеты/знаки)")
        else:
            logger.warning(
                "⚠️ Авторская колода, но контекст Школы пуст (не извлечены сущности)")
    else:
        logger.info(
            f"ℹ️ Колода «{deck_name}» не авторская — контекст Школы не прикладывается")

    human = (
        f"Вопрос клиента: {question}\n"
        + (school_block + "\n" if school_block else "")
        + f"Вытянутые карты (колода «{deck_name}»):\n{cards_text}\n"
        f"Дай связную, глубокую интерпретацию этого расклада в контексте вопроса."
        + (" Для карт авторской колоды обязательно опирайся на ключевые слова "
           "планет и знаков Школы из блока выше." if school_block else "")
    )

    for attempt in range(3):
        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: llm.invoke(
                    [("system", TAROT_SYSTEM_PROMPT), ("human", human)])
            )
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"⏱️ ТАРО время выполнения: {elapsed} сек")
            text = getattr(resp, "content", "") or str(resp)
            if isinstance(text, dict):
                text = text.get("text") or str(text)
            logger.info(f"🎴 ТАРО ответ: {len(text)} символов")
            return text
        except Exception as e:
            error_msg = str(e).lower()
            # Обработка rate limit (429) от Groq free tier
            if "429" in error_msg or "rate_limit" in error_msg or "too many requests" in error_msg:
                logger.warning(f"⚠️ Groq rate limit (429): {e}")
                return None  # обработчик покажет кнопку «Попробовать ещё раз»

            logger.warning(f"⚠️ Ошибка ТАРО-ИИ (попытка {attempt + 1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(3 * (attempt + 1))
    return None  # ошибка — обработчики покажут кнопку повтора
# ============================================================
# УТИЛИТЫ
# ============================================================


def split_text_for_telegram(text: str, limit: int = 4000) -> List[str]:
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


def get_rephrase_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Перефразировать ответ", callback_data="rephrase")
    kb.adjust(1)
    return kb.as_markup()


def main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎴 Таро", callback_data="menu_tarot")
    kb.button(text="🪐 Астрология 12", callback_data="menu_astro")
    kb.button(text="🃏 Карта Дня", callback_data="menu_card_of_day")
    kb.button(text="🌙 Разбудить сервер", url=SELF_URL)
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def _drawable_decks():
    """Колоды, из которых можно тянуть карты (не пустые)."""
    return [d for d in tarot.list_decks() if d.cards_count > 0]


async def send_spread_cards_visual(msg: types.Message, deck, drawn, positions) -> int:
    """
    Отправляет альбом картинок расклада (до 10 фото на альбом).
    Возвращает число отправленных изображений.
    """
    items = tarot_render.spread_cards_visual(deck, drawn, positions)
    media = []
    for it in items:
        if it["path"]:
            media.append(InputMediaPhoto(media=FSInputFile(
                it["path"]), caption=it["caption"]))

    sent = 0
    for i in range(0, len(media), 10):
        try:
            await bot.send_media_group(chat_id=msg.chat.id, media=media[i:i + 10])
            sent += len(media[i:i + 10])
        except TelegramBadRequest as e:
            logger.warning(f"⚠️ send_media_group не удался: {e}")
    if media:
        logger.info(f"🖼️ Отправлено изображений расклада: {sent}")
    return sent


async def send_chunks(msg: types.Message, text: str):
    """Отправка текста по фрагментам БЕЗ клавиатуры."""
    for chunk in split_text_for_telegram(text, 3900):
        await msg.answer(chunk)


async def send_chunks_with_kb(msg: types.Message, text: str, kb):
    """Отправка текста по фрагментам; клавиатура kb крепится к ПОСЛЕДНЕМУ фрагменту."""
    chunks = split_text_for_telegram(text, 3900)
    for i, chunk in enumerate(chunks):
        await msg.answer(chunk, reply_markup=(kb if i == len(chunks) - 1 else None))


async def send_chunks_with_nav(msg: types.Message, text: str, back_callback: str):
    """Отправка текста по фрагментам; к ПОСЛЕДНЕМУ фрагменту крепит клавиатуру Назад/Главное меню."""
    chunks = split_text_for_telegram(text, 3900)
    kb = tarot_kb.spread_done_keyboard(back_callback)
    for i, chunk in enumerate(chunks):
        await msg.answer(chunk, reply_markup=(kb if i == len(chunks) - 1 else None))


async def safe_answer(message: types.Message, text: str, **kwargs):
    try:
        await message.answer(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest:
        await message.answer(text, **kwargs)


async def safe_edit_text(message: types.Message, text: str, **kwargs) -> bool:
    try:
        await message.edit_text(text, **kwargs)
        return True
    except TelegramBadRequest as e:
        logger.warning(f"⚠️ edit_text не удался: {e}")
        return False


# ============================================================
# АСТРОЛОГИЯ: обработка запроса
# ============================================================
async def process_astro_request(message: types.Message, raw_text: str):
    raw_lower = raw_text.lower()

    if re.search(r"\d{2}\.\d{2}\.\d{4}", raw_lower) or any(
        w in raw_lower for w in ["родился", "родилась", "город", "время"]
    ):
        await message.answer(
            "⚠️ **Уведомление Школы Астрологии «12 Планет»**\n\n"
            "Вы ввели данные рождения. Наш бот специализируется на **интерпретации положений**, "
            "а не на расчёте карты. Постройте карту в **ZET** или **Sotis** и пришлите положение планеты/аспект текстом.",
            parse_mode="Markdown"
        )
        return

    forbidden_objects = [
        "лилит", "черная луна", "селен", "белая луна",
        "раху", "кету", "лунные узлы", "северный узел", "южный узел",
        "астероид", "хирон", "паллада", "юнона", "веста", "прозерпин",
        "звезд", "туманност", "жребий", "парс", "фиктивн", "экзальтац", "падени", "обител", "изгнан",
    ]
    if any(w in raw_lower for w in forbidden_objects):
        await message.answer(
            "⚠️ **Уведомление Школы Астрологии «12 Планет»**\n\n"
            "Вы упомянули объекты, не входящие в методологию Школы. Переформулируйте вопрос о планетах, знаках и домах.",
            parse_mode="Markdown"
        )
        return

    if len(raw_text.strip()) < 10:
        await message.answer("🔮 Пожалуйста, опишите астрологический показатель подробнее.")
        return

    processed_query = parse_astrological_input(raw_text)
    task_hint = astro_retriever.build_task_hint(processed_query)
    final_task = f"Показатель: {processed_query}\nЗадача: {task_hint}."

    user_last_queries[message.from_user.id] = final_task

    await message.answer(
        "🔮 Школа Астрологии 12 Планет анализирует... Формируется ответ...",
        parse_mode="Markdown"
    )
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    interpretation = await get_ai_interpretation(final_task)
    logger.info(
        f"📝 Длина сгенерированного ответа: {len(interpretation)} символов")

    if not interpretation or len(interpretation.strip()) < 20:
        await message.answer("⚠️ Модель вернула пустой ответ. Попробуйте перефразировать.")
        return

    chunks = split_text_for_telegram(interpretation)
    sent_texts = set()
    for chunk in chunks:
        chunk_stripped = chunk.strip()
        if chunk_stripped and chunk_stripped not in sent_texts:
            await safe_answer(message, chunk_stripped, reply_markup=get_rephrase_keyboard())
            sent_texts.add(chunk_stripped)


# ============================================================
# /start — ГЛАВНОЕ МЕНЮ
# ============================================================
@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "🔮 Приветствую в интеллектуальном пространстве Школы Астрологии «12 Планет»!\n\n"
        "🎯 Наша миссия — чистая, глубокая и бескомпромиссная интерпретация.\n\n"
        "Выберите раздел:"
    )
    try:
        await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    except TelegramBadRequest:
        await message.answer(welcome_text, reply_markup=main_menu_keyboard())


# ============================================================
# ГЛАВНОЕ МЕНЮ: переходы
# ============================================================
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    logger.info("🔘 Callback: back_to_main")
    await state.clear()
    await callback.answer()
    if not await safe_edit_text(callback.message, "🏠 Главное меню:",
                                reply_markup=main_menu_keyboard()):
        await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu_keyboard())


@dp.callback_query(F.data == "menu_tarot")
async def menu_tarot(callback: types.CallbackQuery, state: FSMContext):
    logger.info("🔘 Callback: menu_tarot")
    await callback.answer()
    await state.clear()

    user_id = callback.from_user.id

    if user_id not in tarot.user_settings:
        await state.set_state(AppStates.waiting_tarot_reversed_setting)
        text = (
            "🎴 <b>НАСТРОЙКА ТАРО</b>\n\n"
            "Использовать ли <b>перевёрнутые карты</b> в раскладах?\n\n"
            "• <b>Да</b> — карты могут выпадать в прямом или перевёрнутом положении\n"
            "• <b>Нет</b> — только прямое положение"
        )
        if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                    reply_markup=tarot_kb.reversed_setting_keyboard()):
            await callback.message.answer(text, parse_mode="HTML",
                                          reply_markup=tarot_kb.reversed_setting_keyboard())
        return

    use_reversed = tarot.get_user_reversed_setting(user_id)
    setting_text = "✅ Перевёрнутые карты" if use_reversed else "❌ Только прямые"
    text = f"🎴 <b>ТАРО</b>\n\nНастройка: {setting_text}\n\nВыберите раздел:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.tarot_menu_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.tarot_menu_keyboard())


@dp.callback_query(F.data.startswith("reversed:"), StateFilter(AppStates.waiting_tarot_reversed_setting))
async def save_reversed_setting(callback: types.CallbackQuery, state: FSMContext):
    logger.info("🔘 Callback: reversed setting")
    use_reversed = callback.data.split(":", 1)[1] == "yes"
    user_id = callback.from_user.id

    tarot.set_user_reversed_setting(user_id, use_reversed)
    await state.clear()

    setting_text = "✅ Перевёрнутые карты" if use_reversed else "❌ Только прямые"
    await callback.answer(f"Настройка: {setting_text}")

    text = f"🎴 <b>ТАРО</b>\n\nНастройка: {setting_text}\n\nВыберите раздел:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.tarot_menu_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.tarot_menu_keyboard())


@dp.callback_query(F.data == "menu_astro")
async def menu_astro(callback: types.CallbackQuery, state: FSMContext):
    logger.info("🔘 Callback: menu_astro")
    await callback.answer()
    await state.set_state(AppStates.waiting_astro_question)
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
# КАРТА ДНЯ (только непустые колоды)
# ============================================================
@dp.callback_query(F.data == "menu_card_of_day")
async def menu_card_of_day(callback: types.CallbackQuery):
    logger.info("🔘 Callback: menu_card_of_day")
    await callback.answer()
    decks = _drawable_decks()
    if not decks:
        await safe_edit_text(callback.message, "⚠️ Нет колод с картами.")
        return
    if len(decks) == 1:
        await _show_cod_shuffle_screen(callback.message, decks[0])
    else:
        text = "🃏 <b>КАРТА ДНЯ</b>\n\nВыберите колоду:"
        if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                    reply_markup=tarot_kb.cod_decks_keyboard(decks)):
            await callback.message.answer(text, parse_mode="HTML",
                                          reply_markup=tarot_kb.cod_decks_keyboard(decks))


async def _show_cod_shuffle_screen(msg: types.Message, deck):
    text = (
        f"🃏 <b>КАРТА ДНЯ</b>\n"
        f"Колода: {deck.name} ({deck.cards_count} карт)\n\n"
        f"Нажмите кнопку, чтобы перемешать колоду."
    )
    kb = tarot_kb.card_of_day_keyboard(deck.deck_id)
    if not await safe_edit_text(msg, text, parse_mode="HTML", reply_markup=kb):
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("cod_deck:"))
async def cod_select_deck(callback: types.CallbackQuery):
    logger.info(f"🔘 Callback: {callback.data}")
    deck_id = callback.data.split(":", 1)[1]
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck or not deck.cards:
        await callback.answer("Колода недоступна", show_alert=True)
        return
    await _show_cod_shuffle_screen(callback.message, deck)


@dp.callback_query(F.data.startswith("cod_shuffle:"))
async def cod_shuffle(callback: types.CallbackQuery):
    logger.info(f"🔘 Callback: {callback.data}")
    deck_id = callback.data.split(":", 1)[1]
    deck = tarot.get_deck(deck_id)
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return

    await callback.answer("🔀 Перемешиваю колоду...")

    tarot.shuffle(deck_id)
    card, is_reversed = tarot.card_of_the_day(deck_id, callback.from_user.id)
    if not card:
        await callback.answer("Не удалось вытянуть карту", show_alert=True)
        return

    caption = tarot_render.format_card_of_day(card, is_reversed, deck)
    short = f"🃏 {card.name} — {deck.name}"
    kb = tarot_kb.card_result_keyboard(deck_id)
    img = tarot_render.resolve_image(deck, card)

    if callback.message.content_type == ContentType.PHOTO and img:
        try:
            media = InputMediaPhoto(media=FSInputFile(img), caption=short)
            await callback.message.edit_media(media)
            await send_chunks_with_kb(callback.message, caption, kb)
            return
        except TelegramBadRequest as e:
            logger.warning(f"⚠️ edit_media не удался: {e}")

    if img:
        await callback.message.answer_photo(FSInputFile(img), caption=short)
        await send_chunks_with_kb(callback.message, caption, kb)
    else:
        await send_chunks_with_kb(callback.message, caption, kb)

# ============================================================
# ТАРО: КОЛОДЫ (просмотр)
# ============================================================


@dp.callback_query(F.data == "tarot_decks")
async def tarot_decks_cb(callback: types.CallbackQuery):
    logger.info("🔘 Callback: tarot_decks")
    await callback.answer()
    decks = tarot.list_decks()
    if not decks:
        await safe_edit_text(callback.message, "⚠️ Колоды не загружены.")
        return
    text = "📚 <b>КОЛОДЫ</b>\n\nВыберите колоду:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.decks_list_keyboard(decks)):
        await callback.message.answer(text, parse_mode="HTML",
                                      reply_markup=tarot_kb.decks_list_keyboard(decks))


@dp.callback_query(F.data.startswith("deck_view:"))
async def deck_view(callback: types.CallbackQuery):
    logger.info(f"🔘 Callback: {callback.data}")
    deck_id = callback.data.split(":", 1)[1]
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return

    author = f"\nАвтор: {deck.author}" if deck.author else ""

    # Пустая колода (в разработке)
    if deck.cards_count == 0:
        text = (
            f"🛠️ <b>{deck.name}</b>{author}\n\n"
            f"{deck.description}\n\n"
            f"Карт в колоде пока нет — колода в разработке."
        )
        kb = tarot_kb.back_to_deck_keyboard(deck_id)
        if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    # Оракульная колода: категории по знакам зодиака
    if deck.deck_type == "oracle":
        groups = deck.groups_ordered()
        kb = tarot_kb.oracle_categories_keyboard(deck_id, groups)
        text = (
            f"🔮 <b>{deck.name}</b>{author}\n"
            f"Карт: {deck.cards_count}\n\n"
            f"{deck.description}\n\n"
            f"Выберите знак зодиака:"
        )
    else:
        kb = tarot_kb.deck_categories_keyboard(deck_id)
        text = (
            f"🎴 <b>{deck.name}</b>{author}\n"
            f"Карт: {deck.cards_count}\n\n"
            f"{deck.description}\n\n"
            f"Выберите категорию:"
        )

    if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("deck_arcana:"))
async def deck_arcana(callback: types.CallbackQuery):
    logger.info(f"🔘 Callback: {callback.data}")
    _, deck_id, group = callback.data.split(":", 2)
    deck = tarot.get_deck(deck_id)
    await callback.answer()
    if not deck:
        await callback.answer("Колода не найдена", show_alert=True)
        return

    if deck.deck_type == "oracle":
        cards = deck.cards_by_group(group)
        title = group
    else:
        if group == "major":
            cards = deck.major_arcana()
        else:
            cards = deck.minor_by_suit(group)
        title = tarot_kb.SUIT_NAMES.get(group, group)

    kb = tarot_kb.deck_cards_keyboard(deck_id, cards, title)
    text = f"🎴 <b>{deck.name}</b>\n{title} — выберите карту:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("deck_card:"))
async def deck_card(callback: types.CallbackQuery):
    logger.info(f"🔘 Callback: {callback.data}")
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
    # «К списку карт» + «Главное меню»
    kb = tarot_kb.back_to_deck_keyboard(deck_id)

    if img:
        # Фото с короткой подписью (без кнопок)
        await callback.message.answer_photo(
            FSInputFile(img), caption=f"🎴 {card.name} — {deck.name}")
        # Полное описание; кнопки — на ПОСЛЕДНЕМ сообщении
        chunks = split_text_for_telegram(caption, 3900)
        for i, chunk in enumerate(chunks):
            last = (i == len(chunks) - 1)
            await callback.message.answer(
                chunk, reply_markup=(kb if last else None))
    else:
        # Без картинки: редактируем/шлём текст, кнопки — на последнем сообщении
        chunks = split_text_for_telegram(caption, 3900)
        for i, chunk in enumerate(chunks):
            last = (i == len(chunks) - 1)
            if i == 0:
                if not await safe_edit_text(callback.message, chunk,
                                            reply_markup=(kb if last else None)):
                    await callback.message.answer(
                        chunk, reply_markup=(kb if last else None))
            else:
                await callback.message.answer(
                    chunk, reply_markup=(kb if last else None))

# ============================================================
# ТАРО: РАСКЛАДЫ (простые) — С ВЫБОРОМ КОЛОДЫ
# ============================================================


@dp.callback_query(F.data == "tarot_spreads")
async def tarot_spreads(callback: types.CallbackQuery):
    logger.info("🔘 Callback: tarot_spreads")
    await callback.answer()
    text = "📖 <b>РАСКЛАДЫ</b>\n\nВыберите расклад:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.spreads_keyboard()):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=tarot_kb.spreads_keyboard())


@dp.callback_query(F.data.startswith("spread:"))
async def spread_pick(callback: types.CallbackQuery):
    """Выбор типа расклада → выбор колоды (если их несколько)."""
    logger.info(f"🔘 Callback: {callback.data}")
    stype = callback.data.split(":", 1)[1]
    decks = _drawable_decks()
    await callback.answer()
    if not decks:
        await callback.answer("Нет колод с картами", show_alert=True)
        return

    if len(decks) == 1:
        await _run_simple_spread(callback.message, stype, decks[0], callback.from_user.id)
    else:
        text = f"🎴 <b>Выберите колоду для расклада:</b>"
        kb = tarot_kb.deck_pick_keyboard(
            f"spread_deck:{stype}", decks, "tarot_spreads")
        if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("spread_deck:"))
async def spread_deck(callback: types.CallbackQuery):
    """Расклад выполняется с выбранной колодой."""
    logger.info(f"🔘 Callback: {callback.data}")
    _, stype, deck_id = callback.data.split(":", 2)
    deck = tarot.get_deck(deck_id)
    if not deck or not deck.cards:
        await callback.answer("Колода недоступна", show_alert=True)
        return
    await callback.answer("🎴 Тяну карты...")
    await _run_simple_spread(callback.message, stype, deck, callback.from_user.id)


async def _run_simple_spread(msg: types.Message, stype: str, deck, user_id: int):
    """Выполнение простых раскладов (одна / три карты) с финальной навигацией."""
    if stype == "one":
        card, is_rev = tarot.card_of_the_day(deck.deck_id, user_id)
        if not card:
            await msg.answer("⚠️ Не удалось вытянуть карту.",
                             reply_markup=tarot_kb.spread_done_keyboard("tarot_spreads"))
            return

        caption = tarot_render.format_card_of_day(card, is_rev, deck)
        short = f"🃏 {card.name} — {deck.name}"
        img = tarot_render.resolve_image(deck, card)
        kb = tarot_kb.spread_done_keyboard("tarot_spreads")
        if img:
            await msg.answer_photo(FSInputFile(img), caption=short)
            await send_chunks_with_kb(msg, caption, kb)
        else:
            await send_chunks_with_kb(msg, caption, kb)

    elif stype == "three":
        drawn = tarot.draw_three_cards(deck.deck_id, user_id)
        if not drawn:
            await msg.answer("⚠️ Не удалось вытянуть карты.",
                             reply_markup=tarot_kb.spread_done_keyboard("tarot_spreads"))
            return
        await send_spread_cards_visual(msg, deck, drawn, ["Прошлое", "Настоящее", "Будущее"])
        caption = tarot_render.format_three_cards(drawn, deck)
        await send_chunks_with_nav(msg, caption, "tarot_spreads")

# ============================================================
# ТАРО: ВОПРОС — С ВЫБОРОМ КОЛОДЫ
# ============================================================


@dp.callback_query(F.data == "tarot_question")
async def tarot_question(callback: types.CallbackQuery, state: FSMContext):
    logger.info("🔘 Callback: tarot_question")
    await state.clear()
    await callback.answer()
    text = "❓ <b>ВОПРОС ТАРО</b>\n\nВыберите тип расклада:"
    if not await safe_edit_text(callback.message, text, parse_mode="HTML",
                                reply_markup=tarot_kb.tarot_question_menu_keyboard()):
        await callback.message.answer(text, parse_mode="HTML",
                                      reply_markup=tarot_kb.tarot_question_menu_keyboard())


@dp.callback_query(F.data.startswith("q_spread:"))
async def question_spread(callback: types.CallbackQuery, state: FSMContext):
    """Выбор расклада в разделе Вопрос → выбор колоды (если их несколько) → вопрос/карты."""
    logger.info(f"🔘 Callback: {callback.data}")
    spread_type = callback.data.split(":", 1)[1]
    decks = _drawable_decks()
    await callback.answer()
    if not decks:
        await callback.answer("Нет колод с картами", show_alert=True)
        return

    if len(decks) == 1:
        deck = decks[0]
        if spread_type == "choice":
            await _start_choice_fsm(callback.message, deck, state)
        elif spread_type == "cod":
            await _run_cod_question(callback.message, deck, callback.from_user.id, state)
        else:
            await _start_question_fsm(callback.message, spread_type, deck, state)
    else:
        text = "🎴 <b>Выберите колоду для расклада:</b>"
        kb = tarot_kb.deck_pick_keyboard(
            f"q_deck:{spread_type}", decks, "tarot_question")
        if not await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=kb):
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("q_deck:"))
async def question_deck_pick(callback: types.CallbackQuery, state: FSMContext):
    """Колода выбрана: запускаем расклад, ФСМ вопроса или ФСМ Варианта выбора."""
    logger.info(f"🔘 Callback: {callback.data}")
    _, spread_type, deck_id = callback.data.split(":", 2)
    deck = tarot.get_deck(deck_id)
    if not deck or not deck.cards:
        await callback.answer("Колода недоступна", show_alert=True)
        return
    await callback.answer()

    if spread_type == "choice":
        await _start_choice_fsm(callback.message, deck, state)
    elif spread_type == "cod":
        await _run_cod_question(callback.message, deck, callback.from_user.id, state)
    else:
        await _start_question_fsm(callback.message, spread_type, deck, state)


async def _start_question_fsm(msg: types.Message, spread_type: str, deck, state: FSMContext):
    """Запуск ФСМ: сначала пользователь пишет вопрос, затем выполняется расклад."""
    await state.set_state(AppStates.waiting_tarot_question_text)
    await state.update_data(q_spread_type=spread_type, deck_id=deck.deck_id)

    spread_names = {
        "three": "Трёхкарточный расклад (Прошлое — Настоящее — Будущее)",
        "celtic": "Кельтский крест (10 позиций)",
        "plusminus": "Плюс — Минус — Итог",
        "mindheart": "Мысли — Чувства — Действия (для отношений)",
        "triplet": "Динамический триплет (Достоинства стихий)",
        "yesno": "Да или Нет (одна карта-ответ)",
    }
    name = spread_names.get(spread_type, "Расклад")
    text = (
        f"❓ <b>ВОПРОС ТАРО</b>\n"
        f"Расклад: {name}\n"
        f"Колода: «{deck.name}»\n\n"
        f"Напишите ваш <b>вопрос</b>, на который должен ответить расклад:"
    )
    if not await safe_edit_text(msg, text, parse_mode="HTML",
                                reply_markup=tarot_kb.back_to_main_keyboard()):
        await msg.answer(text, parse_mode="HTML", reply_markup=tarot_kb.back_to_main_keyboard())


async def _run_cod_question(msg: types.Message, deck, user_id: int, state: FSMContext = None):
    """«Карта Дня» в разделе Вопрос: тянем карту и отправляем в RAG на интерпретацию."""
    card, is_rev = tarot.card_of_the_day(deck.deck_id, user_id)
    if not card:
        await msg.answer("⚠️ Не удалось вытянуть карту.",
                         reply_markup=tarot_kb.spread_done_keyboard("tarot_question"))
        return

    caption = tarot_render.format_card_of_day(card, is_rev, deck)
    short = f"🃏 {card.name} — {deck.name}"
    img = tarot_render.resolve_image(deck, card)
    if img:
        await msg.answer_photo(FSInputFile(img), caption=short)
        await send_chunks(msg, caption)
    else:
        await send_chunks(msg, caption)

    await bot.send_chat_action(chat_id=msg.chat.id, action=ChatAction.TYPING)
    question = (
        "Карта Дня: какая энергия сегодня главная, чего ожидать, "
        "на что обратить внимание и каков совет дня."
    )
    user_last_tarot[user_id] = {
        "question": question, "deck_id": deck.deck_id,
        "drawn_ids": [(card.card_id, is_rev)], "position_kinds": None,
    }
    interpretation = await get_tarot_ai_interpretation(
        question, [(card, is_rev)], deck.name, deck_id=deck.deck_id)
    if interpretation:
        await send_chunks_with_nav(msg, interpretation, "tarot_question")
    else:
        if state:
            await state.set_state(AppStates.waiting_tarot_retry)
            await state.update_data(
                drawn_ids=[(card.card_id, is_rev)],
                deck_id=deck.deck_id,
                question=question,
                position_kinds=None,
                is_choice=False,
            )
        await msg.answer(
            "⚠️ Сервис ИИ временно недоступен. Нажмите кнопку ниже, чтобы повторить "
            "запрос с той же картой.",
            reply_markup=tarot_kb.retry_tarot_keyboard()
        )


async def _start_choice_fsm(msg: types.Message, deck, state: FSMContext):
    """Запуск ФСМ «Вариант выбора» с запоминанием колоды."""
    await state.set_state(AppStates.waiting_choice_essence)
    await state.update_data(deck_id=deck.deck_id)
    text = (
        f"⚖️ <b>ВАРИАНТ ВЫБОРА</b> — колода «{deck.name}»\n\n"
        f"Напишите <b>суть выбора</b> (в чём заключается дилемма?):"
    )
    if not await safe_edit_text(msg, text, parse_mode="HTML",
                                reply_markup=tarot_kb.back_to_main_keyboard()):
        await msg.answer(text, parse_mode="HTML", reply_markup=tarot_kb.back_to_main_keyboard())


async def _run_question_spread(msg: types.Message, spread_type: str, deck, user_id: int, question: str, state: FSMContext = None):
    """Расклад на вопрос: альбом карт + расшифровка + ИИ-ответ + финальная навигация."""
    question_for_llm = question
    position_kinds = None

    if spread_type == "three":
        drawn = tarot.draw_three_cards(deck.deck_id, user_id)
        positions = ["Прошлое", "Настоящее", "Будущее"]
        caption = tarot_render.format_three_cards(drawn, deck)
    elif spread_type == "celtic":
        drawn = tarot.draw_celtic_cross(deck.deck_id, user_id)
        positions = CELTIC_CROSS_POSITIONS
        caption = tarot_render.format_celtic_cross(drawn, deck)
    elif spread_type == "plusminus":
        drawn = tarot.draw_three_cards(deck.deck_id, user_id)
        positions = tarot_render.PLUS_MINUS_POSITIONS
        caption = tarot_render.format_plus_minus(drawn, deck)
        position_kinds = ["positive", "negative", "neutral"]
    elif spread_type == "mindheart":
        drawn = tarot.draw_three_cards(deck.deck_id, user_id)
        positions = tarot_render.MIND_HEART_POSITIONS
        caption = tarot_render.format_mind_heart(drawn, deck)
    elif spread_type == "triplet":
        drawn = tarot.draw_three_cards(deck.deck_id, user_id)
        positions = tarot_render.TRIPLET_POSITIONS
        caption = tarot_render.format_triplet(drawn, deck)
        dignities_text = "\n".join(tarot_render.triplet_dignities(drawn))
        question_for_llm = (
            f"{question}\n\n"
            f"Анализ «Достоинства стихий» (вычислен, следуй ему строго):\n{dignities_text}"
        )
    elif spread_type == "yesno":
        card, is_rev = tarot.card_of_the_day(deck.deck_id, user_id)
        if not card:
            await msg.answer("⚠️ Не удалось вытянуть карту.",
                             reply_markup=tarot_kb.spread_done_keyboard("tarot_question"))
            return
        drawn = [(card, is_rev)]
        positions = ["КАРТА ОТВЕТА"]
        caption = tarot_render.format_yes_no(card, is_rev, deck, question)
        question_for_llm = f"Вопрос клиента, на который нужно ответить ДА или НЕТ: {question}"
        position_kinds = ["neutral"]
    elif spread_type == "cod":
        card, is_rev = tarot.card_of_the_day(deck.deck_id, user_id)
        if not card:
            await msg.answer("⚠️ Не удалось вытянуть карту.",
                             reply_markup=tarot_kb.spread_done_keyboard("tarot_question"))
            return
        drawn = [(card, is_rev)]
        positions = ["КАРТА ДНЯ"]
        caption = tarot_render.format_card_of_day(card, is_rev, deck)
        position_kinds = ["day"]
    else:
        return

    if not drawn:
        await msg.answer("⚠️ Не удалось вытянуть карты.",
                         reply_markup=tarot_kb.spread_done_keyboard("tarot_question"))
        return

    await send_spread_cards_visual(msg, deck, drawn, positions)
    await send_chunks(msg, caption)

    await bot.send_chat_action(chat_id=msg.chat.id, action=ChatAction.TYPING)
    user_last_tarot[user_id] = {
        "question": question_for_llm, "deck_id": deck.deck_id,
        "drawn_ids": [(c.card_id, rev) for c, rev in drawn],
        "position_kinds": position_kinds,
    }
    interpretation = await get_tarot_ai_interpretation(
        question_for_llm, drawn, deck.name, position_kinds, deck_id=deck.deck_id)
    if interpretation:
        await send_chunks_with_nav(msg, interpretation, "tarot_question")
    else:
        if state:
            await state.set_state(AppStates.waiting_tarot_retry)
            await state.update_data(
                drawn_ids=[(c.card_id, rev) for c, rev in drawn],
                deck_id=deck.deck_id,
                question=question_for_llm,
                position_kinds=position_kinds,
                is_choice=False,
            )
        await msg.answer(
            "⚠️ Сервис ИИ временно недоступен. Нажмите кнопку ниже, чтобы повторить "
            "запрос с теми же вытянутыми картами.",
            reply_markup=tarot_kb.retry_tarot_keyboard()
        )

# ============================================================
# ВАРИАНТ ВЫБОРА: FSM
# ============================================================


@dp.message(StateFilter(AppStates.waiting_choice_essence), F.text)
async def choice_essence(message: types.Message, state: FSMContext):
    await state.update_data(essence=message.text.strip())
    await state.set_state(AppStates.waiting_choice_option_a)
    await message.answer("✅ Сохранено.\n\nТеперь напишите <b>Вариант 1</b>:", parse_mode="HTML")


@dp.message(StateFilter(AppStates.waiting_choice_option_a), F.text)
async def choice_option_a(message: types.Message, state: FSMContext):
    await state.update_data(option_a=message.text.strip())
    await state.set_state(AppStates.waiting_choice_option_b)
    await message.answer("✅ Сохранено.\n\nТеперь напишите <b>Вариант 2</b>:", parse_mode="HTML")


@dp.message(StateFilter(AppStates.waiting_choice_option_b), F.text)
async def choice_option_b(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    option_b = message.text.strip()
    essence = data.get("essence", "")
    option_a = data.get("option_a", "")
    deck_id = data.get("deck_id")
    user_id = message.from_user.id

    deck = tarot.get_deck(deck_id) if deck_id else tarot.get_deck()
    if not deck or not deck.cards:
        await message.answer("⚠️ Колода недоступна.",
                             reply_markup=tarot_kb.spread_done_keyboard("tarot_question"))
        return

    await message.answer(f"🔮 Тяну 7 карт из колоды «{deck.name}»...")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    drawn = tarot.draw_choice_spread(deck.deck_id, user_id)
    if len(drawn) != 7:
        logger.error(f"❌ Вариант выбора: {len(drawn)} карт вместо 7")
        await message.answer(f"⚠️ Ошибка: {len(drawn)} карт вместо 7. Попробуйте ещё раз.",
                             reply_markup=tarot_kb.spread_done_keyboard("tarot_question"))
        return

    positions = tarot_render.choice_positions_list()
    await send_spread_cards_visual(message, deck, drawn, positions)
    await send_chunks(message, tarot_render.format_choice_spread(drawn, deck, essence, option_a, option_b))

    # Позиции: достоинство(+) / недостаток(-) / исход — для обоих вариантов; совет — как Карта Дня
    choice_kinds = ["positive", "negative", "neutral",
                    "positive", "negative", "neutral", "day"]

    user_last_tarot[user_id] = {
        "question": f"Вариант выбора: {essence}. Вариант 1: {option_a}. Вариант 2: {option_b}.",
        "deck_id": deck.deck_id,
        "drawn_ids": [(c.card_id, rev) for c, rev in drawn],
        "position_kinds": choice_kinds,
    }
    interpretation = await get_tarot_ai_interpretation(
        f"Вариант выбора: {essence}. Вариант 1: {option_a}. Вариант 2: {option_b}.",
        drawn,
        deck.name,
        choice_kinds,
        deck_id=deck.deck_id
    )
    if interpretation:
        await send_chunks_with_nav(message, interpretation, "tarot_question")
    else:
        await state.set_state(AppStates.waiting_tarot_retry_choice)
        await state.update_data(
            drawn_ids=[(c.card_id, rev) for c, rev in drawn],
            deck_id=deck.deck_id,
            question=f"Вариант выбора: {essence}. Вариант 1: {option_a}. Вариант 2: {option_b}.",
            position_kinds=choice_kinds,
            essence=essence,
            option_a=option_a,
            option_b=option_b,
        )
        await message.answer(
            "⚠️ Сервис ИИ временно недоступен. Нажмите кнопку ниже, чтобы повторить "
            "запрос с теми же вытянутыми картами.",
            reply_markup=tarot_kb.retry_tarot_keyboard()
        )

# ============================================================
# ВОПРОС ТАРО: текст вопроса → расклад → ИИ-интерпретация
# ============================================================


@dp.message(StateFilter(AppStates.waiting_tarot_question_text), F.text)
async def handle_question_text(message: types.Message, state: FSMContext):
    """Пользователь написал вопрос → выполняем расклад и отправляем вопрос + карты в ИИ."""
    data = await state.get_data()
    await state.clear()

    question = message.text.strip()
    spread_type = data.get("q_spread_type")
    deck_id = data.get("deck_id")
    user_id = message.from_user.id

    if len(question) < 5:
        await message.answer("🔮 Пожалуйста, опишите вопрос подробнее.")
        return

    deck = tarot.get_deck(deck_id) if deck_id else tarot.get_deck()
    if not deck or not deck.cards:
        await message.answer("⚠️ Колода недоступна.")
        return

    await message.answer(f"🔮 Тяну карты из колоды «{deck.name}»...")
    await _run_question_spread(message, spread_type, deck, user_id, question, state)

# ============================================================
# АСТРОЛОГИЯ: текст
# ============================================================


@dp.message(StateFilter(AppStates.waiting_astro_question), F.text)
async def handle_astro_question(message: types.Message, state: FSMContext):
    await state.clear()
    await process_astro_request(message, message.text)


@dp.message(F.text)
async def handle_default_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return
    await process_astro_request(message, message.text)

# ============================================================
# ПОВТОР ТОЛКОВАНИЯ (после ошибки ИИ)
# ============================================================


@dp.callback_query(F.data == "retry_tarot",
                   StateFilter(AppStates.waiting_tarot_retry,
                               AppStates.waiting_tarot_retry_choice))
async def retry_tarot(callback: types.CallbackQuery, state: FSMContext):
    """Повторяет запрос к LLM с теми же картами, что и в прошлый раз."""
    logger.info("🔘 Callback: retry_tarot")
    await callback.answer("🔄 Повторяю запрос к ИИ с теми же картами...")
    data = await state.get_data()
    current_state = await state.get_state()

    deck = tarot.get_deck(data["deck_id"])
    if not deck:
        await state.clear()
        await callback.message.answer("⚠️ Колода недоступна.",
                                      reply_markup=tarot_kb.main_menu_keyboard())
        return

    # Восстанавливаем список вытянутых карт по сохранённым card_id
    drawn = []
    for cid, rev in data["drawn_ids"]:
        card = deck.get_card(cid)
        if card:
            drawn.append((card, rev))
    if len(drawn) != len(data["drawn_ids"]):
        await state.clear()
        await callback.message.answer("⚠️ Не удалось восстановить карты. Начните расклад заново.",
                                      reply_markup=tarot_kb.main_menu_keyboard())
        return

    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
    interpretation = await get_tarot_ai_interpretation(
        data["question"], drawn, deck.name, data.get("position_kinds")
    )

    if interpretation:
        await state.clear()
        await send_chunks_with_nav(callback.message, interpretation, "tarot_question")
    else:
        # Снова неудача — оставляем состояние, показываем кнопку повтора
        await callback.message.answer(
            "⚠️ Снова не удалось получить толкование. Сервис ИИ перегружен. "
            "Попробуйте ещё раз через 1–2 минуты.",
            reply_markup=tarot_kb.retry_tarot_keyboard()
        )

# ============================================================
# ПЕРЕФРАЗИРОВАНИЕ
# ============================================================


@dp.callback_query(F.data == "rephrase")
async def handle_rephrase(callback: types.CallbackQuery):
    logger.info("🔘 Callback: rephrase")
    user_id = callback.from_user.id
    if user_id not in user_last_queries:
        await callback.answer("⚠️ История устарела. Задайте новый вопрос.", show_alert=True)
        return
    await callback.answer("🔄 Генерирую новый вариант...")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)

    saved_task = user_last_queries[user_id]
    rephrase_prompt = (
        f"{saved_task}\n\n[ИНСТРУКЦИЯ: Перефразируй предыдущий ответ. "
        f"Сохрани смыслы и факты, но используй другие формулировки.]"
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
        "⚠️ Я работаю только с текстом.\n\n"
        "Опишите показатель словами или пришлите строку из ZET.",
        parse_mode="Markdown"
    )


# ============================================================
# WEB-СЕРВЕР / KEEP-ALIVE
# ============================================================
async def handle_health_check(request):
    uptime_min = round((time.time() - APP_STARTED_AT) / 60, 1)
    html = f"""
    <html>
    <head><meta charset="utf-8"><title>12 Планет</title></head>
    <body style="font-family:sans-serif;text-align:center;padding-top:60px;">
        <h2>✅ Сервис работает</h2>
        <h3>Школа Астрологии «12 Планет»</h3>
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


# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    validate_settings()
    if not settings.IS_DEVELOPMENT:
        await start_web_server()
        asyncio.create_task(keep_alive_pinger())

    await bot.delete_webhook(drop_pending_updates=True)
    await setup_bot_ui()

    drawable = len(_drawable_decks())
    logger.info(f"🚀 Бот запущен в режиме: {settings.ENV}")
    logger.info("=" * 60)
    logger.info("Astro12AI + TAROT")
    logger.info(f"ENV: {settings.ENV}")
    logger.info(f"ИИ-модель: {model_name}")
    logger.info(f"Knowledge chunks: {len(documents)}")
    logger.info(f"Tarot decks: всего={len(tarot_decks)}, с картами={drawable}")
    logger.info("=" * 60)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
