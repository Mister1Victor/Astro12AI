"""
services/web_server.py
Веб-сервер Mini App и API для Astro12AI.
ВАЖНО: Маршрут "/" (health check) регистрируется в main.py.
"""
import logging
from pathlib import Path
from aiohttp import web

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DECKS_DIR = BASE_DIR / "data" / "tarot" / "decks"


async def handle_mini_app_index(request: web.Request) -> web.Response:
    """Отдаёт static/index.html."""
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return web.Response(status=404, text="Mini App not found")
    return web.Response(text=index.read_text(encoding="utf-8"),
                        content_type="text/html")


async def handle_static_file(request: web.Request) -> web.Response:
    """Отдаёт файлы из static/."""
    rel = request.match_info.get("filepath", "")
    base = STATIC_DIR.resolve()
    path = (STATIC_DIR / rel).resolve()
    if not str(path).startswith(str(base)) or not path.is_file():
        return web.Response(status=404, text="File not found")
    content_types = {
        ".html": "text/html", ".css": "text/css",
        ".js": "application/javascript", ".json": "application/json",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    }
    ctype = content_types.get(path.suffix.lower(), "application/octet-stream")
    return web.Response(body=path.read_bytes(), content_type=ctype)


async def handle_deck_image(request: web.Request) -> web.Response:
    """Картинка карты из data/tarot/decks/<deck>/images/."""
    deck_id = request.match_info["deck_id"]
    filename = request.match_info["filename"]
    base = (DECKS_DIR / deck_id / "images").resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base)) or not path.is_file():
        # Фолбэк: корень папки колоды
        base2 = (DECKS_DIR / deck_id).resolve()
        path = (base2 / filename).resolve()
        if not str(path).startswith(str(base2)) or not path.is_file():
            return web.Response(status=404, text="Image not found")
    ctype = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return web.Response(body=path.read_bytes(), content_type=ctype)


async def api_get_decks(request: web.Request) -> web.Response:
    """Список колод из TarotService."""
    svc = request.app.get("tarot_service")
    if not svc:
        return web.json_response([
            {"deck_id": "rider_waite", "name": "Райдер-Уэйт", "cards_count": 78},
            {"deck_id": "thoth", "name": "Таро Тота", "cards_count": 78},
            {"deck_id": "author_deck_146",
                "name": "Оракул «12 Планет»", "cards_count": 146},
        ])
    decks = [
        {"deck_id": d.deck_id, "name": d.name,
         "cards_count": d.cards_count, "deck_type": d.deck_type}
        for d in svc.list_decks() if d.cards_count > 0
    ]
    return web.json_response(decks)


async def api_draw_cards(request: web.Request) -> web.Response:
    """Вытянуть карты из колоды."""
    svc = request.app.get("tarot_service")
    if not svc:
        return web.json_response({"error": "service unavailable"}, status=503)
    try:
        data = await request.json()
        deck_id = data.get("deck_id")
        count = int(data.get("count", 1))
        # JS шлёт 'reversed', принимаем оба варианта
        use_reversed = data.get("use_reversed", data.get("reversed", True))

        deck = svc.get_deck(deck_id)
        if not deck or not deck.cards:
            return web.json_response({"error": "deck not found"}, status=404)

        drawn = svc.draw_cards(count, deck.deck_id)
        cards = []
        for card, is_reversed in drawn:
            if not use_reversed:
                is_reversed = False
            cards.append({
                "card_id": card.card_id,
                "name": card.name,
                "reversed": is_reversed,
                "image_url": f"/api/tarot/image/{deck.deck_id}/{card.image}" if card.image else None,
                "astrology": card.astrology or "",
                "keywords": card.keywords or [],
            })
        return web.json_response({"cards": cards})
    except Exception as e:
        logger.error(f"Ошибка api_draw_cards: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_interpret_spread(request: web.Request) -> web.Response:
    """Толкование расклада через LLM."""
    svc = request.app.get("tarot_service")
    llm = request.app.get("llm")
    astro_retriever = request.app.get("astro_retriever")
    if not svc or not llm:
        return web.json_response({"error": "service unavailable"}, status=503)

    try:
        data = await request.json()
        cards_data = data.get("cards", [])
        question = data.get("question", "")
        spread_type = data.get("spread_type", "one")
        three_card_type = data.get("three_type") or data.get("three_card_type")
        deck_id = data.get("deck_id")

        deck = svc.get_deck(deck_id)
        if not deck:
            return web.json_response({"error": "deck not found"}, status=404)

        # Восстанавливаем карты
        drawn = []
        for cd in cards_data:
            card = deck.get_card(cd.get("card_id"))
            if card:
                drawn.append(
                    (card, cd.get("reversed", cd.get("is_reversed", False))))
        if not drawn:
            return web.json_response({"error": "no cards"}, status=400)

        # Позиции
        position_kinds = None
        if spread_type == "three" and three_card_type == "plus-minus-result":
            position_kinds = ["positive", "negative", "neutral"]

        # Импортируем функцию толкования
        from handlers.tarot import get_tarot_ai_interpretation

        interpretation = await get_tarot_ai_interpretation(
            question=question or "Интерпретируй расклад.",
            drawn=drawn,
            deck_name=deck.name,
            position_kinds=position_kinds,
            deck_id=deck_id,
            llm=llm,
            astro_retriever=astro_retriever,
        )
        if not interpretation:
            return web.json_response({"error": "ИИ недоступен"}, status=503)

        return web.json_response({"interpretation": interpretation})
    except Exception as e:
        logger.error(f"Ошибка api_interpret_spread: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_webapp_data(request: web.Request) -> web.Response:
    """Резервный приём данных Mini App."""
    try:
        data = await request.json()
        logger.info(f"📥 Mini App data: {data.get('action')}")
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def setup_web_server_routes(app: web.Application,
                            tarot_service=None,
                            astro_retriever=None,
                            llm=None):  # ← ДОБАВЛЕН llm
    """Регистрация маршрутов. '/' НЕ регистрируем — он в main.py."""
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    if llm is not None:
        app["llm"] = llm

    # ❌ НЕ добавляем '/' — он уже есть в main.py (handle_health_check)
    app.router.add_get("/webapp", handle_mini_app_index)
    app.router.add_get("/static/{filepath:.*}", handle_static_file)
    app.router.add_get(
        "/api/tarot/image/{deck_id}/{filename}", handle_deck_image)
    app.router.add_get("/api/tarot/decks", api_get_decks)
    app.router.add_post("/api/tarot/draw", api_draw_cards)
    app.router.add_post("/api/tarot/interpret",
                        api_interpret_spread)  # ← ДОБАВЛЕНО
    app.router.add_post("/api/webapp/data", handle_webapp_data)

    logger.info("✅ Маршруты Mini App зарегистрированы")
