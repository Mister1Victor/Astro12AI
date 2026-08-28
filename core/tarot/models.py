"""Модели данных Таро: карта и колода."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class TarotCard:
    """Одна карта Таро."""
    card_id: str                                 # уникальный id: "major_00", "wands_2"
    name: str                                    # родовое имя: "Двойка Жезлов"
    arcana: str = "major"                        # "major" | "minor"
    suit: Optional[str] = None                   # wands/cups/swords/pentacles
    number: Optional[int] = None
    image: Optional[str] = None                  # имя файла в images/
    # колодочное название: «Владея миром», «Владычество»
    title: str = ""
    keywords: List[str] = field(default_factory=list)
    upright: str = ""
    reversed: str = ""
    description: str = ""
    astrology: str = ""                          # «Марс в Овне»

    @property
    def full_name(self) -> str:
        """Имя карты с колодочным названием: Двойка Жезлов — «Владея миром»."""
        if self.title:
            return f"{self.name} — «{self.title}»"
        return self.name

    def get_meaning(self, is_reversed: bool = False) -> str:
        if is_reversed and self.reversed:
            return self.reversed
        return self.upright

    @property
    def is_court(self) -> bool:
        return self.card_id.split("_")[-1] in {"page", "knight", "queen", "king"}


@dataclass
class TarotDeck:
    """Колода Таро."""
    deck_id: str
    name: str
    author: str = ""
    description: str = ""
    images_dir: str = ""
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
