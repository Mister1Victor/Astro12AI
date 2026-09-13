"""
services/web_server.py
Веб-сервер Mini App и API для Astro12AI.

Маршруты:
  GET  /webapp                              — главная страница Mini App (static/index.html)
  GET  /static/{filepath}                   — статика (css/js/изображения Mini App)
  GET  /api/tarot/decks                     — список колод из реального TarotService
  POST /api/tarot/draw                      — вытянуть карты (реальный TarotService)
  GET  /api/tarot/image/{deck_id}/{file}    — картинки карт из data/tarot/decks/
  POST /api/tarot/interpret                 — толкование расклада через LLM
  POST /api/webapp/data                     — резервный приём данных Mini App

ВАЖНО: Маршрут "/" (health check) регистрируется в main.py — здесь НЕ трогаем.
"""
import logging
import os
from pathlib import Path
from aiohttp import web

# ✅ ИСПРАВЛЕНО: было `name` вместо `__name__`
logger = logging.getLogger(__name__)

# ✅ ИСПРАВЛЕНО: было `file` вместо `__file__`
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DECKS_DIR = BASE_DIR / "data" / "tarot" / "decks"

CONTENT_TYPES = {
    ".html": "text/html",           # ✅ ИСПРАВЛЕНО: убраны пробелы в ключах
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

    if not str(path).startswith(str(base)) or not path.is_file():  # ✅ ИСПРАВЛЕНО: убран пробел
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
    use_reversed = data.get("use_reversed", True)

    deck = svc.get_deck(deck_id)
    if not deck or not deck.cards:
        return web.json_response({"error": "deck not found"}, status=404)

    drawn = svc.draw_cards(count, deck.deck_id)
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
            "meaning": card.get_meaning(rev),
            "image_url": (f"/api/tarot/image/{deck.deck_id}/{card.image}"
                          if card.image else None),
        })

    return web.json_response({
        "deck_id": deck.deck_id,
        "deck_name": deck.name,
        "cards": cards,
    })


# ============================================================
# API: ТОЛКОВАНИЕ РАСКЛАДА (через LLM)
# ============================================================
async def api_interpret_spread(request: web.Request) -> web.Response:
    """Толкование расклада через LLM."""
    llm = request.app.get("llm")
    astro_retriever = request.app.get("astro_retriever")
    tarot_service = request.app.get("tarot_service")

    if not llm or not tarot_service:
        return web.json_response({"error": "LLM or TarotService not available"}, status=503)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    question = data.get("question", "")
    cards = data.get("cards", [])
    spread_type = data.get("spread_type", "one")
    deck_id = data.get("deck_id")

    if not cards:
        return web.json_response({"error": "no cards provided"}, status=400)

    # Восстанавливаем карты из TarotService по card_id
    deck = tarot_service.get_deck(deck_id)
    drawn = []
    for c in cards:
        card_id = c.get("card_id")
        reversed_flag = c.get("reversed", False)
        if deck:
            card = deck.get_card(card_id)
            if card:
                drawn.append((card, reversed_flag))

    if not drawn:
        return web.json_response({"error": "cards not found in deck"}, status=404)

    try:
        from core.prompts.tarot_prompt import TAROT_SYSTEM_PROMPT
        from core.tarot import render as tarot_render

        cards_desc = []
        for i, (card, rev) in enumerate(drawn):
            orient = "перевёрнутое" if rev else "прямое"
            astro = f" [{card.astrology}]" if card.astrology else ""
            meaning = tarot_render.card_context_for_position(
                card, rev, "neutral")
            cards_desc.append(
                f"Позиция {i + 1}: {card.name} ({orient}{astro}) —\n{meaning}")

        cards_text = "\n".join(cards_desc)

        # Материалы Школы для авторских колод
        school_block = ""
        if deck_id in ("author_deck_146", "author_deck") and astro_retriever:
            entities_src = " ".join(
                f"{card.name} {card.astrology or ''}" for card, _ in drawn
            )
            school_block = astro_retriever.build_authority_context(
                entities_src)

        human_prompt = (
            f"Вопрос клиента: {question}\n"
            + (school_block + "\n" if school_block else "")
            + f"Вытянутые карты (колода «{deck.name}»):\n{cards_text}\n"
            f"Дай связную, глубокую интерпретацию этого расклада в контексте вопроса."
        )

        resp = await llm.ainvoke([
            ("system", TAROT_SYSTEM_PROMPT),
            ("human", human_prompt)
        ])

        text = getattr(resp, "content", "") or str(resp)
        if isinstance(text, dict):
            text = text.get("text") or str(text)

        return web.json_response({"interpretation": text, "success": True})

    except Exception as e:
        logger.error(f"Ошибка api_interpret_spread: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============================================================
# РЕЗЕРВНЫЙ ПРИЁМ ДАННЫХ (вне Telegram)
# ============================================================
async def handle_webapp_data(request: web.Request) -> web.Response:
    """Логирует данные Mini App (основной канал — tg.sendData в боте)."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    action = data.get("action", "unknown")
    logger.info(f"📥 Mini App data: action={action}")

    if action == "main_menu":
        return web.json_response({"status": "ok"})

    return web.json_response({"status": "ok"})


# ============================================================
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ============================================================
def setup_web_server_routes(app: web.Application, tarot_service=None, astro_retriever=None, llm=None):
    """Регистрация маршрутов веб-сервера."""
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    if llm is not None:
        app["llm"] = llm

    # Mini App и статика
    app.router.add_get('/', handle_mini_app_index)
    app.router.add_get('/webapp', handle_mini_app_index)
    app.router.add_get('/static/{filepath:.*}', handle_static_file)
    # Картинки карт
    app.router.add_get(
        '/api/tarot/image/{deck_id}/{filename}', handle_deck_image)
    # API endpoints
    app.router.add_get('/api/tarot/decks', api_get_decks)
    app.router.add_post('/api/tarot/draw', api_draw_cards)
    # ✅ ДОБАВЛЕН роут интерпретации (был пропущен!)
    app.router.add_post('/api/tarot/interpret', api_interpret_spread)
    app.router.add_post('/api/webapp/data', handle_webapp_data)
    logger.info(
        "✅ Маршруты веб-сервера зарегистрированы (включая /api/tarot/interpret)")
