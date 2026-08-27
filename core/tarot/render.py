"""Отображение Таро: поиск картинок и форматирование подписей (без Markdown-инъекций)."""
import os
from typing import Optional, Tuple, List

from core.tarot.models import TarotDeck, TarotCard

ORIENT_UP = "✅ Прямое положение"
ORIENT_REV = "🔻 Перевёрнутое положение"


def resolve_image(deck: TarotDeck, card: TarotCard) -> Optional[str]:
    """Абсолютный путь к картинке карты или None, если файла нет."""
    if not card.image:
        return None
    path = os.path.join(deck.images_dir, card.image)
    return path if os.path.exists(path) else None


def format_card_of_day(card: TarotCard, is_reversed: bool, deck: TarotDeck) -> str:
    """Подпись для Карты Дня."""
    orient = ORIENT_REV if is_reversed else ORIENT_UP
    lines = [
        "🃏 КАРТА ДНЯ",
        f"Карта: {card.name}",
        f"Колода: {deck.name}",
        f"Положение: {orient}",
        "",
    ]
    if card.keywords:
        lines.append("🔑 Ключевые слова: " + ", ".join(card.keywords))
    if card.astrology:
        lines.append("🪐 Астрология: " + card.astrology)
    meaning = card.get_meaning(is_reversed)
    if meaning:
        lines.append("")
        lines.append("📖 ТОЛКОВАНИЕ:")
        lines.append(meaning)
    if card.description:
        lines.append("")
        lines.append("🖼️ " + card.description)
    return "\n".join(lines)


def format_card_detail(card: TarotCard) -> str:
    """Подробная карточка (для просмотра в Колодах). Показывает оба положения."""
    lines = [f"🎴 {card.name}"]
    if card.astrology:
        lines.append("🪐 " + card.astrology)
    if card.keywords:
        lines.append("🔑 " + ", ".join(card.keywords))
    if card.upright:
        lines.append("")
        lines.append("✅ ПРЯМОЕ:")
        lines.append(card.upright)
    if card.reversed:
        lines.append("")
        lines.append("🔻 ПЕРЕВЁРНУТОЕ:")
        lines.append(card.reversed)
    if card.description:
        lines.append("")
        lines.append("🖼️ " + card.description)
    return "\n".join(lines)


def format_three_cards(drawn: List[Tuple[TarotCard, bool]], deck: TarotDeck) -> str:
    """Расклад «Три карты»."""
    positions = ["ПРОШЛОЕ", "НАСТОЯЩЕЕ", "БУДУЩЕЕ"]
    lines = [f"🔮 Расклад «Три карты» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:3]):
        pos = positions[i] if i < len(positions) else f"Позиция {i+1}"
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"【{pos}】 {card.name} ({orient})")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")
    return "\n".join(lines)
