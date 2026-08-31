"""Модели данных Таро и Оракулов: карта и колода."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class TarotCard:
    """Одна карта Таро (или Оракула)."""
    card_id: str                                 # уникальный id: "major_00", "oracle_001"
    name: str
    arcana: str = "major"                        # "major" | "minor" | "oracle"
    suit: Optional[str] = None
    number: Optional[int] = None
    image: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    upright: str = ""                            # основное значение
    reversed: str = ""                           # перевёрнутое значение (таро)
    description: str = ""
    astrology: str = ""
    # Дополнительные поля оракульных колод (авторская система 12 планет)
    advice: str = ""                             # Совет
    warning: str = ""                            # Предупреждение
    # группа (у оракула — знак зодиака)
    group: str = ""

    def get_meaning(self, is_reversed: bool = False) -> str:
        """Значение с учётом ориентации."""
        if is_reversed and self.reversed:
            return self.reversed
        return self.upright

    @property
    def is_oracle(self) -> bool:
        """Оракульная карта (есть Совет/Предупреждение)."""
        return bool(self.advice or self.warning)

    @property
    def is_court(self) -> bool:
        return bool(self.card_id.split("_")[-1] in {"page", "knight", "queen", "king"})


@dataclass
class TarotDeck:
    """Колода Таро или Оракул."""
    deck_id: str
    name: str
    author: str = ""
    description: str = ""
    deck_type: str = "tarot"                     # "tarot" | "oracle"
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

    def groups_ordered(self) -> List[str]:
        """Упорядоченные группы карт (для оракула — знаки зодиака + затмения)."""
        seen = []
        for c in self.cards.values():
            if c.group and c.group not in seen:
                seen.append(c.group)
        return seen

    def cards_by_group(self, group: str) -> List[TarotCard]:
        return [c for c in self.cards.values() if c.group == group]

    @property
    def cards_count(self) -> int:
        return len(self.cards)

    @property
    def has_images(self) -> bool:
        return any(c.image for c in self.cards.values())
