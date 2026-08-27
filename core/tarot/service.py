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
    "Итог"
]

# Позиции Варианта выбора (7 карт)
CHOICE_POSITIONS = {
    "option_a": [
        "Вариант 1 — Достоинство",
        "Вариант 1 — Недостаток",
        "Вариант 1 — Исход"
    ],
    "option_b": [
        "Вариант 2 — Достоинство",
        "Вариант 2 — Недостаток",
        "Вариант 2 — Исход"
    ],
    "advice": "Совет"
}


class TarotService:
    """Сервис Таро. Хранит колоды и предоставляет операции над ними."""

    def __init__(self, decks: dict):
        self.decks = decks
        self.default_deck_id = next(iter(decks), None) if decks else None
        logger.info(
            f"🎴 TarotService инициализирован. Колода по умолчанию: {self.default_deck_id}")

    # ---------- колоды ----------
    def get_deck(self, deck_id: Optional[str] = None) -> Optional[TarotDeck]:
        """Колода по id или колода по умолчанию."""
        if deck_id:
            return self.decks.get(deck_id)
        return self.decks.get(self.default_deck_id) if self.default_deck_id else None

    def list_decks(self) -> List[TarotDeck]:
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
    ) -> Tuple[Optional[TarotCard], bool]:
        """
        Карта Дня: случайная карта из колоды.
        Возвращает (карта, перевёрнута ли).
        Перемешивает колоду каждый раз для полной случайности.
        """
        deck = self.get_deck(deck_id)
        if not deck or not deck.cards:
            return None, False

        # Перемешиваем колоду перед выбором
        cards = self.shuffle(deck_id)

        card = random.choice(cards)
        is_reversed = random.random() < 0.5  # 50% — перевёрнутая

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
        allow_reversed: bool = True,
    ) -> List[Tuple[TarotCard, bool]]:
        """
        Тянет N уникальных карт для расклада.
        Перемешивает колоду каждый раз для полной случайности.
        Возвращает [(карта, перевёрнута)].
        """
        deck = self.get_deck(deck_id)
        if not deck:
            return []

        # Перемешиваем колоду перед вытягиванием
        cards = self.shuffle(deck_id)
        drawn = cards[: max(0, count)]
        result = [(c, (allow_reversed and random.random() < 0.5))
                  for c in drawn]
        logger.info(f"🎴 Вытянуто {len(result)} карт из «{deck.name}»")
        return result

    def draw_three_cards(self, deck_id: Optional[str] = None) -> List[Tuple[TarotCard, bool]]:
        """Трёхкарточный расклад: Прошлое — Настоящее — Будущее."""
        return self.draw_cards(3, deck_id)

    def draw_celtic_cross(self, deck_id: Optional[str] = None) -> List[Tuple[TarotCard, bool]]:
        """Кельтский крест: 10 карт."""
        return self.draw_cards(10, deck_id)

    def draw_choice_spread(self, deck_id: Optional[str] = None) -> List[Tuple[TarotCard, bool]]:
        """Вариант выбора: 7 карт (3 для варианта A + 3 для варианта B + 1 совет)."""
        return self.draw_cards(7, deck_id)
