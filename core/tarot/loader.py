"""Загрузка колод из data/tarot/decks/. Каждая папка = одна колода."""
import json
from pathlib import Path
from typing import Dict, Optional

from backend.logger import get_logger
from core.tarot.models import TarotDeck, TarotCard

logger = get_logger()

DECKS_ROOT = Path(__file__).resolve().parent.parent.parent / \
    "data" / "tarot" / "decks"
VALID_SUITS = {"wands", "cups", "swords", "pentacles"}


def _parse_card(card_data: dict) -> Optional[TarotCard]:
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
        advice=str(card_data.get("advice", "")).strip(),
        warning=str(card_data.get("warning", "")).strip(),
        group=str(card_data.get("group", "")).strip(),
        business=str(card_data.get("business", "")).strip(),
        relationships=str(card_data.get("relationships", "")).strip(),
        inspires=str(card_data.get("inspires", "")).strip(),
        warns=str(card_data.get("warns", "")).strip(),
        day_meaning=str(card_data.get("day_meaning", "")).strip(),
    )


def load_deck(deck_path: Path) -> Optional[TarotDeck]:
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
        deck_type=str(data.get("deck_type", "tarot")),
        images_dir=str(deck_path / "images"),
    )
    for card_data in data.get("cards", []):
        card = _parse_card(card_data)
        if card:
            deck.cards[card.card_id] = card

    if deck.cards_count == 0:
        logger.info(f"🛠️ Колода «{deck.name}» пуста (в разработке)")
    else:
        logger.info(
            f"🎴 Колода «{deck.name}» ({deck.deck_type}) загружена: {deck.cards_count} карт")
    return deck


def load_all_decks() -> Dict[str, TarotDeck]:
    decks: Dict[str, TarotDeck] = {}
    if not DECKS_ROOT.exists():
        logger.error(f"❌ Папка колод не найдена: {DECKS_ROOT}")
        return decks
    all_dirs = [d for d in sorted(DECKS_ROOT.iterdir())
                if d.is_dir() and not d.name.startswith("_")]
    logger.info(f"📂 Папка колод: {DECKS_ROOT}")
    logger.info(
        f"📂 Найдено подпапок: {len(all_dirs)} → {[d.name for d in all_dirs]}")
    for entry in all_dirs:
        deck = load_deck(entry)
        if deck:
            decks[deck.deck_id] = deck
    logger.info(
        f"🎴 Всего загружено колод: {len(decks)} → {list(decks.keys())}")
    return decks
