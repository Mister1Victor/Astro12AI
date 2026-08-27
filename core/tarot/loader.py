"""Загрузка колод из data/tarot/decks/. Каждая папка = одна колода."""
import json
from pathlib import Path
from typing import Dict, Optional

from backend.logger import get_logger
from core.tarot.models import TarotDeck, TarotCard

logger = get_logger()

# Корень с колодами: <project_root>/data/tarot/decks
DECKS_ROOT = Path(__file__).resolve().parent.parent.parent / \
    "data" / "tarot" / "decks"

VALID_SUITS = {"wands", "cups", "swords", "pentacles"}


def _parse_card(card_data: dict) -> Optional[TarotCard]:
    """Разбирает одну карту из JSON. Возвращает None при отсутствии id/name."""
    card_id = str(card_data.get("id", "")).strip()
    name = str(card_data.get("name", "")).strip()
    if not card_id or not name:
        return None
    return TarotCard(
        card_id=card_id,
        name=name,
        arcana=card_data.get("arcana", "major"),
        suit=card_data.get("suit") if card_data.get(
            "suit") in VALID_SUITS else None,
        number=card_data.get("number"),
        image=card_data.get("image"),
        keywords=list(card_data.get("keywords", [])),
        upright=str(card_data.get("upright", "")).strip(),
        reversed=str(card_data.get("reversed", "")).strip(),
        description=str(card_data.get("description", "")).strip(),
        astrology=str(card_data.get("astrology", "")).strip(),
    )


def load_deck(deck_path: Path) -> Optional[TarotDeck]:
    """Загружает одну колоду из папки. Папка обязана содержать deck.json."""
    deck_json = deck_path / "deck.json"
    if not deck_json.exists():
        logger.warning(f"⚠️ deck.json не найден: {deck_json}")
        return None

    try:
        with open(deck_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"❌ Ошибка чтения {deck_json}: {e}")
        return None

    deck_id = str(data.get("id", deck_path.name)).strip()
    deck = TarotDeck(
        deck_id=deck_id,
        name=str(data.get("name", deck_id)),
        author=str(data.get("author", "")),
        description=str(data.get("description", "")),
        images_dir=str(deck_path / "images"),
    )

    for card_data in data.get("cards", []):
        card = _parse_card(card_data)
        if card:
            deck.cards[card.card_id] = card

    logger.info(f"🎴 Колода «{deck.name}» загружена: {deck.cards_count} карт")
    return deck


def load_all_decks() -> Dict[str, TarotDeck]:
    """Загружает ВСЕ колоды из data/tarot/decks/ (подпапки)."""
    decks: Dict[str, TarotDeck] = {}

    if not DECKS_ROOT.exists():
        logger.warning(f"⚠️ Папка колод не найдена: {DECKS_ROOT}")
        return decks

    for entry in sorted(DECKS_ROOT.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            deck = load_deck(entry)
            if deck and deck.cards_count > 0:
                decks[deck.deck_id] = deck

    logger.info(f"🎴 Всего загружено колод: {len(decks)}")
    return decks
