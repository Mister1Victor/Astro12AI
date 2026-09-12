"""
Модуль веб-сервера для Mini App и API endpoints.
Обслуживает статические файлы (HTML, CSS, JS) и предоставляет API для бота.
"""
import json
import logging
from aiohttp import web
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def handle_mini_app_index(request: web.Request) -> web.Response:
    """Отдаёт главную страницу Mini App."""
    content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Astro12AI - Таро Расклад</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="stylesheet" href="/static/css/mini-app.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🔮 Таро Школы 12 Планет</h1>
            <p class="subtitle">Выберите расклад и вытяните карты</p>
        </header>
        <!-- Выбор расклада -->
        <section id="spread-selection" class="section">
            <h2>Выберите тип расклада</h2>
            <div class="button-grid">
                <button class="btn-primary" data-spread="one">🃏 Одна карта</button>
                <button class="btn-primary" data-spread="three">🔮 Три карты</button>
                <button class="btn-primary" data-spread="choice">⚖️ Выбор пути</button>
                <button class="btn-primary" data-spread="celtic">✝️ Кельтский крест</button>
            </div>
        </section>
        <!-- Выбор колоды -->
        <section id="deck-selection" class="section hidden">
            <h2>Выберите колоду</h2>
            <div id="decks-list" class="deck-list"></div>
            <button class="btn-secondary" id="back-to-spread">← Назад к раскладам</button>
        </section>
        <!-- Экран перемешивания -->
        <section id="shuffle-screen" class="section hidden">
            <h2 id="shuffle-title">Перемешайте колоду</h2>
            <div class="card-deck-visual">
                <div class="card-back" id="deck-visual"></div>
            </div>
            <button class="btn-primary btn-large" id="shuffle-btn">🔀 Перемешать</button>
            <button class="btn-primary btn-large hidden" id="draw-cards-btn">✨ Вытянуть карты</button>
        </section>
        <!-- Результат -->
        <section id="result-screen" class="section hidden">
            <h2>Ваши карты</h2>
            <div id="cards-result" class="cards-result"></div>
            <div class="result-actions">
                <button class="btn-success" id="send-to-bot">✅ Отправить в бот</button>
                <button class="btn-secondary" id="retry-spread">🔄 Повторить расклад</button>
            </div>
        </section>
        <!-- Астрология -->
        <section id="astrology-input" class="section hidden">
            <h2>🪐 Параметры аспекта</h2>
            <form id="astrology-form">
                <div class="form-group">
                    <label for="planet1">Первая планета:</label>
                    <select id="planet1" required>
                        <option value="">Выберите планету</option>
                        <option value="Sun">Солнце</option>
                        <option value="Moon">Луна</option>
                        <option value="Mercury">Меркурий</option>
                        <option value="Venus">Венера</option>
                        <option value="Mars">Марс</option>
                        <option value="Jupiter">Юпитер</option>
                        <option value="Saturn">Сатурн</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="sign1">Знак первой планеты:</label>
                    <select id="sign1" required>
                        <option value="">Выберите знак</option>
                        <option value="Ari">Овен</option>
                        <option value="Tau">Телец</option>
                        <option value="Gem">Близнецы</option>
                        <option value="Can">Рак</option>
                        <option value="Leo">Лев</option>
                        <option value="Vir">Дева</option>
                        <option value="Lib">Весы</option>
                        <option value="Sco">Скорпион</option>
                        <option value="Sgr">Стрелец</option>
                        <option value="Cap">Козерог</option>
                        <option value="Aqr">Водолей</option>
                        <option value="Psc">Рыбы</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="aspect-type">Тип аспекта:</label>
                    <select id="aspect-type" required>
                        <option value="">Выберите аспект</option>
                        <option value="conjunction">Соединение (0°)</option>
                        <option value="sextile">Секстиль (60°)</option>
                        <option value="square">Квадрат (90°)</option>
                        <option value="trine">Трин (120°)</option>
                        <option value="opposition">Оппозиция (180°)</option>
                        <option value="quincunx">Квиконс (150°)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="planet2">Вторая планета:</label>
                    <select id="planet2" required>
                        <option value="">Выберите планету</option>
                        <option value="Sun">Солнце</option>
                        <option value="Moon">Луна</option>
                        <option value="Mercury">Меркурий</option>
                        <option value="Venus">Венера</option>
                        <option value="Mars">Марс</option>
                        <option value="Jupiter">Юпитер</option>
                        <option value="Saturn">Сатурн</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="sign2">Знак второй планеты:</label>
                    <select id="sign2" required>
                        <option value="">Выберите знак</option>
                        <option value="Ari">Овен</option>
                        <option value="Tau">Телец</option>
                        <option value="Gem">Близнецы</option>
                        <option value="Can">Рак</option>
                        <option value="Leo">Лев</option>
                        <option value="Vir">Дева</option>
                        <option value="Lib">Весы</option>
                        <option value="Sco">Скорпион</option>
                        <option value="Sgr">Стрелец</option>
                        <option value="Cap">Козерог</option>
                        <option value="Aqr">Водолей</option>
                        <option value="Psc">Рыбы</option>
                    </select>
                </div>
                <button type="submit" class="btn-success">✅ Отправить в бот</button>
            </form>
        </section>
    </div>
    <script src="/static/js/mini-app.js"></script>
