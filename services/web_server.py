"""
services/web_server.py
Веб-сервер Mini App и API для Astro12AI.
Маршруты:
GET  /webapp                              — главная страница Mini App (static/index.html)
GET  /favicon.ico                         — пустой ответ (не 404)
GET  /static/{filepath}                   — статика (css/js/изображения Mini App)
GET  /api/tarot/decks                     — список колод из TarotService
POST /api/tarot/draw                      — вытянуть карты (TarotService)
POST /api/tarot/interpret                 — толкование расклада через LLM
GET  /api/tarot/image/{deck_id}/{file}    — картинки карт
POST /api/webapp/data                     — резервный приём данных Mini App
ВАЖНО: Маршрут "/" (health check) регистрируется в main.py — здесь НЕ трогаем.
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
# FAVICON (убираем 404)
# ============================================================
async def handle_favicon(request: web.Request) -> web.Response:
    """Пустой ответ 204 — браузер не показывает ошибку."""
    return web.Response(status=204)


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
    """Реальное вытягивание карт через TarotService.draw_cards."""
    svc = request.app.get("tarot_service")
    if svc is None:
        return web.json_response({"error": "tarot service unavailable"}, status=503)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    deck_id = data.get("deck_id")
    try:
        count = int(data.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 10))
    allow_reversed = bool(data.get("use_reversed", True))

    deck = svc.get_deck(deck_id)
    if not deck or not deck.cards:
        return web.json_response({"error": "deck not found"}, status=404)

    drawn = svc.draw_cards(count, deck.deck_id)
    cards = []
    for card, rev in drawn:
        # Если пользователь отключил перевёрнутые — сбрасываем rev
        final_rev = rev if allow_reversed else False
        cards.append({
            "card_id": card.card_id,
            "name": card.name,
            "reversed": final_rev,
            "astrology": card.astrology or "",
            "keywords": card.keywords or [],
            "meaning": card.get_meaning(final_rev),
            "image_url": (f"/api/tarot/image/{deck.deck_id}/{card.image}"
                          if card.image else None),
        })
    return web.json_response({
        "deck_id": deck.deck_id,
        "deck_name": deck.name,
        "cards": cards,
    })


# ============================================================
# API: ТОЛКОВАНИЕ РАСКЛАДА (LLM) — ответ ВНУТРИ Mini App
# ============================================================
async def api_interpret_spread(request: web.Request) -> web.Response:
    """Толкование расклада через LLM (вызывается из Mini App)."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    llm = request.app.get("llm")
    svc = request.app.get("tarot_service")
    astro_retriever = request.app.get("astro_retriever")

    if not llm or not svc:
        return web.json_response({"error": "LLM or TarotService unavailable"}, status=503)

    cards_data = data.get("cards", [])
    question = data.get("question", "") or "Общая интерпретация расклада"
    deck_id = data.get("deck_id")
    spread_type = data.get("spread_type", "one")

    deck = svc.get_deck(deck_id)
    deck_name = deck.name if deck else "Неизвестная колода"

    # Восстанавливаем объекты карт
    drawn = []
    for c in cards_data:
        card = deck.get_card(c.get("card_id")) if deck else None
        if card:
            drawn.append((card, bool(c.get("reversed", False))))

    if not drawn:
        return web.json_response({"error": "No valid cards"}, status=400)

    # Определяем position_kinds по типу расклада
    position_kinds = None
    if spread_type == "plusminus":
        position_kinds = ["positive", "negative", "neutral"]
    elif spread_type == "choice" and len(drawn) == 7:
        position_kinds = ["positive", "negative", "neutral",
                          "positive", "negative", "neutral", "day"]
    elif spread_type == "cod":
        position_kinds = ["day"]

    # Импортируем функцию интерпретации (из handlers/tarot.py или main.py)
    try:
        from handlers.tarot import get_tarot_ai_interpretation
        interpretation = await get_tarot_ai_interpretation(
            question=question,
            drawn=drawn,
            deck_name=deck_name,
            position_kinds=position_kinds,
            deck_id=deck_id,
            llm=llm,
            astro_retriever=astro_retriever,
        )
    except ImportError:
        # Fallback: функция в main.py (без llm/astro_retriever параметров)
        from main import get_tarot_ai_interpretation
        interpretation = await get_tarot_ai_interpretation(
            question, drawn, deck_name, position_kinds, deck_id
        )

    if not interpretation:
        return web.json_response({
            "interpretation": "⚠️ Сервис ИИ временно недоступен. Попробуйте через 1–2 минуты."
        })

    return web.json_response({"interpretation": interpretation})


# ============================================================
# РЕЗЕРВНЫЙ ПРИЁМ ДАННЫХ (вне Telegram)
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
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ============================================================
def setup_web_server_routes(app: web.Application,
                            tarot_service=None,
                            astro_retriever=None,
                            llm=None):
    """Регистрация маршрутов Mini App и API. Вызывается из main.py."""
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    if llm is not None:
        app["llm"] = llm

    # ❌ НЕ регистрируем '/' — он уже занят health check в main.py
    app.router.add_get("/webapp", handle_mini_app_index)
    app.router.add_get("/favicon.ico", handle_favicon)
    app.router.add_get("/static/{filepath:.*}", handle_static_file)
    app.router.add_get("/api/tarot/decks", api_get_decks)
    app.router.add_post("/api/tarot/draw", api_draw_cards)
    app.router.add_post("/api/tarot/interpret", api_interpret_spread)
    app.router.add_get(
        "/api/tarot/image/{deck_id}/{filename}", handle_deck_image)
    app.router.add_post("/api/webapp/data", handle_webapp_data)

    logger.info("✅ Маршруты Mini App и API зарегистрированы")
