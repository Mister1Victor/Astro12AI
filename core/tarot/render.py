"""Отображение Таро: картинки, подписи, астрологический символизм, достоинства стихий."""
import os
from typing import Optional, Tuple, List

from core.tarot.models import TarotDeck, TarotCard
from core.tarot.service import CELTIC_CROSS_POSITIONS, CHOICE_POSITIONS
from core.tarot import dignities as tarot_dignities

ORIENT_UP = "✅ Прямое положение"
ORIENT_REV = "🔻 Перевёрнутое положение"

# Позиции расклада «Плюс — Минус — Итог»
PLUS_MINUS_POSITIONS = [
    "ПЛЮС — Благоприятные факторы, плюсы решения",
    "МИНУС — Скрытые угрозы, риски",
    "ИТОГ — Общий результат при выборе этого пути",
]

# Позиции расклада «Мысли — Чувства — Действия»
MIND_HEART_POSITIONS = [
    "МЫСЛИ — Что человек думает о вас / ситуации",
    "ЧУВСТВА — Что он чувствует на самом деле",
    "ДЕЙСТВИЯ — Как он проявит себя в действиях",
]

# Позиции «Динамического триплета» (вектор чтения)
TRIPLET_POSITIONS = [
    "Карта 1 — ЯДРО (суть)",
    "Карта 2 — МОДИФИКАТОР (катализатор)",
    "Карта 3 — ВЕКТОР (итог)",
]


def resolve_image(deck: TarotDeck, card: TarotCard) -> Optional[str]:
    """Абсолютный путь к картинке карты или None."""
    if not card.image:
        return None
    path = os.path.join(deck.images_dir, card.image)
    return path if os.path.exists(path) else None


def choice_positions_list() -> List[str]:
    """7 позиций расклада «Вариант выбора» по порядку карт."""
    return (
        CHOICE_POSITIONS["option_a"]
        + CHOICE_POSITIONS["option_b"]
        + [CHOICE_POSITIONS["advice"]]
    )


def triplet_dignities(drawn) -> List[str]:
    """Строки Достоинств стихий для триплета (для подписи и для LLM)."""
    return tarot_dignities.triplet_dignities(drawn)


def spread_cards_visual(deck: TarotDeck, drawn, positions: List[str]) -> List[dict]:
    """Визуал расклада: для каждой карты {"path", "caption", "name"}."""
    items = []
    for i, (card, rev) in enumerate(drawn):
        pos = positions[i] if i < len(positions) else f"Позиция {i + 1}"
        orient = "перевёрнуто" if rev else "прямо"
        lines = [f"【{pos}】", f"{card.name} — {orient}"]
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        items.append({
            "path": resolve_image(deck, card),
            "caption": "\n".join(lines)[:1024],
            "name": card.name,
        })
    return items


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
    """Подробная карточка (для просмотра в Колодах)."""
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


def format_three_cards(drawn, deck: TarotDeck) -> str:
    """Расклад «Три карты»."""
    positions = ["ПРОШЛОЕ", "НАСТОЯЩЕЕ", "БУДУЩЕЕ"]
    lines = [f"🔮 Расклад «Три карты» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:3]):
        pos = positions[i] if i < len(positions) else f"Позиция {i + 1}"
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"【{pos}】 {card.name} ({orient})")
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")
    return "\n".join(lines)


def format_plus_minus(drawn, deck: TarotDeck) -> str:
    """Расклад «Плюс — Минус — Итог»."""
    icons = ["➕", "➖", "🎯"]
    lines = [f"➕➖ Расклад «Плюс — Минус — Итог» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:3]):
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(
            f"{icons[i]}【{PLUS_MINUS_POSITIONS[i]}】 {card.name} ({orient})")
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")
    return "\n".join(lines)


def format_mind_heart(drawn, deck: TarotDeck) -> str:
    """Расклад «Мысли — Чувства — Действия» (для отношений)."""
    icons = ["💭", "❤️", "🎬"]
    lines = [f"💭 Расклад «Мысли — Чувства — Действия» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:3]):
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(
            f"{icons[i]}【{MIND_HEART_POSITIONS[i]}】 {card.name} ({orient})")
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")
    return "\n".join(lines)


def format_yes_no(card: TarotCard, is_reversed: bool, deck: TarotDeck, question: str) -> str:
    """Расклад «Да или Нет»: одна карта-ответ."""
    orient = ORIENT_REV if is_reversed else ORIENT_UP
    lines = [
        f"🎯 Расклад «Да или Нет» — {deck.name}",
        "",
        f"❓ Вопрос: {question}",
        "",
        f"【КАРТА ОТВЕТА】 {card.name}",
        f"Положение: {orient}",
        f"Стихия: {tarot_dignities.element_label(card)}",
    ]
    if card.astrology:
        lines.append(f"🪐 {card.astrology}")
    meaning = card.get_meaning(is_reversed)
    if meaning:
        lines.append("")
        lines.append("📖 " + meaning)
    return "\n".join(lines)


def format_triplet(drawn, deck: TarotDeck) -> str:
    """Динамический триплет: карты + анализ Достоинств стихий."""
    lines = [f"🌀 Расклад «Динамический триплет» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:3]):
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"【{TRIPLET_POSITIONS[i]}】 {card.name} ({orient})")
        lines.append(f"Стихия: {tarot_dignities.element_label(card)}")
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")
    lines.append("⚖️ ДОСТОИНСТВА СТИХИЙ:")
    lines.extend(tarot_dignities.triplet_dignities(drawn))
    lines.append("")
    lines.append("Карты читаются как одно связное предложение: "
                 "карта 2 влияет на карту 1, карта 3 — на карту 2 и направляет всю связку к финалу.")
    return "\n".join(lines)


def format_celtic_cross(drawn, deck: TarotDeck) -> str:
    """Расклад «Кельтский крест» (10 карт)."""
    lines = [f"✝️ Расклад «Кельтский крест» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:10]):
        pos = CELTIC_CROSS_POSITIONS[i] if i < len(
            CELTIC_CROSS_POSITIONS) else f"Позиция {i + 1}"
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"【{i + 1}. {pos}】 {card.name} ({orient})")
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")
    return "\n".join(lines)


def format_choice_spread(drawn, deck: TarotDeck, essence: str, option_a: str, option_b: str) -> str:
    """Расклад «Вариант выбора» (7 карт: 3 + 3 + совет)."""
    lines = [
        f"⚖️ Расклад «Вариант выбора» — {deck.name}",
        "",
        f"📝 Суть выбора: {essence}",
        "",
        f"🅰️ ВАРИАНТ 1: {option_a}",
    ]

    for i, (card, rev) in enumerate(drawn[:3]):
        pos = CHOICE_POSITIONS["option_a"][i]
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"  【{pos}】 {card.name} ({orient})")
        if card.astrology:
            lines.append(f"  🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(f"  {meaning}")
        lines.append("")

    lines.append(f"🅱️ ВАРИАНТ 2: {option_b}")

    for i, (card, rev) in enumerate(drawn[3:6]):
        pos = CHOICE_POSITIONS["option_b"][i]
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"  【{pos}】 {card.name} ({orient})")
        if card.astrology:
            lines.append(f"  🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(f"  {meaning}")
        lines.append("")

    if len(drawn) >= 7:
        card, rev = drawn[6]
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"💡 СОВЕТ: {card.name} ({orient})")
        if card.astrology:
            lines.append(f"🪐 {card.astrology}")
        meaning = card.get_meaning(rev)
        if meaning:
            lines.append(meaning)
        lines.append("")

    return "\n".join(lines)
