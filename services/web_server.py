"""
Модуль веб-сервера для Mini App и API endpoints.
Обслуживает статические файлы (HTML, CSS, JS) и предоставляет API для бота.
"""
import json
import logging
import os
import time
from aiohttp import web
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Время старта приложения (для health check)
APP_STARTED_AT = time.time()


async def handle_health_check(request):
    """Health check для Render — проверяет, что сервис жив."""
    uptime_min = round((time.time() - APP_STARTED_AT) / 60, 1)
    html = f"""
    <html>
    <head><meta charset="utf-8"><title>12 Планет</title></head>
    <body style="font-family:sans-serif;text-align:center;padding-top:60px;">
    <h2>✅ Сервис работает</h2>
    <h3>Школа «12 Планет»</h3>
    <p>Аптайм: {uptime_min} мин.</p>
    <h3>Вернитесь в Telegram и /start.</h3>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def handle_mini_app_index(request: web.Request) -> web.Response:
    """Отдаёт главную страницу Mini App."""
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    index_path = os.path.join(static_dir, 'index.html')
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(status=404, text='Mini App not found: static/index.html')


async def handle_static_file(request: web.Request) -> web.Response:
    """Отдаёт статические файлы (CSS, JS, изображения)."""
    file_path = request.match_info.get('filepath', '')
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    full_path = os.path.normpath(os.path.join(static_dir, file_path))

    # Защита от выхода за пределы static/
    if not full_path.startswith(os.path.normpath(static_dir)):
        return web.Response(status=403, text='Forbidden')
    if not os.path.exists(full_path):
        return web.Response(status=404, text='File not found')

    content_type_map = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.html': 'text/html',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
    }
    ext = os.path.splitext(file_path)[1].lower()
    content_type = content_type_map.get(ext, 'application/octet-stream')

    with open(full_path, 'rb') as f:
        content = f.read()
    return web.Response(body=content, content_type=content_type)


async def api_get_decks(request: web.Request) -> web.Response:
    """API: Получить список колод."""
    tarot_service = request.app.get('tarot_service')
    if not tarot_service:
        decks = [
            {"deck_id": "rider_waite", "name": "Райдер-Уэйт", "cards_count": 78},
            {"deck_id": "thoth", "name": "Таро Тота", "cards_count": 78},
            {"deck_id": "author_deck_146",
                "name": "Авторская колода 12 Планет", "cards_count": 146}
        ]
        return web.json_response(decks)

    decks = tarot_service.list_decks()
    result = []
    for deck in decks:
        if deck.cards_count > 0:
            result.append({
                "deck_id": deck.deck_id,
                "name": deck.name,
                "cards_count": deck.cards_count,
                "deck_type": deck.deck_type
            })
    return web.json_response(result)


async def api_draw_cards(request: web.Request) -> web.Response:
    """API: Вытянуть карты из колоды."""
    try:
        data = await request.json()
        deck_id = data.get('deck_id')
        count = data.get('count', 1)
        use_reversed = data.get('use_reversed', True)

        tarot_service = request.app.get('tarot_service')
        if not tarot_service:
            cards = []
            for i in range(count):
                cards.append({
                    "card_id": f"card_{i}",
                    "name": f"Карта {i+1}",
                    "reversed": False,
                    "image_url": f"/static/cards/card_{i}.jpg"
                })
            return web.json_response({"cards": cards})

        drawn = tarot_service.draw_cards(
            count, deck_id, use_reversed=use_reversed)
        cards = []
        for card, is_reversed in drawn:
            cards.append({
                "card_id": card.card_id,
                "name": card.name,
                "reversed": is_reversed,
                "image_url": f"/api/tarot/image/{deck_id}/{card.image}" if card.image else None,
                "astrology": card.astrology or "",
                "keywords": card.keywords or []
            })
        return web.json_response({"cards": cards})
    except Exception as e:
        logger.error(f"Ошибка API draw_cards: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_interpret_spread(request: web.Request) -> web.Response:
    """API: Получить толкование расклада от LLM."""
    try:
        data = await request.json()
        deck_id = data.get('deck_id')
        spread_type = data.get('spread_type')
        question = data.get('question', '')
        cards_data = data.get('cards', [])

        llm = request.app.get('llm')
        tarot_service = request.app.get('tarot_service')
        astro_retriever = request.app.get('astro_retriever')

        if not llm or not tarot_service:
            return web.json_response(
                {"error": "LLM or TarotService not available"}, status=503
            )

        from core.tarot.models import TarotCard
        drawn = []
        for card_data in cards_data:
            card = TarotCard(
                card_id=card_data['card_id'],
                name=card_data['name'],
                reversed=card_data.get('reversed', False),
                astrology=card_data.get('astrology', ''),
                keywords=card_data.get('keywords', [])
            )
            drawn.append((card, card_data.get('reversed', False)))

        deck = tarot_service.get_deck(deck_id)
        deck_name = deck.name if deck else deck_id

        position_kinds = None
        if spread_type == 'three':
            position_kinds = ['neutral', 'neutral', 'neutral']
        elif spread_type == 'plusminus':
            position_kinds = ['positive', 'negative', 'neutral']

        from handlers.tarot import get_tarot_ai_interpretation
        interpretation = await get_tarot_ai_interpretation(
            question=question,
            drawn=drawn,
            deck_name=deck_name,
            position_kinds=position_kinds,
            deck_id=deck_id,
            llm=llm,
            astro_retriever=astro_retriever
        )
        if not interpretation:
            return web.json_response(
                {"error": "Не удалось получить толкование"}, status=500
            )
        return web.json_response({"interpretation": interpretation, "success": True})
    except Exception as e:
        logger.error(f"Ошибка API interpret_spread: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_webapp_data(request: web.Request) -> web.Response:
    """Обработка данных от Mini App (альтернатива tg.sendData)."""
    try:
        data = await request.json()
        action = data.get('action')
        if action == 'tarot_spread':
            logger.info(f"Получены данные расклада: {data}")
            return web.json_response({"status": "ok"})
        elif action == 'astrology_aspect':
            logger.info(f"Получены данные аспекта: {data}")
            return web.json_response({"status": "ok"})
        elif action == 'main_menu':
            logger.info(f"Запрос основного меню: {data}")
            return web.json_response({"status": "ok"})
        return web.json_response({"status": "unknown_action"}, status=400)
    except Exception as e:
        logger.error(f"Ошибка обработки webapp данных: {e}")
        return web.json_response({"error": str(e)}, status=500)


def setup_web_server_routes(
    app: web.Application,
    tarot_service=None,
    astro_retriever=None,
    llm=None  # ← ДОБАВЛЕНО: теперь принимает llm
):
    """Регистрация маршрутов веб-сервера."""
    # Сохраняем сервисы в app для доступа из хендлеров
    if tarot_service is not None:
        app["tarot_service"] = tarot_service
    if astro_retriever is not None:
        app["astro_retriever"] = astro_retriever
    if llm is not None:  # ← ДОБАВЛЕНО
        app["llm"] = llm

    # 1. Health check для Render
    app.router.add_get('/health', handle_health_check)

    # 2. Mini App и статика
    app.router.add_get('/', handle_mini_app_index)
    app.router.add_get('/webapp', handle_mini_app_index)
    app.router.add_get('/static/{filepath:.*}', handle_static_file)

    # 3. API endpoints
    app.router.add_get('/api/tarot/decks', api_get_decks)
    app.router.add_post('/api/tarot/draw', api_draw_cards)
    app.router.add_post('/api/tarot/interpret',
                        api_interpret_spread)  # ← ДОБАВЛЕНО
    app.router.add_post('/api/webapp/data', handle_webapp_data)

    logger.info("✅ Маршруты веб-сервера зарегистрированы (включая LLM)")
