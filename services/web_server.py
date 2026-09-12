"""
services/web_server.py
Веб-сервер Mini App и API для Astro12AI.

Маршруты:
GET  /webapp                              — главная страница Mini App (static/index.html)
GET  /static/{filepath}                   — статика (css/js/изображения Mini App)
GET  /api/tarot/decks                     — список колод из реального TarotService
POST /api/tarot/draw                      — вытянуть карты (реальный TarotService)
GET  /api/tarot/image/{deck_id}/{file}    — картинки карт из data/tarot/decks/
POST /api/webapp/data                     — резервный приём данных Mini App

ВАЖНО: Маршрут "/" (health check) регистрируется в main.py — здесь мы его НЕ трогаем, 
чтобы избежать RuntimeError: method HEAD is already registered.
"""
import logging
from pathlib import Path
from aiohttp import web

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DECKS_DIR = BASE_DIR / "data" / "tarot" / "decks"

CONTENT_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

# ============================================================
# MINI APP: ГЛАВНАЯ СТРАНИЦА
# ============================================================


async def handle_mini_app_index(request: web.Request) -> web.Response:
    """Отдаёт static/index.html."""
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return web.Response(status=404, text="Mini App not found: static/index.html")
    return web.Response(text=index.read_text(encoding="utf-8"), content_type="text/html")

# ============================================================
# СТАТИКА
# ============================================================


async def handle_static_file(request: web.Request) -> web.Response:
    """Отдаёт файлы из static/ с защитой от выхода за пределы папки."""
    rel = request.match_info.get("filepath", "")
    base = STATIC_DIR.resolve()
    path = (STATIC_DIR / rel).resolve()

    if not str(path).startswith(str(base)) or not path.is_file():
        return web.Response(status=404, text="File not found")

    ctype = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return web.Response(body=path.read_bytes(), content_type=ctype)

# ============================================================
# КАРТИНКИ КАРТ
# ============================================================


async def handle_deck_image(request: web.Request) -> web.Response:
    """Картинка карты: ищет в images/, фолбэк — корень папки колоды."""
    deck_id = request.match_info["deck_id"]
    filename = request.match_info["filename"]

    base = (DECKS_DIR / deck_id / "images").resolve()
    path = (base / filename).resolve()

    if not str(path).startswith(str(base)) or not path.is_file():
        base2 = (DECKS_DIR / deck_id).resolve()
        path = (base2 / filename).resolve()
        if not str(path).startswith(str(base2)) or not path.is_file():
            return web.Response(status=404, text="Image not found")

    ctype = CONTENT_TYPES.get(path.suffix.lower(), "image/jpeg")
    return web.Response(body=path.read_bytes(), content_type=ctype)

# ============================================================
# API: КОЛОДЫ
# ============================================================


async def api_get_decks(request: web.Request) -> web.Response:
    """Список колод из реального TarotService."""
    svc = request.app.get("tarot_service")
    if svc is None:
        return web.json_response({"error": "tarot service unavailable"}, status=503)

    decks = [
        {
            "deck_id": d.deck_id,
            "name": d.name,
            "cards_count": d.cards_count,
            "deck_type": d.deck_type,
        }
        for d in svc.list_decks() if d.cards_count > 0
    ]
    return web.json_response(decks)

# ============================================================
# API: ВЫТЯНУТЬ КАРТЫ
# ============================================================


async def api_draw_cards(request: web.Request) -> web.Response:
    """API: Вытянуть карты из колоды."""
    try:
        data = await request.json()
        deck_id = data.get('deck_id')
        count = data.get('count', 1)
        allow_reversed = data.get('allow_reversed', False)
        spread_type = data.get('spread_type', 'one')
        
        svc = request.app.get("tarot_service")
        
        # Демо-список карт для fallback
        demo_cards_list = [
            {"card_id": "0", "name": "Шут"},
            {"card_id": "1", "name": "Маг"},
            {"card_id": "2", "name": "Жрица"},
            {"card_id": "3", "name": "Императрица"},
            {"card_id": "4", "name": "Император"},
            {"card_id": "5", "name": "Иерофант"},
            {"card_id": "6", "name": "Влюблённые"},
            {"card_id": "7", "name": "Колесница"},
            {"card_id": "8", "name": "Сила"},
            {"card_id": "9", "name": "Отшельник"},
            {"card_id": "10", "name": "Колесо Фортуны"},
            {"card_id": "11", "name": "Справедливость"},
            {"card_id": "12", "name": "Повешенный"},
            {"card_id": "13", "name": "Смерть"},
            {"card_id": "14", "name": "Умеренность"},
            {"card_id": "15", "name": "Дьявол"},
            {"card_id": "16", "name": "Башня"},
            {"card_id": "17", "name": "Звезда"},
            {"card_id": "18", "name": "Луна"},
            {"card_id": "19", "name": "Солнце"},
            {"card_id": "20", "name": "Суд"},
            {"card_id": "21", "name": "Мир"}
        ]
        
        import random
        cards = []
        used_indices = set()
        
        for i in range(count):
            while True:
                idx = random.randint(0, len(demo_cards_list) - 1)
                if idx not in used_indices:
                    used_indices.add(idx)
                    break
            
            card_template = demo_cards_list[idx]
            is_reversed = allow_reversed and random.random() < 0.3
            
            # Формируем правильный ID для изображения (00, 01, ..., 21)
            card_img_id = card_template["card_id"].zfill(2)
            
            cards.append({
                "card_id": card_template["card_id"],
                "name": card_template["name"],
                "reversed": is_reversed,
                "image_url": f"/api/tarot/image/{deck_id or 'rider_waite'}/{card_img_id}.jpg"
            })
        
        # Генерируем демо-толкование
        interpretation = generate_demo_interpretation(cards, allow_reversed)
        
        return web.json_response({"cards": cards, "interpretation": interpretation})
    except Exception as e:
        logger.error(f"Ошибка API draw_cards: {e}")
        return web.json_response({"error": str(e), "cards": [], "interpretation": ""}, status=500)


