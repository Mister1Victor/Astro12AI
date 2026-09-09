"""Клавиатуры для Mini App и основных функций бота."""
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardButton


def main_menu_keyboard():
    """Главное меню бота с кнопкой Mini App."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎴 Таро", callback_data="menu_tarot")
    kb.button(text="🪐 Астрология 12", callback_data="menu_astro")
    kb.button(text="🃏 Карта Дня", callback_data="menu_card_of_day")
    # Кнопка для запуска Mini App
    kb.button(text="✨ Интерактивный расклад", web_app={"url": "https://your-domain.com/webapp"})
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def mini_app_menu_keyboard(webapp_url: str):
    """Меню с кнопкой запуска Mini App."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔮 Открыть панель Таро", web_app={"url": f"{webapp_url}/tarot"})
    kb.button(text="🌟 Открыть панель Астрологии", web_app={"url": f"{webapp_url}/astrology"})
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def tarot_mini_app_result_keyboard(spread_type: str, cards_data: str):
    """
    Клавиатура для отправки результатов из Mini App в бот.
    cards_data: JSON-строка с данными карт.
    """
    kb = InlineKeyboardBuilder()
    # Передаём данные через callback_data (до 64 байт) или через web_app
    kb.button(text="✅ Подтвердить расклад", callback_data=f"miniapp_tarot:{spread_type}:{cards_data[:50]}")
    kb.adjust(1)
    return kb.as_markup()


def astrology_mini_app_input_keyboard():
    """Клавиатура для ввода астрологических данных через Mini App."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🪐 Ввести параметры аспекта", web_app={"url": "https://your-domain.com/webapp/astrology"})
    kb.adjust(1)
    return kb.as_markup()
