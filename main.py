from backend.logger import get_logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from core.knowledge.loader import load_knowledge_base
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
import os
import re
import time
import asyncio
import aiohttp

from typing import Dict

from core.prompts.system_prompt import SYSTEM_PROMPT
from core.rag.engine import AstroRetriever
from core.rag.context import context_statistics
from core.llm.model import create_llm
from backend.config import settings
from dotenv import load_dotenv
from backend.validators import validate_settings

load_dotenv()
ENV = os.getenv("ENV", "production").lower()

logger = get_logger()
logger.info("=== ИНИЦИАЛИЗАЦИЯ ПРОДАКШН АСТРО-БОТА ===")

# Render автоматически прокидывает переменную RENDER_EXTERNAL_URL с публичным адресом
SELF_URL = os.getenv("RENDER_EXTERNAL_URL",
                     "https://astro-bot-b8m8.onrender.com")
KEEP_ALIVE_INTERVAL = 3600
APP_STARTED_AT = time.time()

# 1. ЗАГРУЗКА И ОПТИМИЗАЦИЯ БАЗЫ ЗНАНИЙ
documents = load_knowledge_base()
logger.info(f"🔥 Успешно создано фрагментов: {len(documents)}")

astro_retriever = AstroRetriever(documents)
llm = create_llm()

# Извлекаем название модели для логирования из настроек
model_name = getattr(settings, "MODEL_NAME", "Неизвестная модель")
logger.info(f"🤖 Используемая ИИ-модель: {model_name}")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{input}")
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(
    astro_retriever.get_retriever(),
    question_answer_chain
)

bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher()
# 🆕 Хранилище последнего запроса для каждого пользователя (для кнопки перефразирования)
user_last_queries: Dict[int, str] = {}

ZODIAC_MAP = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы", "Can": "Рак",
    "Leo": "Лев", "Vir": "Дева", "Lib": "Весы", "Sco": "Скорпион",
    "Sgr": "Стрелец", "Cap": "Козерог", "Aqr": "Водолей", "Psc": "Рыбы"
}


def parse_astrological_input(text: str) -> str:
    pattern = r"([а-яА-Я\w\s\-]+)\s+([а-яА-Я\w\-]+)\s*>\s*(\d+°\d+\'?)\s*<\s*(\d+)([a-zA-Z]{3})(\d+)\s*-\s*(\d+)([a-zA-Z]{3})(\d+)"
    match = re.search(pattern, text)
    if match:
        aspect_type = match.group(1).strip()
        planets = match.group(2).strip()
        exact_angle = match.group(3)
        p1_deg = match.group(4)
        p1_sign = ZODIAC_MAP.get(match.group(5), match.group(5))
        p2_deg = match.group(7)
        p2_sign = ZODIAC_MAP.get(match.group(8), match.group(8))
        return (
            f"Сходящийся напряженный аспект {aspect_type} между {planets} (точное расстояние {exact_angle}). "
            f"Первая планета находится в {p1_deg} градусах знака {p1_sign}, вторая планета — в {p2_deg} градусах знака {p2_sign}."
        )
    return text


async def get_ai_interpretation(query: str) -> str:
    for attempt in range(3):
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: rag_chain.invoke({"input": query}))

            # Логирование контекста RAG
            if "context" in response:
                stats = context_statistics(response["context"])
                logger.info("=" * 60)
                logger.info("КОНТЕКСТ RAG")
                logger.info(stats)
                logger.info("=" * 60)

                logger.info("===== ИСПОЛЬЗОВАННЫЕ ДОКУМЕНТЫ =====")
                used = set()
                for doc in response["context"]:
                    source = doc.metadata.get("source", "Неизвестно")
                    if source not in used:
                        used.add(source)
                        logger.info(source)

            # 🆕 Исправленное логирование токенов (извлекаем из AIMessage)
            answer_msg = response.get("answer")
            if answer_msg:
                # Вариант 1: через response_metadata (старые версии LangChain / некоторые провайдеры)
                if hasattr(answer_msg, "response_metadata"):
                    usage = answer_msg.response_metadata.get("token_usage", {})
                    if usage:
                        logger.info(f"📊 Токены: prompt={usage.get('prompt_tokens', 'N/A')}, "
                                    f"completion={usage.get('completion_tokens', 'N/A')}, "
                                    f"total={usage.get('total_tokens', 'N/A')}")
                # Вариант 2: через usage_metadata (современный стандарт LangChain)
                elif hasattr(answer_msg, "usage_metadata"):
                    usage = answer_msg.usage_metadata
                    logger.info(f"📊 Токены: input={usage.get('input_tokens', 'N/A')}, "
                                f"output={usage.get('output_tokens', 'N/A')}, "
                                f"total={usage.get('total_tokens', 'N/A')}")

            return response['answer']

        except Exception as e:
            logger.warning(f"⚠️ Ошибка вызова ИИ (Попытка {attempt+1}): {e}")
            await asyncio.sleep(3)

    return "❌ Извините, шлюз ИИ-интерпретации сейчас перегружен. Повторите отправку запроса через 5-10 минут."


