# -*- coding: utf-8 -*-
"""
Авторская колода «12 Планет» — 146 карт.
Модуль работы с данными карт:
  - загрузка JSON, сгенерированного oracle_generator.py;
  - формирование текста для подписи к изображению карты в Telegram;
  - построение контекста для LLM в зависимости от позиции карты в раскладе.

Правила использования по позиции:
  - "plus" / "dignity"  → Значение + Совет
  - "minus" / "flaw"    → Предупреждение
  - "day"               → Значение + Совет + Предупреждение
  - "neutral"           → всё вместе (по умолчанию)
"""

import json
import os
import random
from typing import Dict, List, Optional

# =============================================================
# ПУТИ
# =============================================================
# Путь к папке с колодой (относительно корня проекта)
DECK_DIR = os.path.join("Astro12AI", "data", "tarot",
                        "decks", "author_deck_146")
CARDS_JSON = os.path.join(DECK_DIR, "cards_data.json")

# Глобальный словарь с данными карт
CARDS_DATA: Dict[str, dict] = {}


# =============================================================
# ЗАГРУЗКА
# =============================================================
def load_deck(json_path: Optional[str] = None) -> Dict[str, dict]:
    """Загружает данные карт из JSON. Возвращает словарь."""
    global CARDS_DATA
    path = json_path or CARDS_JSON
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Файл данных колоды не найден: {path}. "
            f"Сначала запустите oracle_generator.py для генерации карт и JSON."
        )
    with open(path, "r", encoding="utf-8") as f:
        CARDS_DATA = json.load(f)
    return CARDS_DATA


def ensure_loaded():
    """Гарантирует, что колода загружена."""
    if not CARDS_DATA:
        load_deck()


# =============================================================
# ПОЛУЧЕНИЕ ДАННЫХ КАРТЫ
# =============================================================
def get_card(card_id: str) -> Optional[dict]:
    """Возвращает данные карты по ID (строка или число)."""
    ensure_loaded()
    return CARDS_DATA.get(str(card_id))


def get_card_image_path(card_id: str) -> str:
    """Возвращает абсолютный путь к изображению карты."""
    card = get_card(card_id)
    if not card:
        raise ValueError(f"Карта {card_id} не найдена в колоде")
    return os.path.join(DECK_DIR, card["image"])


def get_all_card_ids() -> List[str]:
    """Возвращает список всех ID карт в колоде."""
    ensure_loaded()
    return list(CARDS_DATA.keys())


# =============================================================
# ЗАГОЛОВОК КАРТЫ
# =============================================================
def _get_card_title(card: dict) -> str:
    """Формирует человекочитаемый заголовок карты."""
    if card.get("type") == "eclipse":
        return card.get("title", "ЗАТМЕНИЕ")
    planet = card.get("planet", "")
    sign = card.get("sign", "")
    ruler_mark = " (управитель знака)" if card.get("is_ruler") else ""
    return f"{planet} в знаке {sign}{ruler_mark}"


# =============================================================
# ФОРМАТИРОВАНИЕ ТЕКСТА ДЛЯ TELEGRAM (под изображением)
# =============================================================
def format_card_caption(card_id: str) -> str:
    """
    Полный текст для подписи к изображению карты в Telegram,
    когда пользователь запросил просто карту (не расклад).
    Содержит Значение + Совет + Предупреждение.
    """
    card = get_card(card_id)
    if not card:
        return ""

    title = _get_card_title(card)
    lines = [f"🔮 {title}", ""]

    if card.get("type") == "eclipse":
        lines += [
            f"💫 Значение: {card['meaning']}",
            "",
            f"💡 Совет: {card['advice']}",
            "",
            f"⚠️ Предупреждение: {card['warning']}",
        ]
    else:
        lines += [
            f"💫 Значение: {card['meaning']}",
            "",
            f"💡 Совет: {card['advice']}",
            "",
            f"⚠️ Предупреждение: {card['warning']}",
        ]
        if card.get("is_ruler"):
            lines += ["", f"👑 Планета управляет этим знаком — её сила здесь максимальна."]

    return "\n".join(lines)


