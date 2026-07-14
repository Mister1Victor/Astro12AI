from langchain_groq import ChatGroq
from backend.config import settings


def create_llm():
    """
    Создание экземпляра языковой модели.
    В дальнейшем здесь можно будет выбирать Groq, OpenAI,
    Ollama или локальную модель.
    """

    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.MODEL_NAME,
        temperature=settings.TEMPERATURE,
    )