"""
services/web_server.py
Веб-сервер Mini App и API (production).
Маршруты (корень '/' обслуживает main.py — здесь НЕ регистрируется):
  GET  /webapp                                — главная страница Mini App
  GET  /static/{filepath}                     — статика (css/js)
  GET  /api/tarot/image/{deck_id}/{filename}  — картинки карт
  GET  /api/tarot/decks                       — список колод (реальный TarotService)
  POST /api/tarot/draw                        — вытянуть карты (реальный TarotService)
  POST /api/tarot/interpret                   — толкование расклада через LLM
  POST /api/webapp/data                       — резервный приём данных Mini App
"""
import logging
import os
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DECKS_DIR = BASE_DIR / "data" / "tarot" / "decks"

CONTENT_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".html": "text/html",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


# ============================================================
# MINI APP: ГЛАВНАЯ СТРАНИЦА
# ============================================================
async def handle_mini_app_index(request: web.Request) -> web.Response:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return web.Response(status=404, text="Mini App not found: static/index.html")
    return web.Response(text=index.read_text(encoding="utf-8"),
                        content_type="text/html")


# ============================================================
# СТАТИКА
# ============================================================
async def handle_static_file(request: web.Request) -> web.Response:
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


# ============================================================
# API: ВЫТЯНУТЬ КАРТЫ (реальный TarotService)
# ============================================================
async def api_draw_cards(request: web.Request) -> web.Response:
    svc = request.app.get("tarot_service")
    if not svc:
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

    deck = svc.get_deck(deck_id)
    if not deck or not deck.cards:
        return web.json_response({"error": "deck not found"}, status=404)

    drawn = svc.draw_cards(count, deck.deck_id, user_id=None)
    cards = []
    for card, is_reversed in drawn:
        if not use_reversed:
            is_reversed = False
        cards.append({
            "card_id": card.card_id,
            "name": card.name,
            "reversed": is_reversed,
            "astrology": card.astrology or "",
            "keywords": card.keywords or [],
            "image_url": (f"/api/tarot/image/{deck.deck_id}/{card.image}"
                          if card.image else None),
        })
    return web.json_response({"cards": cards, "deck_id": deck.deck_id})


# ============================================================
# API: ТОЛКОВАНИЕ РАСКЛАДА (LLM) — ответ ВНУТРИ Mini App
# ============================================================
async def api_interpret_spread(request: web.Request) -> web.Response:
    svc = request.app.get("tarot_service")
    llm = request.app.get("llm")
    astro_retriever = request.app.get("astro_retriever")
    if not svc or not llm:
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

    deck = svc.get_deck(deck_id)
    if not deck or not deck.cards:
        return web.json_response({"error": "deck not found"}, status=404)

    # Восстанавливаем РЕАЛЬНЫЕ карты колоды (со значениями) — не пустышки
    drawn = []
    for c in cards_data:
        card = deck.get_card(c.get("card_id"))
        if card:
            drawn.append((card, bool(c.get("reversed", False))))
    if not drawn:
        return web.json_response({"error": "no cards restored"}, status=400)

    # Виды позиций для позиционной логики оракула
    position_kinds = None
    if spread_type == "three" and three_card_type == "plus-minus-result":
        position_kinds = ["positive", "negative", "neutral"]

    if not question:
        question = "Интерпретируй расклад из Mini App в контексте вопроса пользователя."

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
            {"error": "rate_limit",
             "message": "Сервис ИИ временно перегружен. Попробуйте через 1–2 минуты."},
            status=503)
    return web.json_response({"interpretation": interpretation, "success": True})


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
# РЕГИСТРАЦИЯ МАРШРУТОВ ('/' НЕ трогаем — он в main.py)
# ============================================================
def setup_web_server_routes(app: web.Application, tarot_service=None, astro_retriever=None, llm=None):
    """Регистрация маршрутов веб-сервера."""
    # Mini App и статика
    app.router.add_get('/webapp', handle_mini_app_index)
    app.router.add_get('/static/{filepath:.*}', handle_static_file)

    # API endpoints
    app.router.add_get('/api/tarot/decks', api_get_decks)
    app.router.add_post('/api/tarot/draw', api_draw_cards)
    app.router.add_post('/api/webapp/data', handle_webapp_data)

    logger.info("✅ Маршруты веб-сервера зарегистрированы")