# =============================================================
# ФОРМАТИРОВАНИЕ ПО ПОЗИЦИИ В РАСКЛАДЕ
# =============================================================
def format_card_for_position(card_id: str, position_type: str) -> str:
    """
    Форматирует текст карты в зависимости от позиции в раскладе.

    position_type:
      - "plus" / "dignity"  → Значение + Совет
      - "minus" / "flaw"    → только Предупреждение
      - "day"               → Значение + Совет + Предупреждение (карта дня)
      - "neutral" / другое  → всё вместе
    """
    card = get_card(card_id)
    if not card:
        return ""

    title = _get_card_title(card)
    meaning = card.get("meaning", "")
    advice = card.get("advice", "")
    warning = card.get("warning", "")

    if position_type in ("plus", "dignity"):
        return "\n".join([
            f"✨ {title}",
            "",
            f"💫 Значение: {meaning}",
            "",
            f"💡 Совет: {advice}",
        ])

    if position_type in ("minus", "flaw"):
        return "\n".join([
            f"⚠️ {title}",
            "",
            f"🔮 Предупреждение: {warning}",
        ])

    if position_type == "day":
        return "\n".join([
            f"🌟 {title} — Карта дня",
            "",
            f"💫 Значение: {meaning}",
            "",
            f"💡 Совет: {advice}",
            "",
            f"⚠️ Предупреждение: {warning}",
        ])

    # neutral
    return format_card_caption(card_id)


# =============================================================
# КОНТЕКСТ ДЛЯ LLM
# =============================================================
def build_llm_context(card_id: str, position_type: str,
                      user_question: str = "") -> str:
    """
    Строит контекст для LLM с учётом позиции карты.
    В зависимости от позиции передаются только релевантные блоки:
      - plus/dignity  → Значение + Совет
      - minus/flaw    → Предупреждение
      - day           → все три блока
    """
    card = get_card(card_id)
    if not card:
        return ""

    title = _get_card_title(card)
    meaning = card.get("meaning", "")
    advice = card.get("advice", "")
    warning = card.get("warning", "")

    if position_type in ("plus", "dignity"):
        content = f"Значение: {meaning}\nСовет: {advice}"
        instruction = (
            "Карта выпала в положительной позиции (плюс/достоинство выбора). "
            "Раскрой значение и совет карты в контексте вопроса клиента."
        )
    elif position_type in ("minus", "flaw"):
        content = f"Предупреждение: {warning}"
        instruction = (
            "Карта выпала в отрицательной позиции (минус/недостаток выбора). "
            "Раскрой предупреждение карты в контексте вопроса клиента."
        )
    elif position_type == "day":
        content = (
            f"Значение: {meaning}\n"
            f"Совет: {advice}\n"
            f"Предупреждение: {warning}"
        )
        instruction = (
            "Это карта дня. Раскрой и совет, и предупреждение карты "
            "в контексте текущего дня."
        )
    else:
        content = (
            f"Значение: {meaning}\n"
            f"Совет: {advice}\n"
            f"Предупреждение: {warning}"
        )
        instruction = "Раскрой значение карты в контексте вопроса клиента."

    parts = [f"Карта: {title}", content, "", instruction]
    if user_question:
        parts += ["", f"Вопрос клиента: {user_question}"]

    return "\n".join(parts)


# =============================================================
# СЛУЧАЙНЫЙ ВЫБОР КАРТ
# =============================================================
def draw_cards(count: int, exclude: Optional[List[str]] = None) -> List[str]:
    """Тянет `count` случайных карт из колоды без повторений."""
    ensure_loaded()
    exclude = set(str(x) for x in (exclude or []))
    available = [cid for cid in CARDS_DATA.keys() if cid not in exclude]
    if count > len(available):
        count = len(available)
    return random.sample(available, count)


def draw_single_card(exclude: Optional[List[str]] = None) -> str:
    """Тянет одну случайную карту."""
    ids = draw_cards(1, exclude=exclude)
    return ids[0] if ids else ""


# =============================================================
# АВТОЗАГРУЗКА ПРИ ИМПОРТЕ
# =============================================================
try:
    load_deck()
except FileNotFoundError:
    # Данные ещё не сгенерированы — это нормально при первом запуске
    pass
