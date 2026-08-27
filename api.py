from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time

# Импортируем вашу существующую логику
from core.knowledge.loader import load_knowledge_base
from core.prompts.system_prompt import SYSTEM_PROMPT
from core.rag.engine import AstroRetriever
from core.llm.model import create_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

app = FastAPI(title="Astro12 & Tarot AI API")

# Разрешаем запросы с фронтенда (Web/Mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать домены вашего приложения
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. ИНИЦИАЛИЗАЦИЯ RAG (как в вашем main.py)
documents = load_knowledge_base()
astro_retriever = AstroRetriever(documents)
llm = create_llm()

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}")
])
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(astro_retriever, question_answer_chain)

# Функция парсинга ZET (копируем из вашего main.py)


def parse_astrological_input(text: str) -> str:
    # ... (здесь должен быть ваш код парсинга аспектов и куспидов из main.py) ...
    return text.strip()

# Модели данных для запросов


class AIRequest(BaseModel):
    question: str
    mode: str  # "astro" или "tarot"
    lang: str = "ru"
    # Для Таро в будущем добавим: deck: str, spread: str


@app.post("/api/ask")
async def ask_ai(req: AIRequest):
    start_time = time.time()

    if req.mode == "astro":
        processed_query = parse_astrological_input(req.question)
        # ИСПОЛЬЗУЕМ ВАШУ ОПТИМИЗАЦИЮ ИЗ ПЛАНА (Изменение 4)
        task_hint = astro_retriever.build_task_hint(processed_query)
        final_task = f"Показатель: {processed_query}\nЗадача: {task_hint}."
    elif req.mode == "tarot":
        # В будущем сюда подтянутся данные выбранной колоды и расклада
        final_task = f"Вопрос по Таро: {req.question}. Задача: Глубокая интерпретация карт."
    else:
        return {"error": "Unknown mode"}

    try:
        # Запускаем синхронный LangChain в асинхронном потоке
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: rag_chain.invoke({"input": final_task}))

        elapsed = round(time.time() - start_time, 2)
        return {
            "answer": response.get("answer", ""),
            "time": elapsed,
            "lang": req.lang
        }
    except Exception as e:
        return {"error": str(e)}
