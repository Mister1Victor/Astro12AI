"""
services/web_server.py
Веб-сервер Mini App и API для Astro12AI.

Маршруты:
  GET  /                                    — health check (если main.py его не зарегистрировал)
  GET  /health                              — health check
  GET  /webapp                              — главная страница Mini App (static/index.html)
  GET  /static/{filepath}                   — статика Mini App (css/js)
  GET  /api/tarot/image/{deck_id}/{file}    — КАРТИНКИ КАРТ из data/tarot/decks/<колода>/images/
  GET  /api/tarot/decks                     — список колод (реальный TarotService)
  POST /api/tarot/draw                      — вытянуть карты (реальный TarotService)
  POST /api/tarot/interpret                 — РЕАЛЬНОЕ толкование LLM (как в боте)
  POST /api/webapp/data                     — резервный приём данных Mini App
"""
import logging
import time
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DECKS_DIR = BASE_DIR / "data" / "tarot" / "decks"
APP_STARTED_AT = time.time()

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
# HEALTH / INDEX / STATICA
# ============================================================
async def handle_health(request: web.Request) -> web.Response:
    uptime_min = round((time.time() - APP_STARTED_AT) / 60, 1)
    html = (
        "<html><head><meta charset='utf-8'><title>12 Планет</title></head>"
        "<body style='font-family:sans-serif;text-align:center;padding-top:60px;'>"
        "<h2>✅ Сервис работает</h2><h3>Школа «12 Планет»</h3>"
        f"<p>Аптайм: {uptime_min} мин.</p></body></html>"
    )
    return web.Response(text=html, content_type="text/html")


async def handle_mini_app_index(request: web.Request) -> web.Response:
    """Отдаёт static/index.html."""
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return web.Response(status=404, text="Mini App not found: static/index.html")
    return web.Response(text=index.read_text(encoding="utf-8"),
                        content_type="text/html")


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
# КАРТИНКИ КАРТ (все колоды: rider_waite, thoth, author_deck, author_deck_146)
# ============================================================
async def handle_deck_image(request: web.Request) -> web.Response:
    """Картинка карты: data/tarot/decks/<deck_id>/images/<file>, фолбэк — корень колоды."""
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
# СЛУЖЕБНОЕ: доступ к сервисам (надёжно при любой версии main.py)
# ============================================================
def _get_services(request: web.Request):
    app = request.app
    tarot_service = app.get("tarot_service")
    llm = app.get("llm")
    astro_retriever = app.get("astro_retriever")
    if tarot_service is None or llm is None or astro_retriever is None:
        try:  # main.py уже загружен к моменту запроса — берём его экземпляры
            import main as _main
            tarot_service = tarot_service or getattr(_main, "tarot", None)
            llm = llm or getattr(_main, "llm", None)
            astro_retriever = astro_retriever or getattr(
                _main, "astro_retriever", None)
        except Exception:
            pass
    if llm is None:
        try:
            from core.llm.model import create_llm
            llm = create_llm()
        except Exception:
            llm = None
    return tarot_service, llm, astro_retriever


# ============================================================
# API: КОЛОДЫ
# ============================================================
async def api_get_decks(request: web.Request) -> web.Response:
    tarot_service, _, _ = _get_services(request)
    if not tarot_service:
        return web.json_response({"error": "tarot service unavailable"}, status=503)
    result = []
    for deck in tarot_service.list_decks():
        if deck.cards_count > 0:
            result.append({
                "deck_id": deck.deck_id,
                "name": deck.name,
                "cards_count": deck.cards_count,
                "deck_type": deck.deck_type,
            })
    return web.json_response(result)


# ============================================================
# API: ВЫТЯНУТЬ КАРТЫ (реальное, с image_url на /api/tarot/image/...)
# ============================================================
async def api_draw_cards(request: web.Request) -> web.Response:
    tarot_service, _, _ = _get_services(request)
    if not tarot_service:
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
    use_reversed = bool(data.get("use_reversed", True))

    deck = tarot_service.get_deck(deck_id)
    if not deck or not deck.cards:
        return web.json_response({"error": "deck not found"}, status=404)

    drawn = tarot_service.draw_cards(count, deck.deck_id)
    cards = []
    for card, rev in drawn:
        if not use_reversed:
            rev = False
        cards.append({
            "card_id": card.card_id,
            "name": card.name,
            "reversed": rev,
            "astrology": card.astrology or "",
            "keywords": card.keywords or [],
            "image_url": (f"/api/tarot/image/{deck.deck_id}/{card.image}"
                          if card.image else None),
        })
    return web.json_response({
        "cards": cards,
        "deck_id": deck.deck_id,
        "deck_name": deck.name,
    })


