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
        allow_reversed = data.get('allow_reversed', False)
        
        # Демо-колода карт для примера
        demo_cards_list = [
            {"card_id": "0", "name": "Шут", "reversed": False},
            {"card_id": "1", "name": "Маг", "reversed": False},
            {"card_id": "2", "name": "Жрица", "reversed": False},
            {"card_id": "3", "name": "Императрица", "reversed": False},
            {"card_id": "4", "name": "Император", "reversed": False},
            {"card_id": "5", "name": "Иерофант", "reversed": False},
            {"card_id": "6", "name": "Влюблённые", "reversed": False},
            {"card_id": "7", "name": "Колесница", "reversed": False},
            {"card_id": "8", "name": "Сила", "reversed": False},
            {"card_id": "9", "name": "Отшельник", "reversed": False},
            {"card_id": "10", "name": "Колесо Фортуны", "reversed": False},
            {"card_id": "11", "name": "Справедливость", "reversed": False},
            {"card_id": "12", "name": "Повешенный", "reversed": False},
            {"card_id": "13", "name": "Смерть", "reversed": False},
            {"card_id": "14", "name": "Умеренность", "reversed": False},
            {"card_id": "15", "name": "Дьявол", "reversed": False},
            {"card_id": "16", "name": "Башня", "reversed": False},
            {"card_id": "17", "name": "Звезда", "reversed": False},
            {"card_id": "18", "name": "Луна", "reversed": False},
            {"card_id": "19", "name": "Солнце", "reversed": False},
            {"card_id": "20", "name": "Суд", "reversed": False},
            {"card_id": "21", "name": "Мир", "reversed": False}
        ]
        
        import random
        cards = []
        used_indices = set()
        
        for i in range(count):
            # Выбираем случайную карту без повторений
            while True:
                idx = random.randint(0, len(demo_cards_list) - 1)
                if idx not in used_indices:
                    used_indices.add(idx)
                    break
            
            card_template = demo_cards_list[idx]
            is_reversed = allow_reversed and random.random() < 0.3
            
            cards.append({
                "card_id": card_template["card_id"],
                "name": card_template["name"],
                "reversed": is_reversed,
                "image_url": ""
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
