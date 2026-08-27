"""Модуль Таро Школы «12 Планет». Автономен от RAG/Астрологии."""
from core.tarot.models import TarotCard, TarotDeck
from core.tarot.loader import load_all_decks, load_deck
from core.tarot.service import TarotService

__all__ = ["TarotCard", "TarotDeck",
           "load_all_decks", "load_deck", "TarotService"]
