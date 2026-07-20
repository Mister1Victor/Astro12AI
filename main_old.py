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
# сервиса — на неё и будем "стучаться" сами, чтобы не давать Render усыплять сервис.
SELF_URL = os.getenv("RENDER_EXTERNAL_URL",
                     "https://astro-bot-b8m8.onrender.com")
# 10 минут — с запасом до 15-минутного таймаута простоя Render
KEEP_ALIVE_INTERVAL = 3600
APP_STARTED_AT = time.time()

# 1. СТРИМИНГОВАЯ ЗАГРУЗКА И ОПТИМИЗАЦИЯ БАЗЫ ЗНАНИЙ

documents = load_knowledge_base()

logger.info(
    f"🔥 Успешно создано фрагментов: {len(documents)}"
)

astro_retriever = AstroRetriever(documents)

llm = create_llm()

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
            if "context" in response:
                stats = context_statistics(response["context"])
                logger.info("=" * 60)
                logger.info("КОНТЕКСТ RAG")
                logger.info(stats)
                logger.info("=" * 60)
            if "context" in response:
                logger.info("===== ИСПОЛЬЗОВАННЫЕ ДОКУМЕНТЫ =====")

                used = set()

            for doc in response["context"]:
                source = doc.metadata.get("source", "Неизвестно")

                if source not in used:
                    used.add(source)
                    logger.info(source)

            return response['answer']

        except Exception as e:
            logger.info(f"⚠️ Ошибка вызова Groq (Попытка {attempt+1}): {e}")
            await asyncio.sleep(3)
    return "❌ Извините, шлюз ИИ-интерпретации сейчас перегружен. Повторите отправку запроса через 5-10 минут."


def split_text_for_telegram(text: str, limit: int = 4000) -> list[str]:
    """
    Делит длинный ответ ИИ на части, укладывающиеся в лимит Telegram (4096 симв.),
    режет по границам абзацев/предложений, а не посимвольно — иначе можно разорвать
    Markdown-разметку (**жирный текст**) ровно на стыке двух сообщений и получить ошибку парсинга.
    """
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
        # Абзац сам длиннее лимита — режем по предложениям
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


async def safe_answer(message: types.Message, text: str, **kwargs):
    """
    Отправляет сообщение с Markdown-разметкой. Ответы модели иногда содержат символы
    (одиночные *, _, [ ] и т.п.), которые ломают Telegram-парсер Markdown — в этом случае
    бот не должен падать или молчать, а обязан отправить тот же текст без разметки.
    """
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
    if re.search(r"\d{2}\.\d{2}\.\d{4}", raw_text) or any(word in raw_text.lower() for word in ["родился", "родилась", "город", "время"]):
        redirect_text = (
            "⚠️ **Уведомление Школы Астрологии «12 Планет»**\n\n"
            "Вы ввели сырые данные рождения (дату/время/город). Как сообщалось в приветствии, наш бот "
            "специализирован на **высокоточной интерпретации положений**, а не на их расчете.\n\n"
            "С задачей построения карты и эфемерид безупречно справляются профессиональные программы (например, **ZET** или **Sotis**).\n\n"
            "Пожалуйста, постройте карту в вашей программе и пришлите текстовый вопрос (например, положение планеты в доме/знаке) "
            "или скопируйте текстовую строку аспекта из ZET, чтобы мы провели глубокий анализ по методике нашей Школы."
        )
        await message.answer(redirect_text, parse_mode="Markdown")
        return

    processed_query = parse_astrological_input(raw_text)

    # Сразу формируем запрос на комплексный анализ без выбора сфер
    final_task = f"Показатель: {processed_query}\nФокус анализа: Проанализируй данный показатель на основании ключевых слов Школы комплексно по всем фундаментальным сферам жизни."

    await message.answer(
        "🔮 Школа Астрологии 12 Планет анализирует фрагменты текстов... Формирую ответ...",
        parse_mode="Markdown"
    )
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    interpretation = await get_ai_interpretation(final_task)

    for chunk in split_text_for_telegram(interpretation):
        await safe_answer(message, chunk)


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
    """
    Пока процесс жив, каждые KEEP_ALIVE_INTERVAL секунд сам обращается к своему
    публичному URL. Render усыпляет бесплатный Web Service после ~15 минут без
    входящего HTTP-трафика — регулярный самопинг не даёт этому таймауту накопиться,
    пока сервис уже поднят. Это НЕ спасает от пробуждения "с нуля" (см. пояснение
    в чате), а лишь удерживает уже запущенный сервис активным.
    """
    await asyncio.sleep(30)  # даём приложению полностью подняться перед первым пингом
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
    """Кнопка меню (иконка ☰ слева от поля ввода) со списком команд — /start всегда под рукой."""
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
    logger.info(f"Documents: {len(documents)}")
    logger.info(f"Knowledge chunks: {len(documents)}")
    logger.info("=" * 60)
    try:
        await dp.start_polling(bot)

    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
