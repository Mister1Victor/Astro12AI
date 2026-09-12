"""Модуль обработки Tarot-запросов."""
import asyncio
import time
from typing import Dict, List, Optional

from aiogram import F, types
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backend.logger import get_logger
from core.tarot.service import TarotService, CELTIC_CROSS_POSITIONS, CHOICE_POSITIONS
from core.tarot import keyboards as tarot_kb
from core.tarot import render as tarot_render
from core.llm.model import create_llm
from core.prompts.tarot_prompt import TAROT_SYSTEM_PROMPT

logger = get_logger()

# Авторские колоды Школы
SCHOOL_DECK_IDS = {"author_deck_146", "author_deck"}


def _is_school_deck(deck_id=None, deck_name=None) -> bool:
    """Определяет авторскую колоду Школы по id ИЛИ по названию."""
    if deck_id and deck_id in SCHOOL_DECK_IDS:
        return True
    if deck_name and "12 Планет" in deck_name:
        return True
    return False


async def get_tarot_ai_interpretation(
    question: str,
    drawn,
    deck_name: str,
    position_kinds=None,
    deck_id=None,
    llm=None,
    astro_retriever=None
) -> Optional[str]:
    """
    Интерпретация расклада через LLM.
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
            f"Позиция {i + 1}: {card.name} ({orient}{astro}) —\n{meaning}"
        )
    cards_text = "\n".join(cards_desc)

    # Материалы Школы астрологии — только для авторских колод
    school_block = ""
    if _is_school_deck(deck_id, deck_name):
        entities_src = " ".join(
            f"{card.name} {card.astrology or ''}" for card, _ in drawn
        )
        if astro_retriever:
            school_block = astro_retriever.build_authority_context(entities_src)
        logger.info(
            f"🏫 Авторская колода «{deck_name}»: извлечено из карт: {entities_src[:120]}..."
        )
        if school_block:
            logger.info(
                "🏫 Таро(авторская колода): приложен контекст Школы (планеты/знаки)"
            )
        else:
            logger.warning(
                "⚠️ Авторская колода, но контекст Школы пуст (не извлечены сущности)"
            )
    else:
        logger.info(
            f"ℹ️ Колода «{deck_name}» не авторская — контекст Школы не прикладывается"
        )

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
                    [("system", TAROT_SYSTEM_PROMPT), ("human", human)]
                )
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
    return None


async def send_spread_cards_visual(msg: types.Message, deck, drawn, positions, bot) -> int:
    """
    Отправляет альбом картинок расклада (до 10 фото на альбом).
    Возвращает число отправленных изображений.
    """
    items = tarot_render.spread_cards_visual(deck, drawn, positions)
    media = []
    for it in items:
        if it["path"]:
            from aiogram.types import FSInputFile, InputMediaPhoto
            media.append(InputMediaPhoto(media=FSInputFile(it["path"]), caption=it["caption"]))

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


def split_text_for_telegram(text: str, limit: int = 4000) -> List[str]:
    """Разделение текста на части для отправки в Telegram."""
    if len(text) <= limit:
        return [text]
    import re
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


async def send_chunks_with_nav(msg: types.Message, text: str, back_callback: str):
    """Отправка текста по фрагментам; к ПОСЛЕДНЕМУ фрагменту крепит клавиатуру Назад/Главное меню."""
    chunks = split_text_for_telegram(text, 3900)
    kb = tarot_kb.spread_done_keyboard(back_callback)
    for i, chunk in enumerate(chunks):
        await msg.answer(chunk, reply_markup=(kb if i == len(chunks) - 1 else None))


async def safe_answer(message: types.Message, text: str, **kwargs):
    """Безопасная отправка сообщения."""
    try:
        await message.answer(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest:
        await message.answer(text, **kwargs)
