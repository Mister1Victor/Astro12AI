"""Модуль обработки астрологических запросов."""
import re
from typing import Dict, List

from aiogram import F, types
from aiogram.filters import Command, StateFilter
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backend.logger import get_logger
from core.rag.engine import AstroRetriever
from core.prompts.system_prompt import SYSTEM_PROMPT

logger = get_logger()

ZODIAC_MAP = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы", "Can": "Рак",
    "Leo": "Лев", "Vir": "Дева", "Lib": "Весы", "Sco": "Скорпион",
    "Sgr": "Стрелец", "Cap": "Козерог", "Aqr": "Водолей", "Psc": "Рыбы"
}


def parse_astrological_input(text: str) -> str:
    """Парсинг астрологических запросов из ZET."""
    parsed_parts = []

    # Парсинг аспектов
    aspect_pattern = (
        r"([а-яА-Я\w\s\-]+?)\s+"
        r"([а-яА-Я\w\-]+)\s*"
        r"([><])\s*"
        r"[\d°\'\"]+\s*"
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

    # Парсинг куспидов домов
    cusp_pattern = (
        r"\b(II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|I)\s+"
        r"[\d°\'\".,\s]+\s*"
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


async def process_astro_request(
    message: types.Message,
    raw_text: str,
    rag_chain,
    astro_retriever: AstroRetriever,
    bot
):
    """Обработка астрологического запроса пользователя."""
    raw_lower = raw_text.lower()

    # Проверка на данные рождения
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

    # Проверка на запрещённые объекты
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

    await message.answer(
        "🔮 Школа Астрологии 12 Планет анализирует... Формируется ответ...",
        parse_mode="Markdown"
    )
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Вызов RAG через переданный chain
    try:
        response = rag_chain.invoke({"input": final_task})
        interpretation = response.get("answer", "")
        
        if hasattr(interpretation, "content"):
            interpretation = interpretation.content
        
        if not interpretation or len(interpretation.strip()) < 20:
            await message.answer("⚠️ Модель вернула пустой ответ. Попробуйте перефразировать.")
            return

        # Отправка ответа частями
        chunks = split_text_for_telegram(interpretation)
        sent_texts = set()
        for chunk in chunks:
            chunk_stripped = chunk.strip()
            if chunk_stripped and chunk_stripped not in sent_texts:
                await safe_answer(message, chunk_stripped, reply_markup=get_rephrase_keyboard())
                sent_texts.add(chunk_stripped)

    except Exception as e:
        logger.error(f"❌ Ошибка при получении астрологической интерпретации: {e}")
        await message.answer("❌ Произошла ошибка при анализе. Попробуйте позже.")


def split_text_for_telegram(text: str, limit: int = 4000) -> List[str]:
    """Разделение текста на части для отправки в Telegram."""
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
    """Клавиатура для перефразирования ответа."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Перефразировать ответ", callback_data="rephrase")
    kb.adjust(1)
    return kb.as_markup()


async def safe_answer(message: types.Message, text: str, **kwargs):
    """Безопасная отправка сообщения с fallback на Markdown."""
    try:
        await message.answer(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest:
        await message.answer(text, **kwargs)
