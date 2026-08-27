"""Модели данных Таро: карта и колода."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class TarotCard:
    """Одна карта Таро."""
    card_id: str                                 # уникальный id: "major_00", "wands_ace"
    name: str                                    # "Шут (0)"
    arcana: str = "major"                        # "major" | "minor"
    # для minor: wands/cups/swords/pentacles
    suit: Optional[str] = None
    number: Optional[int] = None                 # номер карты
    # имя файла в images/ (например major_00.jpg)
    image: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    upright: str = ""                            # толкование в прямом положении
    reversed: str = ""                           # толкование в перевёрнутом положении
    description: str = ""                        # описание символики
    astrology: str = ""                          # астрологическое соответствие

    def get_meaning(self, is_reversed: bool = False) -> str:
        """Толкование с учётом ориентации."""
        if is_reversed and self.reversed:
            return self.reversed
        return self.upright

    @property
    def is_court(self) -> bool:
        """Придворная ли карта (Паж/Рыцарь/Королева/Король)."""
        return bool(self.card_id.split("_")[-1] in {"page", "knight", "queen", "king"})


@dataclass
class TarotDeck:
    """Колода Таро."""
    deck_id: str                                 # уникальный id папки: "rider_waite"
    name: str                                    # отображаемое название
    author: str = ""
    description: str = ""
    images_dir: str = ""                         # абсолютный путь к images/
    cards: Dict[str, TarotCard] = field(default_factory=dict)

    def get_card(self, card_id: str) -> Optional[TarotCard]:
        return self.cards.get(card_id)

    def all_cards(self) -> List[TarotCard]:
        return list(self.cards.values())

    def major_arcana(self) -> List[TarotCard]:
        return [c for c in self.cards.values() if c.arcana == "major"]

    def minor_by_suit(self, suit: str) -> List[TarotCard]:
        return [c for c in self.cards.values() if c.arcana == "minor" and c.suit == suit]

    @property
    def cards_count(self) -> int:
        return len(self.cards)

    @property
    def has_images(self) -> bool:
        return any(c.image for c in self.cards.values())
