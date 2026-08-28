"""Inline-клавиатуры Таро и главного меню."""
from typing import List

from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.tarot.models import TarotDeck

SUIT_NAMES = {
    "major": "Старшие Арканы",
    "wands": "Жезлы",
    "cups": "Кубки",
    "swords": "Мечи",
    "pentacles": "Пентакли",
}


# ================= ГЛАВНОЕ МЕНЮ =================
def main_menu_keyboard():
    """Главное меню: Таро, Астрология 12, Карта Дня."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎴 Таро", callback_data="menu_tarot")
    kb.button(text="🪐 Астрология 12", callback_data="menu_astro")
    kb.button(text="🃏 Карта Дня", callback_data="menu_card_of_day")
    kb.adjust(2, 1)
    return kb.as_markup()


def back_to_main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


# ================= НАСТРОЙКА ПЕРЕВЁРНУТЫХ КАРТ =================
def reversed_setting_keyboard():
    """Выбор настройки перевёрнутых карт при первом входе в Таро."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, использовать перевёрнутые",
              callback_data="reversed:yes")
    kb.button(text="❌ Нет, только прямые", callback_data="reversed:no")
    kb.adjust(1)
    return kb.as_markup()


# ================= МЕНЮ ТАРО =================
def tarot_menu_keyboard():
    """Таро: Колоды, Расклады, Вопрос."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 Колоды", callback_data="tarot_decks")
    kb.button(text="📖 Расклады", callback_data="tarot_spreads")
    kb.button(text="❓ Вопрос", callback_data="tarot_question")
    kb.button(text="🔙 Назад", callback_data="back_to_main")
    kb.adjust(3, 1)
    return kb.as_markup()


# ================= КОЛОДЫ =================
def decks_list_keyboard(decks: List[TarotDeck]):
    """Список колод (для просмотра)."""
    kb = InlineKeyboardBuilder()
    for d in decks:
        kb.button(text=f"🎴 {d.name} · {d.cards_count}",
                  callback_data=f"deck_view:{d.deck_id}")
    kb.button(text="🔙 Назад", callback_data="menu_tarot")
    kb.adjust(1)
    return kb.as_markup()


def deck_categories_keyboard(deck_id: str):
    """Категории карт внутри колоды."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✨ Старшие Арканы (22)",
              callback_data=f"deck_arcana:{deck_id}:major")
    kb.button(text="🔥 Жезлы", callback_data=f"deck_arcana:{deck_id}:wands")
    kb.button(text="💧 Кубки", callback_data=f"deck_arcana:{deck_id}:cups")
    kb.button(text="🗡️ Мечи", callback_data=f"deck_arcana:{deck_id}:swords")
    kb.button(text="🪙 Пентакли",
              callback_data=f"deck_arcana:{deck_id}:pentacles")
    kb.button(text="🔙 К колодам", callback_data="tarot_decks")
    kb.adjust(1)
    return kb.as_markup()


def deck_cards_keyboard(deck_id: str, cards, title: str):
    """Список карт одной масти/аркана."""
    kb = InlineKeyboardBuilder()
    for c in cards:
        kb.button(
            text=c.name, callback_data=f"deck_card:{deck_id}:{c.card_id}")
    kb.button(text="🔙 Назад", callback_data=f"deck_view:{deck_id}")
    kb.adjust(2)
    return kb.as_markup()


def back_to_deck_keyboard(deck_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 К списку карт", callback_data=f"deck_view:{deck_id}")
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


# ================= КАРТА ДНЯ =================
def cod_decks_keyboard(decks: List[TarotDeck]):
    """Выбор колоды для Карты Дня."""
    kb = InlineKeyboardBuilder()
    for d in decks:
        kb.button(text=f"🎴 {d.name}", callback_data=f"cod_deck:{d.deck_id}")
    kb.button(text="🔙 Назад", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def card_of_day_keyboard(deck_id: str):
    """Экран Карты Дня: кнопка перемешивания."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔀 Перемешать и вытянуть карту",
              callback_data=f"cod_shuffle:{deck_id}")
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def card_result_keyboard(deck_id: str):
    """После вытягивания карты: перемешать ещё раз."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔀 Перемешать ещё раз",
              callback_data=f"cod_shuffle:{deck_id}")
    kb.button(text="🎴 Другая колода", callback_data="menu_card_of_day")
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


# ================= РАСКЛАДЫ =================
def spreads_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🃏 Одна карта", callback_data="spread:one")
    kb.button(text="🔮 Три карты (Прошлое-Настоящее-Будущее)",
              callback_data="spread:three")
    kb.button(text="🔙 Назад", callback_data="menu_tarot")
    kb.adjust(1)
    return kb.as_markup()


# ================= ВОПРОС (ВЫБОР РАСКЛАДА) =================
def tarot_question_menu_keyboard():
    """Меню выбора расклада для вопроса."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔮 Трёхкарточный (Прошлое-Настоящее-Будущее)",
              callback_data="q_spread:three")
    kb.button(text="✝️ Кельтский крест (10 карт)",
              callback_data="q_spread:celtic")
    kb.button(text="⚖️ Вариант выбора (два пути + совет)",
              callback_data="q_spread:choice")
    kb.button(text="🔙 Назад", callback_data="menu_tarot")
    kb.adjust(1)
    return kb.as_markup()
