"""
Веб-сервер Astro12AI Mini App.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Обслуживает:
  • Статические файлы (HTML, CSS, JS) Telegram Mini App
  • REST API для фронтенда (колоды, вытягивание карт)
  • Приём данных от Mini App через POST /api/webapp/data
  • Health check для Render keep-alive

Интеграция с ядром:
  • TarotService — реальное вытягивание карт из колод
  • AstroRetriever — подготовка астрологических данных
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web

from backend.logger import get_logger

logger = get_logger("web_server")

# ═══════════════════════════════════════════════════════════════
# ПУТИ
# ═══════════════════════════════════════════════════════════════
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# MIME-типы для статических файлов
CONTENT_TYPES = {
    ".html": "text/html",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf":  "font/ttf",
}


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════
async def handle_health_check(request: web.Request) -> web.Response:
    """Health check endpoint для Render keep-alive."""
    import time
    started = request.app.get("started_at", time.time())
    uptime = round((time.time() - started) / 60, 1)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><title>Astro12AI — Health</title></head>
<body style="font-family:sans-serif;text-align:center;padding:60px 20px;">
  <h2>✅ Astro12AI Mini App работает</h2>
  <h3>Школа Астрологии «12 Планет»</h3>
  <p>Аптайм: {uptime} мин.</p>
  <p style="opacity:0.6;font-size:13px;">Вернитесь в Telegram → /start</p>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


# ═══════════════════════════════════════════════════════════════
# СТАТИЧЕСКИЕ ФАЙЛЫ
# ═══════════════════════════════════════════════════════════════
async def handle_index(request: web.Request) -> web.Response:
    """Главная страница Mini App (index.html)."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return web.Response(
            text="<h1>index.html not found</h1>",
            status=404, content_type="text/html",
        )
    return web.Response(
        text=index_path.read_text(encoding="utf-8"),
        content_type="text/html",
    )


async def handle_static(request: web.Request) -> web.Response:
    """Отдача статических файлов из папки static/."""
    filepath = request.match_info.get("filepath", "")

    # Защита от directory traversal
    safe_path = (STATIC_DIR / filepath).resolve()
    if not str(safe_path).startswith(str(STATIC_DIR.resolve())):
        return web.Response(status=403, text="Forbidden")

    if not safe_path.is_file():
        return web.Response(status=404, text="File not found")

    ext = safe_path.suffix.lower()
    content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

    # Бинарные файлы (изображения, шрифты)
    if ext in (".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf"):
        return web.Response(
            body=safe_path.read_bytes(),
            content_type=content_type,
        )

    # Текстовые файлы
    return web.Response(
        text=safe_path.read_text(encoding="utf-8"),
        content_type=content_type,
    )


