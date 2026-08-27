# ================= НАСТРОЙКА ПЕРЕВЁРНУТЫХ КАРТ =================
def reversed_setting_keyboard():
    """Клавиатура выбора настройки перевёрнутых карт."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, использовать перевёрнутые",
              callback_data="reversed:yes")
    kb.button(text="❌ Нет, только прямые", callback_data="reversed:no")
    kb.adjust(1)
    return kb.as_markup()