</body>
</html>"""
    return web.Response(text=content, content_type='text/html')


async def handle_static_file(request: web.Request) -> web.Response:
    """Отдаёт статические файлы (CSS, JS)."""
    file_path = request.match_info.get('filepath', '')
    static_dir = 'static'
    
    import os
    full_path = os.path.join(static_dir, file_path)
    
    if not os.path.exists(full_path):
        return web.Response(status=404, text='File not found')
    
    content_type_map = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.html': 'text/html',
        '.json': 'application/json'
    }
    
    ext = os.path.splitext(file_path)[1]
    content_type = content_type_map.get(ext, 'text/plain')
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return web.Response(text=content, content_type=content_type)


async def api_get_decks(request: web.Request) -> web.Response:
    """API: Получить список колод."""
    # В продакшене загружать из реального сервиса
    decks = [
        {"deck_id": "rider_waite", "name": "Райдер-Уэйт", "cards_count": 78},
        {"deck_id": "thoth", "name": "Таро Тота", "cards_count": 78},
        {"deck_id": "author_deck_146", "name": "Авторская колода 12 Планет", "cards_count": 146}
    ]
    return web.json_response(decks)


async def api_draw_cards(request: web.Request) -> web.Response:
    """API: Вытянуть карты из колоды."""
    try:
        data = await request.json()
        deck_id = data.get('deck_id')
        count = data.get('count', 1)
        
        # В продакшене вызывать реальный сервис TarotService
        # Здесь демо-ответ
        cards = []
        for i in range(count):
            cards.append({
                "card_id": f"card_{i}",
                "name": f"Карта {i+1}",
                "reversed": False,
                "image_url": f"/static/cards/card_{i}.jpg"
            })
        
        return web.json_response({"cards": cards})
    except Exception as e:
        logger.error(f"Ошибка API draw_cards: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_webapp_data(request: web.Request) -> web.Response:
    """Обработка данных от Mini App (альтернатива tg.sendData)."""
    try:
        data = await request.json()
        action = data.get('action')
        
        if action == 'tarot_spread':
            # Сохраняем данные для обработки ботом
            logger.info(f"Получены данные расклада: {data}")
            return web.json_response({"status": "ok"})
        
        elif action == 'astrology_aspect':
            logger.info(f"Получены данные аспекта: {data}")
            return web.json_response({"status": "ok"})
        
        return web.json_response({"status": "unknown_action"}, status=400)
    except Exception as e:
        logger.error(f"Ошибка обработки webapp данных: {e}")
        return web.json_response({"error": str(e)}, status=500)


def setup_web_server_routes(app: web.Application, tarot_service=None, astro_retriever=None):
    """Регистрация маршрутов веб-сервера."""
    app.router.add_get('/', handle_mini_app_index)
    app.router.add_get('/webapp', handle_mini_app_index)
    app.router.add_get('/static/{filepath:.*}', handle_static_file)
    
    # API endpoints
    app.router.add_get('/api/tarot/decks', api_get_decks)
    app.router.add_post('/api/tarot/draw', api_draw_cards)
    app.router.add_post('/api/webapp/data', handle_webapp_data)
    
    logger.info("✅ Маршруты веб-сервера зарегистрированы")
