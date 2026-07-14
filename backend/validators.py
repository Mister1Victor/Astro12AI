from backend.config import settings


def validate_settings():
    errors = []

    if not settings.TELEGRAM_TOKEN:
        errors.append("Не найден TELEGRAM_TOKEN")

    if not settings.GROQ_API_KEY:
        errors.append("Не найден GROQ_API_KEY")

    if errors:
        raise RuntimeError("\n".join(errors))
    