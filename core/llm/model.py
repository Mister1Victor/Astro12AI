from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings
from backend.logger import get_logger

logger = get_logger()


def create_llm():
    """
    Создание экземпляра языковой модели.

    Поддерживаемые провайдеры (задаются в .env через LLM_PROVIDER):
    - "groq" (по умолчанию): Быстрый, но с жесткими дневными лимитами.
    - "openrouter": Лучший выбор для бесплатного тестирования (модели с суффиксом :free).
    - "gemini": Огромные бесплатные лимиты и контекст (Gemini 1.5 Flash).
    """
    provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()

    # 🆕 Умный выбор модели по умолчанию в зависимости от провайдера
    if provider == "openrouter":
        default_model = "qwen/qwen-2.5-72b-instruct:free"
    elif provider == "gemini":
        default_model = "gemini-1.5-flash"
    else:
        default_model = "qwen/qwen3.6-27b"  # Актуальная модель на Groq [[1]]

    model_name = getattr(settings, "MODEL_NAME", default_model)

    # 🆕 Безопасное приведение типов с fallback на значения по умолчанию
    try:
        temperature = float(getattr(settings, "TEMPERATURE", 0.2))
        max_tokens = int(getattr(settings, "MAX_TOKENS", 4096))
    except (ValueError, TypeError):
        logger.warning(
            "⚠️ Неверный формат TEMPERATURE или MAX_TOKENS в настройках. Используются значения по умолчанию.")
        temperature = 0.2
        max_tokens = 4096

    logger.info(f"🤖 Инициализация LLM: Провайдер={provider}, Модель={model_name}, "
                f"Температура={temperature}, MaxTokens={max_tokens}")

    if provider == "openrouter":
        return ChatOpenAI(
            api_key=getattr(settings, "OPENROUTER_API_KEY",
                            ""),  # ✅ Обновлено на api_key
            base_url="https://openrouter.ai/api/v1",
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            # ✅ Обновлено на api_key
            api_key=getattr(settings, "GOOGLE_API_KEY", ""),
            model=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,                         # ✅ Верно для Gemini
        )

    else:
        # По умолчанию используем Groq (для обратной совместимости)
        return ChatGroq(
            api_key=getattr(settings, "GROQ_API_KEY", ""),
            model=model_name,  # model="qwen/qwen3.6-27b",
            temperature=temperature,
            # ✅ Отключаем режим рассуждения для скорости (поддерживается langchain_groq)
            reasoning_effort="none",
            # Ограничивает выборку лучшими 80% токенов
            top_p=0.80,
            # ✅ ИСПРАВЛЕНО: 1.5 было слишком агрессивно и могло ломать связность
            presence_penalty=0.2,
            max_tokens=max_tokens,
        )