# ═══════════════════════════════════════════════════════════════
# API: КОЛОДЫ ТАРО
# ═══════════════════════════════════════════════════════════════
async def api_get_decks(request: web.Request) -> web.Response:
    """
    GET /api/tarot/decks
    Возвращает список колод с картами из реального TarotService.
    """
    tarot_service = request.app.get("tarot_service")

    if not tarot_service:
        # Fallback: демо-данные если сервис не подключён
        logger.warning("⚠️ TarotService не подключён — отдаём демо-данные")
        decks = [
            {"deck_id": "rider_waite",     "name": "Таро Райдера-Уэйта",
                "cards_count": 78},
            {"deck_id": "thoth",
                "name": "Таро Тота (Кроули)",              "cards_count": 78},
            {"deck_id": "author_deck",
                "name": "Авторская колода «12 Планет»",     "cards_count": 78},
            {"deck_id": "author_deck_146",
                "name": "Оракул «12 Планет»",              "cards_count": 146},
        ]
        return web.json_response(decks)

    # Реальные данные из TarotService
    try:
        all_decks = tarot_service.list_decks()
        result = []
        for deck in all_decks:
            if deck.cards_count > 0:  # Только колоды с картами
                result.append({
                    "deck_id":     deck.deck_id,
                    "name":        deck.name,
                    "author":      deck.author or "",
                    "description": deck.description or "",
                    "cards_count": deck.cards_count,
                    "deck_type":   deck.deck_type,
                    "has_images":  deck.has_images,
                })
        return web.json_response(result)
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка колод: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════
# API: ВЫТЯГИВАНИЕ КАРТ
# ═══════════════════════════════════════════════════════════════
async def api_draw_cards(request: web.Request) -> web.Response:
    """
    POST /api/tarot/draw
    Вытягивает карты из колоды через реальный TarotService.

    Body: {
        "deck_id": "rider_waite",
        "count": 3,
        "spread_type": "three",
        "user_id": 123456789    (опционально, для настройки перевёрнутых)
    }
    """
    tarot_service = request.app.get("tarot_service")

    try:
        data = await request.json()
        deck_id = data.get("deck_id", "")
        count = int(data.get("count", 1))
        spread_type = data.get("spread_type", "one")
        user_id = data.get("user_id")

        if count < 1 or count > 15:
            return web.json_response(
                {"error": "count должен быть от 1 до 15"}, status=400
            )

        if not tarot_service:
            return _demo_draw_response(count, spread_type)

        # Реальное вытягивание через TarotService
        deck = tarot_service.get_deck(deck_id)
        if not deck or not deck.cards:
            return web.json_response(
                {"error": f"Колода '{deck_id}' не найдена или пуста"},
                status=404,
            )

        drawn = tarot_service.draw_cards(count, deck_id, user_id)
        if not drawn or len(drawn) < count:
            return web.json_response(
                {"error": "Не удалось вытянуть достаточно карт"},
                status=500,
            )

        # Формируем ответ для фронтенда
        cards = []
        for card, is_reversed in drawn:
            card_data = {
                "card_id":   card.card_id,
                "name":      card.name,
                "reversed":  is_reversed,
                "arcana":    card.arcana,
                "suit":      card.suit,
                "number":    card.number,
                "keywords":  card.keywords,
                "astrology": card.astrology or "",
                "image_url": _resolve_card_image_url(deck, card),
            }

            # Для оракульных карт — добавляем Значение/Совет/Предупреждение
            if card.is_oracle:
                card_data["is_oracle"] = True
                card_data["upright"] = card.upright
                card_data["advice"] = card.advice
                card_data["warning"] = card.warning
            else:
                card_data["is_oracle"] = False
                card_data["upright"] = card.upright
                card_data["reversed_text"] = card.reversed

            cards.append(card_data)

        logger.info(
            f"🎴 API draw: deck={deck_id}, spread={spread_type}, "
            f"count={count}, drawn={len(cards)}"
        )
        return web.json_response({
            "cards":       cards,
            "deck_id":     deck_id,
            "deck_name":   deck.name,
            "spread_type": spread_type,
        })

    except json.JSONDecodeError:
        return web.json_response({"error": "Невалидный JSON"}, status=400)
    except Exception as e:
        logger.error(f"❌ Ошибка API draw_cards: {e}")
        return web.json_response({"error": str(e)}, status=500)


def _resolve_card_image_url(deck, card) -> Optional[str]:
    """Возвращает URL изображения карты для фронтенда."""
    if not card.image:
        return None

    # Проверяем стандартное место
    img_path = Path(deck.images_dir) / card.image
    if img_path.exists():
        return f"/static/decks/{deck.deck_id}/images/{card.image}"

    # Запасной вариант — в корне колоды
    deck_root = Path(deck.images_dir).parent
    alt_path = deck_root / card.image
    if alt_path.exists():
        return f"/static/decks/{deck.deck_id}/{card.image}"

    return None


def _demo_draw_response(count: int, spread_type: str) -> web.Response:
    """Демо-ответ когда TarotService не подключён (для разработки)."""
    cards = []
    for i in range(count):
        cards.append({
            "card_id":   f"demo_card_{i}",
            "name":      f"Карта {i + 1} (демо)",
            "reversed":  False,
            "arcana":    "major",
            "keywords":  ["демо"],
            "astrology": "",
            "image_url": None,
            "is_oracle": False,
            "upright":   "Демо-карта для тестирования интерфейса.",
        })
    return web.json_response({
        "cards":       cards,
        "deck_id":     "demo",
        "deck_name":   "Демо-колода",
        "spread_type": spread_type,
    })


