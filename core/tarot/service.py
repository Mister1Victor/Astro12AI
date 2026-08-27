"""Бизнес-логика Таро: перемешивание, Карта Дня, вытягивание карт для раскладов."""
import random
from typing import Optional, Tuple, List

from backend.logger import get_logger
from core.tarot.models import TarotDeck, TarotCard

logger = get_logger()


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
        seed: Optional[str] = None,
    ) -> Tuple[Optional[TarotCard], bool]:
        """
        Карта Дня: случайная карта из колоды.
        Возвращает (карта, перевёрнута ли).
        Если передан seed — выбор детерминирован (например, 'дата:user_id').
        """
        deck = self.get_deck(deck_id)
        if not deck or not deck.cards:
            return None, False

        cards = deck.all_cards()
        rnd = random.Random(seed) if seed is not None else random.Random()

        card = rnd.choice(cards)
        is_reversed = rnd.random() < 0.5  # 50% — перевёрнутая

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
        """Тянет N уникальных карт для расклада. Возвращает [(карта, перевёрнута)]."""
        deck = self.get_deck(deck_id)
        if not deck:
            return []
        cards = deck.all_cards()
        random.shuffle(cards)
        drawn = cards[: max(0, count)]
        result = [(c, (allow_reversed and random.random() < 0.5))
                  for c in drawn]
        logger.info(f"🎴 Вытянуто {len(result)} карт из «{deck.name}»")
        return result