def split_text_for_telegram(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]

    parts, current = [], ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
            current = ""
        if len(paragraph) <= limit:
            current = paragraph
            continue

        for sentence in re.split(r"(?<=[.!?]) ", paragraph):
            candidate = f"{current} {sentence}" if current else sentence
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    parts.append(current)
                current = sentence
    if current:
        parts.append(current)
    return parts


def get_rephrase_keyboard():
    """Создает inline-клавиатуру с кнопкой перефразирования"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Перефразировать ответ", callback_data="rephrase")
    builder.adjust(1)
    return builder.as_markup()


async def safe_answer(message: types.Message, text: str, **kwargs):
    try:
        await message.answer(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest:
        await message.answer(text, **kwargs)


@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "🔮 **Приветствую вас в интеллектуальном пространстве Школы Астрологии «12 Планет»!**\n\n"
        "В отличие от стандартных ботов, мы полностью **отказались от встроенных математических расчетов** "
        "координат, городов и эфемерид внутри мессенджера. Опыт показывает, что с расчетом точной долготы планет "
        "и куспидов домов идеально справляются специализированные профессиональные программы — такие как **ZET** или **Sotis**.\n\n"
        "🎯 **Наша миссия — чистая, глубокая и бескомпромиссная интерпретация.**\n\n"
        "Я обучен строго на закрытой базе знаний, методичках, книгах и лекциях нашей Школы. "
        "Я готов расшифровать для вас абсолютно любой астрологический показатель.\n\n"
        "📝 **Как отправить запрос?**\n"
        "• **Обычным текстом**, например: _«Что означает Сатурн в Деве в 4 доме в квадратуре с Нептуном в Стрельце в 6 доме?»_\n"
        "• **Прямым логом (копипастом) из программы ZET**, например:\n"
        "`Квадрат Сатурн-Нептун  > 91°19'<  20Vir16 - 21Sgr36`\n\n"
        "👉 Введите ваш вопрос или скопируйте строку аспектов из ZET ниже:\n\n"
        "ℹ️ Бот работает на бесплатном сервере: если он не отвечает больше минуты — вероятно, "
        "сервер «уснул» после простоя. Нажмите кнопку ниже, подождите ~40–60 секунд, пока откроется "
        "страница, и повторите команду /start."
    )
    wake_kb = InlineKeyboardBuilder()
    wake_kb.button(text="🌙 Разбудить сервер", url=SELF_URL)
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=wake_kb.as_markup())


@dp.message(F.text)
async def handle_user_input(message: types.Message):
    raw_text = message.text

    # Фильтр сырых данных рождения
    if re.search(r"\d{2}\.\d{2}\.\d{4}", raw_text) or any(word in raw_text.lower() for word in ["родился", "родилась", "город", "время"]):
        redirect_text = (
            "⚠️ **Уведомление Школы Астрологии «12 Планет»**\n\n"
            "Вы ввели данные рождения (дату/время/город). Как сообщалось в приветствии, наш бот "
            "специализирован на **высокоточной интерпретации положений**, а не на их расчете.\n\n"
            "С задачей построения карты и эфемерид безупречно справляются профессиональные программы (например, **ZET** или **Sotis**).\n\n"
            "Пожалуйста, постройте карту в вашей программе и пришлите текстовый вопрос (например, положение планеты в доме/знаке) "
            "или скопируйте текстовую строку аспекта из ZET, чтобы мы провели глубокий анализ по методике нашей Школы."
        )
        await message.answer(redirect_text, parse_mode="Markdown")
        return

    # 🆕 Фильтр слишком коротких запросов (экономия токенов)
    if len(raw_text.strip()) < 10:
        await message.answer("🔮 Пожалуйста, опишите астрологический показатель подробнее (например, скопируйте аспект из ZET или задайте конкретный вопрос).")
        return

    processed_query = parse_astrological_input(raw_text)
    final_task = f"Показатель: {processed_query}\nЗадача: Комплексный анализ по всем фундаментальным сферам."

    # 🆕 Сохраняем запрос пользователя для возможности перефразирования
    user_last_queries[message.from_user.id] = final_task

    await message.answer(
        "🔮 Высшая Школа Астрологии 12 Планет анализирует фрагменты текстов... Формирую ответ...",
        parse_mode="Markdown"
    )
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    interpretation = await get_ai_interpretation(final_task)

    # 🆕 Добавляем reply_markup=get_rephrase_keyboard() к каждому фрагменту (или к последнему)
    for chunk in split_text_for_telegram(interpretation):
        await safe_answer(message, chunk, reply_markup=get_rephrase_keyboard())


@dp.callback_query(F.data == "rephrase")
async def handle_rephrase(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # Проверяем, есть ли сохраненный запрос
    if user_id not in user_last_queries:
        await callback.answer("⚠️ История запроса устарела. Пожалуйста, задайте новый вопрос.", show_alert=True)
        return

    # Убираем спиннер загрузки на кнопке
    await callback.answer("🔄 Генерирую новый вариант...")

    # Показываем действие "печатает"
    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)

    # Берем сохраненный запрос и добавляем инструкцию для LLM перефразировать ответ
    saved_task = user_last_queries[user_id]
    rephrase_prompt = f"{saved_task}\n\n[ИНСТРУКЦИЯ: Перефразируй предыдущий ответ. Сохрани все астрологические смыслы, факты и выводы из контекста, но используй другие формулировки, структуру предложений и абзацев, чтобы текст воспринимался свежо.]"

    # Вызываем ИИ с модифицированным промптом
    new_interpretation = await get_ai_interpretation(rephrase_prompt)

    # Отправляем новый ответ с той же кнопкой (чтобы можно было перефразировать еще раз)
    for chunk in split_text_for_telegram(new_interpretation):
        await safe_answer(callback.message, chunk, reply_markup=get_rephrase_keyboard())


@dp.message()
async def handle_non_text_input(message: types.Message):
    await message.answer(
        "⚠️ Я работаю только с текстовыми запросами.\n\n"
        "Пожалуйста, опишите словами астрологический показатель или пришлите текстовую строку "
        "аспекта, скопированную из программы **ZET**.",
        parse_mode="Markdown"
    )


async def handle_health_check(request):
    uptime_min = round((time.time() - APP_STARTED_AT) / 60, 1)
    html = f"""
    <html>
      <head><meta charset="utf-8"><title>12 Планет — Астро-бот</title></head>
      <body style="font-family: sans-serif; text-align:center; padding-top: 60px;">
        <h2>✅ Сервис проснулся и работает</h2>
        <h3>Высшая Школа Астрологии «12 Планет» — ИИ-интерпретатор</h3>
        <p>Аптайм текущего инстанса: {uptime_min} мин.</p>
        <h3>Можете вернуться в Telegram и отправить /start ещё раз.</h3>
      </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def keep_alive_pinger():
    await asyncio.sleep(30)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        while True:
            try:
                async with session.get(SELF_URL) as resp:
                    logger.info(f"🔁 Self-ping OK: {resp.status}")
            except Exception as e:
                logger.info(f"⚠️ Self-ping не удался: {e}")
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()


async def setup_bot_ui():
    await bot.set_my_commands([
        BotCommand(command="start",
                   description="🔄 Перезапустить бота / главное меню"),
    ])
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def main():
    validate_settings()
    if not settings.IS_DEVELOPMENT:
        await start_web_server()
        asyncio.create_task(keep_alive_pinger())

    await bot.delete_webhook(drop_pending_updates=True)
    await setup_bot_ui()

    logger.info(f"🚀 Бот запущен в режиме: {settings.ENV}")
    logger.info("=" * 60)
    logger.info("Astro12AI")
    logger.info(f"ENV: {settings.ENV}")
    logger.info(f"ИИ-модель: {model_name}")
    logger.info(f"Documents: {len(documents)}")
    logger.info(f"Knowledge chunks: {len(documents)}")
    logger.info("=" * 60)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
