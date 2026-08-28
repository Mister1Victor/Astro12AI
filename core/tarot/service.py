"""Бизнес-логика Таро: перемешивание, Карта Дня, расклады."""
import random
from typing import Optional, Tuple, List

from backend.logger import get_logger
from core.tarot.models import TarotDeck, TarotCard

logger = get_logger()

# Позиции Кельтского креста (10 карт)
CELTIC_CROSS_POSITIONS = [
    "Суть ситуации (сигнификатор)",
    "Препятствие / что пересекает",
    "Цель / сознательное стремление",
    "Корни / подсознательное",
    "Прошлое (уходящее)",
    "Ближайшее будущее",
    "Я (самовосприятие)",
    "Окружение (внешние влияния)",
    "Надежды и страхи",
    "Итог",
]

# Позиции Варианта выбора (7 карт)
CHOICE_POSITIONS = {
    "option_a": [
        "Вариант 1 — Достоинство",
        "Вариант 1 — Недостаток",
        "Вариант 1 — Исход",
    ],
    "option_b": [
        "Вариант 2 — Достоинство",
        "Вариант 2 — Недостаток",
        "Вариант 2 — Исход",
    ],
    "advice": "Совет",
}


class TarotService:
    """Сервис Таро. Хранит колоды и предоставляет операции над ними."""

    def __init__(self, decks: dict):
        self.decks = decks
        self.user_settings: dict = {}
        # Умный выбор дефолтной колоды: берём ту, где больше всего карт
        # (защита от ситуации, когда шаблон _template становится дефолтом)
        self.default_deck_id = None
        if decks:
            self.default_deck_id = max(
                decks.keys(), key=lambda k: decks[k].cards_count)
        logger.info(
            f"🎴 TarotService инициализирован. "
            f"Колода по умолчанию: {self.default_deck_id}"
        )

    # ---------- настройки пользователя ----------
    def set_user_reversed_setting(self, user_id: int, use_reversed: bool):
        """Запоминает настройку перевёрнутых карт для пользователя."""
        self.user_settings[user_id] = use_reversed
        logger.info(f"🎴 Пользователь {user_id}: перевёрнутые={use_reversed}")

    def get_user_reversed_setting(self, user_id: int) -> bool:
        """Возвращает настройку перевёрнутых карт (по умолчанию True)."""
        return self.user_settings.get(user_id, True)

    # ---------- колоды ----------
    def get_deck(self, deck_id: Optional[str] = None) -> Optional[TarotDeck]:
        """Колода по id или колода по умолчанию."""
        if deck_id:
            return self.decks.get(deck_id)
        if self.default_deck_id:
            return self.decks.get(self.default_deck_id)
        return None

    def list_decks(self) -> List[TarotDeck]:
        """Список всех загруженных колод."""
        return list(self.decks.values())

    # ---------- перемешивание ----------
    def shuffle(self, deck_id: Optional[str] = None) -> List[TarotCard]:
        """Перемешивает колоду и возвращает случайный порядок."""
        deck = self.get_deck(deck_id)
        if not deck:
            return []
        cards = deck.all_cards()
        random.shuffle(cards)
        logger.info(f"🔀 Перемешана колода «{deck.name}» ({len(cards)} карт)")
        return cards

    # ---------- Карта Дня ----------
    def card_of_the_day(
        self,
        deck_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[Optional[TarotCard], bool]:
        """
        Карта Дня: случайная карта из колоды.
        Возвращает (карта, перевёрнута ли).
        """
        deck = self.get_deck(deck_id)
        if not deck or not deck.cards:
            return None, False

        cards = self.shuffle(deck.deck_id)
        if not cards:
            return None, False

        card = random.choice(cards)

        # Учитываем настройку пользователя
        use_reversed = self.get_user_reversed_setting(
            user_id) if user_id else True
        is_reversed = (random.random() < 0.5) if use_reversed else False

        logger.info(
            f"🃏 Карта Дня из «{deck.name}»: {card.name} "
            f"(перевёрнута={is_reversed})"
        )
        return card, is_reversed

    # ---------- расклады ----------
    def draw_cards(
        self,
        count: int,
        deck_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Tuple[TarotCard, bool]]:
        """
        Тянет N уникальных карт для расклада.
        Перемешивает колоду каждый раз для полной случайности.
        Возвращает [(карта, перевёрнута)].
        """
        deck = self.get_deck(deck_id)
        if not deck:
            logger.error(f"❌ Колода не найдена: {deck_id}")
            return []

        cards = self.shuffle(deck.deck_id)
        drawn = cards[: max(0, count)]

        if len(drawn) < count:
            logger.error(
                f"❌ Недостаточно карт: запрошено {count}, вытянуто {len(drawn)}"
            )

        use_reversed = self.get_user_reversed_setting(
            user_id) if user_id else True
        result = [(c, (use_reversed and random.random() < 0.5)) for c in drawn]

        logger.info(
            f"🎴 Вытянуто {len(result)} карт из «{deck.name}» "
            f"(use_reversed={use_reversed})"
        )
        return result

    def draw_three_cards(
        self,
        deck_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Tuple[TarotCard, bool]]:
        """Трёхкарточный расклад: Прошлое — Настоящее — Будущее."""
        return self.draw_cards(3, deck_id, user_id)

    def draw_celtic_cross(
        self,
        deck_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Tuple[TarotCard, bool]]:
        """Кельтский крест: 10 карт."""
        return self.draw_cards(10, deck_id, user_id)

    def draw_choice_spread(
        self,
        deck_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Tuple[TarotCard, bool]]:
        """Вариант выбора: 7 карт (3 для варианта A + 3 для варианта B + 1 совет)."""
        drawn = self.draw_cards(7, deck_id, user_id)
        if len(drawn) != 7:
            logger.error(
                f"❌ КРИТИЧЕСКАЯ ОШИБКА: Вариант выбора должен иметь 7 карт, "
                f"получено {len(drawn)}"
            )
        return drawn
