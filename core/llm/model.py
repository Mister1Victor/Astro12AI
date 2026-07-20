from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings
from backend.logger import get_logger  # Добавлено для логирования

logger = get_logger()


def create_llm():
    """
    Создание экземпляра языковой модели.

    Поддерживаемые провайдеры (задаются в .env через LLM_PROVIDER):
    - "groq" (по умолчанию): Быстрый, но с жесткими дневными лимитами.
    - "openrouter": Лучший выбор для бесплатного тестирования (модели с суффиксом :free).
    - "gemini": Огромные бесплатные лимиты и контекст (Gemini 1.5 Flash).
    """

    # Получаем настройки с дефолтными значениями groq
    provider = getattr(settings, "LLM_PROVIDER", "openrouter").lower().strip()

    # Примеры корректных имен моделей:
    # Groq: "llama-3.3-70b-versatile", "qwen/qwen3.6-27b"
    # OpenRouter: "openai/gpt-4o", "qwen/qwen-2.5-72b-instruct:free"
    # Gemini: "gemini-1.5-flash", "gemini-1.5-pro"
    model_name = getattr(settings, "MODEL_NAME", "qwen3.6-27b")

    # ИСПРАВЛЕНО: было "с" (кириллица), стало "TEMPERATURE"
    temperature = float(getattr(settings, "TEMPERATURE", 0.1))

    logger.info(
        f"🤖 Инициализация LLM: Провайдер={provider}, Модель={model_name}, Температура={temperature}")

    if provider == "openrouter":
        # OpenRouter использует API, полностью совместимый с OpenAI
        return ChatOpenAI(
            openai_api_key=getattr(settings, "OPENROUTER_API_KEY", ""),
            # base_url - более современный параметр в langchain_openai
            base_url="https://openrouter.ai/api/v1",
            # model=model_name,
            model=cohere/north-mini-code: free,
            temperature=temperature,
        )

    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            google_api_key=getattr(settings, "GOOGLE_API_KEY", ""),
            model=model_name,
            temperature=temperature,
        )

    else:
        # По умолчанию используем Groq (для обратной совместимости)
        return ChatGroq(
            api_key=getattr(settings, "GROQ_API_KEY", ""),
            model=model_name,
            temperature=temperature,
        )
