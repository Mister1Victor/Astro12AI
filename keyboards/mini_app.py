"""Клавиатуры для Mini App и основных функций бота."""
import os

from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Публичный адрес: Render автоматически прокидывает RENDER_EXTERNAL_URL.
# Локально — фолбэк на прод-адрес Render.
SELF_URL = os.getenv("RENDER_EXTERNAL_URL",
                     "https://astro-bot-b8m8.onrender.com")
WEBAPP_URL = f"{SELF_URL}/webapp"


def main_menu_keyboard():
    """Главное меню: разделы + вход в Mini App + пробуждение сервера."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎴 Таро", callback_data="menu_tarot")
    kb.button(text="🪐 Астрология 12", callback_data="menu_astro")
    kb.button(text="🃏 Карта Дня", callback_data="menu_card_of_day")
    kb.button(text="✨ Интерактивный расклад",
              web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="🌙 Разбудить сервер", url=SELF_URL)
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def mini_app_menu_keyboard():
    """Меню с кнопками открытия Mini App (обе панели — секции внутри Mini App)."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔮 Открыть панель Таро", web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="🌟 Открыть панель Астрологии",
              web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def mini_app_repeat_keyboard():
    """Повторный вход в Mini App (например, после расклада)."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✨ Открыть Mini App ещё раз",
              web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def astrology_mini_app_input_keyboard():
    """Ввод параметров аспекта через Mini App (форма живёт внутри Mini App)."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🪐 Ввести параметры аспекта",
              web_app=WebAppInfo(url=WEBAPP_URL))
    kb.adjust(1)
    return kb.as_markup()
