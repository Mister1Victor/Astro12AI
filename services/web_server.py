"""
Модуль веб-сервера для Mini App и API endpoints.
Отдаёт статические файлы (HTML, CSS, JS), картинки колод и API для бота.

ВАЖНО: маршрут "/" НЕ регистрируется — он принадлежит main.py (health check).
"""
import logging
from pathlib import Path
from aiohttp import web

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = _PROJECT_ROOT / "static"


# ============================================================
# MINI APP: главная страница
# ============================================================
async def handle_mini_app_index(request: web.Request) -> web.Response:
    """Отдаёт главную страницу Mini App (static/index.html)."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return web.Response(text=index.read_text(encoding="utf-8"),
                            content_type="text/html")
    return web.Response(
        text="<html><body><h2>Mini App: не найден static/index.html</h2></body></html>",
        content_type="text/html", status=404)


# ============================================================
# СТАТИКА: CSS / JS / картинки Mini App
# ============================================================
async def handle_static_file(request: web.Request) -> web.Response:
    """Отдаёт статические файлы (CSS, JS, HTML, JSON)."""
    rel = request.match_info.get("filepath", "")
    path = (STATIC_DIR / rel).resolve()
    if not str(path).startswith(str(STATIC_DIR)) or not path.is_file():
        return web.Response(status=404, text="File not found")
    ctype = {
        ".css": "text/css",
        ".js": "application/javascript",
        ".html": "text/html",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }.get(path.suffix.lower(), "text/plain")
    return web.Response(body=path.read_bytes(), content_type=ctype)


# ============================================================
# КАРТИНКИ КОЛОД для Mini App
# ============================================================
async def handle_deck_image(request: web.Request) -> web.Response:
    """Отдаёт картинку карты: /api/tarot/image/{deck_id}/{filename}."""
    deck_id = request.match_info["deck_id"]
    filename = request.match_info["filename"]
    base = (_PROJECT_ROOT / "data" / "tarot" /
            "decks" / deck_id / "images").resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base)) or not path.is_file():
        return web.Response(status=404, text="Image not found")
    ctype = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return web.Response(body=path.read_bytes(), content_type=ctype)


# ============================================================
# API: колоды и вытягивание карт (реальный TarotService)
# ============================================================
async def api_get_decks(request: web.Request) -> web.Response:
    """API: список колод из реального TarotService."""
    svc = request.app.get("tarot_service")
    if svc is not None:
        decks = [
            {"deck_id": d.deck_id, "name": d.name, "cards_count": d.cards_count}
            for d in svc.list_decks() if d.cards_count > 0
        ]
    else:
        decks = [
            {"deck_id": "rider_waite", "name": "Таро Райдера-Уэйта", "cards_count": 78},
            {"deck_id": "thoth", "name": "Таро Тота", "cards_count": 78},
            {"deck_id": "author_deck_146",
                "name": "Оракул «12 Планет»", "cards_count": 146},
        ]
    return web.json_response(decks)


async def api_draw_cards(request: web.Request) -> web.Response:
    """API: вытянуть карты из колоды через реальный TarotService."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)
    deck_id = data.get("deck_id")
    count = int(data.get("count", 1))
    spread_type = data.get("spread_type", "one")
    svc = request.app.get("tarot_service")
    if svc is None:
        return web.json_response({"error": "tarot service unavailable"}, status=503)
    drawn = svc.draw_cards(count, deck_id)
    cards = []
    for card, rev in drawn:
        cards.append({
            "card_id": card.card_id,
            "name": card.name,
            "reversed": rev,
            "astrology": card.astrology or "",
            "meaning": card.get_meaning(rev),
            "image_url": (f"/api/tarot/image/{deck_id}/{card.image}"
                          if card.image else None),
        })
    return web.json_response({"cards": cards, "spread_type": spread_type})


# ============================================================
# Приём данных из Mini App (дубль tg.sendData)
# ============================================================
async def handle_webapp_data(request: web.Request) -> web.Response:
    """Логирует данные Mini App (основной канал — tg.sendData в боте)."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)
    action = data.get("action")
    logger.info(f"📥 Mini App data: action={action}")
    if action in ("tarot_spread", "astrology_aspect"):
        return web.json_response({"status": "ok"})
    return web.json_response({"status": "unknown_action"}, status=400)


# ============================================================
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ============================================================
def setup_web_server_routes(app: web.Application, tarot_service=None,
                            astro_retriever=None):
    """Регистрация маршрутов Mini App и API. Маршрут '/' НЕ трогаем (он в main.py)."""
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    app.router.add_get("/webapp", handle_mini_app_index)
    app.router.add_get("/static/{filepath:.*}", handle_static_file)
    app.router.add_get("/api/tarot/decks", api_get_decks)
    app.router.add_post("/api/tarot/draw", api_draw_cards)
    app.router.add_get(
        "/api/tarot/image/{deck_id}/{filename}", handle_deck_image)
    app.router.add_post("/api/webapp/data", handle_webapp_data)
    logger.info("✅ Маршруты веб-сервера зарегистрированы (Mini App + API)")