# ═══════════════════════════════════════════════════════════════
# API: ДАННЫЕ ОТ MINI APP (для бота)
# ═══════════════════════════════════════════════════════════════
# In-memory хранилище pending-данных (в продакшене → Redis/SQLite)
_pending_webapp_data: Dict[int, List[Dict]] = {}


async def api_receive_webapp_data(request: web.Request) -> web.Response:
    """
    POST /api/webapp/data
    Принимает данные от Mini App и сохраняет для последующей
    обработки Telegram-ботом.

    Body: {
        "action":      "tarot_spread" | "astrology_aspect",
        "user_id":     123456789,
        "spread_type": "three",
        "deck_id":     "rider_waite",
        "cards":       [...],
        "timestamp":   1234567890
    }
    """
    try:
        data = await request.json()
        action = data.get("action", "unknown")
        user_id = data.get("user_id", 0)

        logger.info(
            f"📨 WebApp data: action={action}, user_id={user_id}, "
            f"keys={list(data.keys())}"
        )

        # Валидация
        if action == "tarot_spread":
            if not data.get("cards"):
                return web.json_response(
                    {"error": "Отсутствуют данные карт"}, status=400
                )
        elif action == "astrology_aspect":
            if not data.get("query"):
                return web.json_response(
                    {"error": "Отсутствует текст запроса"}, status=400
                )
        else:
            return web.json_response(
                {"error": f"Неизвестное действие: {action}"}, status=400
            )

        # Сохраняем для бота
        if user_id not in _pending_webapp_data:
            _pending_webapp_data[user_id] = []
        _pending_webapp_data[user_id].append(data)

        # Ограничиваем буфер (не более 10 pending на пользователя)
        if len(_pending_webapp_data[user_id]) > 10:
            _pending_webapp_data[user_id] = _pending_webapp_data[user_id][-10:]

        return web.json_response({"status": "ok", "action": action})

    except json.JSONDecodeError:
        return web.json_response({"error": "Невалидный JSON"}, status=400)
    except Exception as e:
        logger.error(f"❌ Ошибка приёма webapp данных: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_get_pending_data(request: web.Request) -> web.Response:
    """
    GET /api/webapp/pending?user_id=123
    Бот запрашивает pending-данные от Mini App для пользователя.
    """
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        data = _pending_webapp_data.pop(user_id, [])
        return web.json_response({"data": data})

    except (ValueError, TypeError):
        return web.json_response({"error": "Invalid user_id"}, status=400)


# ═══════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ═══════════════════════════════════════════════════════════════
def setup_web_server_routes(
    app: web.Application,
    tarot_service=None,
    astro_retriever=None,
):
    """
    Регистрация всех маршрутов веб-сервера.

    Args:
        app: aiohttp Application
        tarot_service: экземпляр TarotService (опционально)
        astro_retriever: экземпляр AstroRetriever (опционально)
    """
    # Сохраняем сервисы в app для доступа из хендлеров
    app["tarot_service"] = tarot_service
    app["astro_retriever"] = astro_retriever

    # ── Health check ──
    app.router.add_get("/",       handle_health_check)
    app.router.add_get("/health", handle_health_check)

    # ── Mini App ──
    app.router.add_get("/webapp",      handle_index)
    app.router.add_get("/tarot",       handle_index)
    app.router.add_get("/astrology",   handle_index)

    # ── Статика ──
    app.router.add_get("/static/{filepath:.*}", handle_static)

    # ── API: Таро ──
    app.router.add_get("/api/tarot/decks",  api_get_decks)
    app.router.add_post("/api/tarot/draw",   api_draw_cards)

    # ── API: WebApp данные ──
    app.router.add_post("/api/webapp/data",    api_receive_webapp_data)
    app.router.add_get("/api/webapp/pending", api_get_pending_data)

    logger.info("✅ Маршруты веб-сервера зарегистрированы")
    logger.info(f"   Статика: {STATIC_DIR}")
    logger.info(
        f"   TarotService: {'✅ подключён' if tarot_service else '⚠️ не подключён'}")
    logger.info(
        f"   AstroRetriever: {'✅ подключён' if astro_retriever else '⚠️ не подключён'}")