# ============================================================
# API: РЕАЛЬНОЕ ТОЛКОВАНИЕ LLM
# ============================================================
async def api_interpret_spread(request: web.Request) -> web.Response:
    """Толкование расклада тем же LLM-пайплайном, что и в боте
    (handlers.tarot.get_tarot_ai_interpretation: TAROT_SYSTEM_PROMPT +
    материалы Школы для авторских колод)."""
    tarot_service, llm, astro_retriever = _get_services(request)
    if not tarot_service or not llm:
        return web.json_response({"error": "service unavailable"}, status=503)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    deck_id = data.get("deck_id")
    spread_type = data.get("spread_type", "one")
    three_card_type = data.get("three_card_type")
    question = (data.get("question") or "").strip()
    cards_data = data.get("cards", [])

    deck = tarot_service.get_deck(deck_id)
    if not deck:
        return web.json_response({"error": "deck not found"}, status=404)

    # Восстанавливаем РЕАЛЬНЫЕ объекты карт (со значениями) — как в боте
    drawn = []
    for cd in cards_data:
        card = deck.get_card(cd.get("card_id"))
        if card:
            drawn.append((card, bool(cd.get("reversed", False))))
    if not drawn:
        return web.json_response({"error": "no cards restored"}, status=400)

    # Виды позиций — те же, что в боте
    if spread_type == "three" and three_card_type == "plus-minus-result":
        position_kinds = ["positive", "negative", "neutral"]
    elif spread_type == "choice":
        position_kinds = ["positive", "negative", "neutral",
                          "positive", "negative", "neutral", "day"]
    elif spread_type == "one":
        position_kinds = ["day"]
    else:
        position_kinds = None

    if not question:
        question = ("Интерпретируй расклад в контексте вопроса пользователя.")

    from handlers.tarot import get_tarot_ai_interpretation
    interpretation = await get_tarot_ai_interpretation(
        question=question,
        drawn=drawn,
        deck_name=deck.name,
        position_kinds=position_kinds,
        deck_id=deck.deck_id,
        llm=llm,
        astro_retriever=astro_retriever,
    )
    if not interpretation:
        return web.json_response(
            {"error": "ИИ временно недоступен. Попробуйте через 1–2 минуты."},
            status=503)
    return web.json_response({"interpretation": interpretation, "success": True})

# ============================================================
# API: АСТРОЛОГИЯ (интерпретация в Mini App)
# ============================================================


async def api_interpret_astro(request: web.Request) -> web.Response:
    """Интерпретация астрологического запроса через умный поисковик."""
    tarot_service, llm, astro_retriever = _get_services(request)
    if not astro_retriever or not llm:
        return web.json_response({"error": "service unavailable"}, status=503)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    raw_text = data.get("query", "").strip()
    if not raw_text:
        return web.json_response({"error": "empty query"}, status=400)

    try:
        # Импортируем функции парсинга из main.py
        from main import parse_astrological_input, get_ai_interpretation

        processed_query = parse_astrological_input(raw_text)
        task_hint = astro_retriever.build_task_hint(processed_query)
        final_task = f"Показатель: {processed_query}\nЗадача: {task_hint}."

        interpretation = await get_ai_interpretation(final_task)

        if not interpretation:
            return web.json_response({"error": "ИИ не дал ответа"}, status=503)
        return web.json_response({"interpretation": interpretation, "success": True})
    except Exception as e:
        logger.error(f"Ошибка api_interpret_astro: {e}")
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# РЕЗЕРВНЫЙ ПРИЁМ ДАННЫХ MINI APP
# ============================================================


async def handle_webapp_data(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)
    action = data.get("action")
    if action in ("tarot_spread", "astrology_aspect", "main_menu"):
        logger.info(f"📥 Mini App data: action={action}")
        return web.json_response({"status": "ok"})
    return web.json_response({"status": "unknown_action"}, status=400)


# ============================================================
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ============================================================
def _root_registered(app: web.Application) -> bool:
    for res in app.router.resources():
        info = res.get_info()
        if isinstance(info, dict) and info.get("path") == "/":
            return True
    return False


def setup_web_server_routes(app: web.Application, tarot_service=None,
                            astro_retriever=None, llm=None):
    """Регистрация маршрутов Mini App и API. Вызывается из main.py."""
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    if llm is not None:
        app["llm"] = llm

    # '/' регистрируем только если main.py его не занял (health check)
    if not _root_registered(app):
        app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/webapp", handle_mini_app_index)
    app.router.add_get("/static/{filepath:.*}", handle_static_file)
    app.router.add_get(
        "/api/tarot/image/{deck_id}/{filename}", handle_deck_image)
    app.router.add_get("/api/tarot/decks", api_get_decks)
    app.router.add_post("/api/tarot/draw", api_draw_cards)
    app.router.add_post("/api/tarot/interpret", api_interpret_spread)
    app.router.add_post("/api/webapp/data", handle_webapp_data)
    app.router.add_post("/api/tarot/interpret", api_interpret_spread)
    app.router.add_post("/api/astro/interpret", api_interpret_astro)
    app.router.add_post("/api/webapp/data", handle_webapp_data)
    logger.info("✅ Маршруты Mini App и API зарегистрированы "
                "(картинки /api/tarot/image/..., толкование /api/tarot/interpret)")
