from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.config import settings


def create_llm():
    """
    Создание экземпляра языковой модели.

    Поддерживаемые провайдеры (задаются в .env через LLM_PROVIDER):
    - "groq" (по умолчанию): Быстрый, но с жесткими дневными лимитами.
    - "openrouter": Лучший выбор для бесплатного тестирования (модели с суффиксом :free).
    - "gemini": Огромные бесплатные лимиты и контекст (Gemini 1.5 Flash).
    """

    # Получаем настройки с дефолтными значениями, чтобы код не падал,
    # если какая-то переменная еще не добавлена в .env
    provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()
    # llama-3.3-70b-versatile openai/gpt-oss-120b
    model_name = getattr(settings, "MODEL_NAME", "llama-3.3-70b-versatile")
    temperature = getattr(settings, "с", 0.1)

    if provider == "openrouter":
        # OpenRouter использует API, полностью совместимый с OpenAI
        return ChatOpenAI(
            openai_api_key=getattr(settings, "OPENROUTER_API_KEY", ""),
            openai_api_base="https://openrouter.ai/api/v1",
            model=model_name,
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