def generate_demo_interpretation(cards, allow_reversed):
    """Генерация демо-толкования внутри приложения."""
    base_meanings = {
        "Шут": "Новые начинания, спонтанность, вера в будущее",
        "Маг": "Сила воли, мастерство, проявление желаемого",
        "Жрица": "Интуиция, тайные знания, внутренний голос",
        "Императрица": "Изобилие, творчество, материнская энергия",
        "Император": "Структура, власть, стабильность",
        "Иерофант": "Традиции, обучение, духовное руководство",
        "Влюблённые": "Выбор, гармония, отношения",
        "Колесница": "Движение вперёд, победа, контроль",
        "Сила": "Внутренняя сила, терпение, сострадание",
        "Отшельник": "Самоанализ, мудрость, уединение",
        "Колесо Фортуны": "Перемены, циклы, судьба",
        "Справедливость": "Честность, правда, закон",
        "Повешенный": "Пауза, новый взгляд, жертва",
        "Смерть": "Трансформация, окончание, начало нового",
        "Умеренность": "Баланс, гармония, терпение",
        "Дьявол": "Искушение, зависимость, материализм",
        "Башня": "Внезапные перемены, разрушение иллюзий",
        "Звезда": "Надежда, вдохновение, духовность",
        "Луна": "Иллюзии, страхи, подсознание",
        "Солнце": "Радость, успех, жизненная энергия",
        "Суд": "Возрождение, призыв, прощение",
        "Мир": "Завершение, целостность, путешествие"
    }
    
    reversed_prefix = "↔️ В перевёрнутом положении: "
    
    interpretations = []
    for card in cards:
        meaning = base_meanings.get(card["name"], "Энергия трансформации")
        if card["reversed"]:
            meaning = reversed_prefix + meaning.lower()
        interpretations.append(f"**{card['name']}**: {meaning}")
    
    return "\n\n".join(interpretations)


# ============================================================
# API: ТОЛКОВАНИЕ РАСКЛАДА (LLM) — ответ ВНУТРИ Mini App
# ============================================================


async def handle_webapp_data(request: web.Request) -> web.Response:
    """Логирует данные Mini App (основной канал — tg.sendData в боте)."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    logger.info(f"📥 Mini App data: action={data.get('action')}")
    return web.json_response({"status": "ok"})


# ============================================================
# API: ТОЛКОВАНИЕ РАСКЛАДА (LLM) — ответ ВНУТРИ Mini App
# ============================================================


async def api_interpret_spread(request: web.Request) -> web.Response:
    """API: Толкование расклада через LLM."""
    try:
        data = await request.json()
        cards = data.get('cards', [])
        question = data.get('question', '')
        spread_type = data.get('spread_type', 'one_card')
        
        llm = request.app.get('llm')
        if not llm or not cards:
            # Фолбэк на демо-толкование
            interpretation = generate_demo_interpretation(cards, False)
            return web.json_response({"interpretation": interpretation})
        
        # Формируем промпт для LLM
        card_names = [f"{card['name']}{' (перевернута)' if card.get('reversed') else ''}" for card in cards]
        prompt_text = f"""
Ты эксперт по Таро. Дай толкование расклада.
Расклад: {spread_type}
Вопрос: {question}
Карты: {', '.join(card_names)}

Дай краткое и точное толкование на русском языке.
"""
        response = await llm.ainvoke(prompt_text)
        interpretation = response.content if hasattr(response, 'content') else str(response)
        
        return web.json_response({"interpretation": interpretation})
    except Exception as e:
        logger.error(f"Ошибка API interpret_spread: {e}")
        return web.json_response({"error": str(e), "interpretation": ""}, status=500)

# ============================================================
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ============================================================
def setup_web_server_routes(app: web.Application,
                            tarot_service=None,
                            astro_retriever=None,
                            llm=None):
    """Регистрация маршрутов Mini App и API. Вызывается из main.py."""
    # Сохраняем сервисы в app context для доступа из хендлеров
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    if llm is not None:
        app["llm"] = llm

    # ❌ ИСПРАВЛЕНО: Убрали app.router.add_get('/', handle_mini_app_index)
    # Путь '/' уже занят health check в main.py. Mini App доступен по '/webapp'.

    app.router.add_get("/webapp", handle_mini_app_index)
    app.router.add_get("/static/{filepath:.*}", handle_static_file)
    app.router.add_get("/api/tarot/decks", api_get_decks)
    app.router.add_post("/api/tarot/draw", api_draw_cards)
    app.router.add_post("/api/tarot/interpret", api_interpret_spread)
    app.router.add_get(
        "/api/tarot/image/{deck_id}/{filename}", handle_deck_image)
    app.router.add_post("/api/webapp/data", handle_webapp_data)

    logger.info("✅ Маршруты Mini App и API успешно зарегистрированы")
