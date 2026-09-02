"""Отображение Таро и Оракулов: картинки, подписи, символизм, позиции."""
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

# Позиции «Динамического триплета»
TRIPLET_POSITIONS = [
    "Карта 1 — ЯДРО (суть)",
    "Карта 2 — МОДИФИКАТОР (катализатор)",
    "Карта 3 — ВЕКТОР (итог)",
]


def resolve_image(deck: TarotDeck, card: TarotCard) -> Optional[str]:
    """Абсолютный путь к картинке карты или None.
    Ищет в <колода>/images/, затем в корне папки колоды."""
    if not card.image:
        return None
    # 1) Стандартное место: <колода>/images/<имя файла>
    path = os.path.join(deck.images_dir, card.image)
    if os.path.exists(path):
        return path
    # 2) Запасной вариант: файл лежит в корне папки колоды
    #    (оригинальный oracle_generator.py сохраняет PNG именно туда)
    deck_root = os.path.dirname(deck.images_dir)
    alt_path = os.path.join(deck_root, card.image)
    if os.path.exists(alt_path):
        return alt_path
    return None


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


# ============================================================
# ПОЗИЦИОННАЯ ЛОГИКА для Оракула (Значение / Совет / Предупреждение)
# ============================================================
def card_context_for_position(card: TarotCard, is_reversed: bool, kind: str = "neutral") -> str:
    """
    Текст карты для LLM с учётом позиции в раскладе.

    Для оракульных карт (есть Совет/Предупреждение):
      'positive' (плюс, достоинство)  -> Значение + Совет (карта советует)
      'negative' (минус, недостаток)  -> Значение + Предупреждение (карта предупреждает)
      'day'      (Карта Дня)          -> Значение + Совет + Предупреждение (оба варианта)
      'neutral'  (прочие позиции)     -> Значение + Совет + Предупреждение (полный контекст)

    Для обычных карт Таро — значение по ориентации, как раньше.
    """
    base = card.get_meaning(is_reversed)
    if not card.is_oracle:
        return base

    parts = [f"Значение: {base}"] if base else []
    if kind == "positive":
        if card.advice:
            parts.append(f"Совет: {card.advice}")
    elif kind == "negative":
        if card.warning:
            parts.append(f"Предупреждение: {card.warning}")
    else:  # 'day' и 'neutral' — оба варианта
        if card.advice:
            parts.append(f"Совет: {card.advice}")
        if card.warning:
            parts.append(f"Предупреждение: {card.warning}")
    return "\n".join(parts)


# ============================================================
# ВИЗУАЛ РАСКЛАДОВ
# ============================================================
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


# ============================================================
# ФОРМАТЫ ПОДПИСЕЙ
# ============================================================def format_card_of_day(card: TarotCard, is_reversed: bool, deck: TarotDeck) -> str:
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

    if card.is_oracle:
        if card.upright:
            lines += ["", "📖 ЗНАЧЕНИЕ:", card.upright]
        if card.advice:
            lines += ["", "💡 СОВЕТ:", card.advice]
        if card.warning:
            lines += ["", "⚠️ ПРЕДУПРЕЖДЕНИЕ:", card.warning]
        if card.day_meaning:
            lines += ["", "🃏 КАРТА ДНЯ:", card.day_meaning]
    else:
        meaning = card.get_meaning(is_reversed)
        if meaning:
            lines += ["", "📖 ТОЛКОВАНИЕ:", meaning]
        if card.day_meaning:
            lines += ["", "🃏 КАРТА ДНЯ:", card.day_meaning]
        if card.inspires:
            lines += ["", "🌟 КАРТА СОВЕТУЕТ:", card.inspires]
        if card.warns:
            lines += ["", "⚠️ КАРТА ПРЕДУПРЕЖДАЕТ:", card.warns]

    if card.description:
        lines += ["", "🖼️ " + card.description]
    return "\n".join(lines)


def format_card_detail(card: TarotCard) -> str:
    """Подробная карточка (просмотр в Колодах): весь текст под изображением."""
    lines = [f"🎴 {card.name}"]
    if card.astrology:
        lines.append("🪐 " + card.astrology)
    if card.keywords:
        lines.append("🔑 " + ", ".join(card.keywords))

    if card.is_oracle:
        if card.upright:
            lines += ["", "📖 ЗНАЧЕНИЕ:", card.upright]
        if card.advice:
            lines += ["", "💡 СОВЕТ:", card.advice]
        if card.warning:
            lines += ["", "⚠️ ПРЕДУПРЕЖДЕНИЕ:", card.warning]
    else:
        if card.upright:
            lines += ["", "✅ ПРЯМОЕ:", card.upright]
        if card.reversed:
            lines += ["", "🔻 ПЕРЕВЁРНУТОЕ:", card.reversed]

    # Дополнительные разделы (показываются, только если заполнены)
    if card.business:
        lines += ["", "💼 В БИЗНЕСЕ И РАБОТЕ:", card.business]
    if card.relationships:
        lines += ["", "❤️ В ОТНОШЕНИЯХ:", card.relationships]
    if card.inspires:
        lines += ["", "🌟 КАРТА СОВЕТУЕТ (ВДОХНОВЛЯЕТ):", card.inspires]
    if card.warns:
        lines += ["", "⚠️ КАРТА ПРЕДУПРЕЖДАЕТ:", card.warns]
    if card.day_meaning:
        lines += ["", "🃏 КАРТА ДНЯ:", card.day_meaning]

    if card.description:
        lines += ["", "🖼️ " + card.description]
    return "\n".join(lines)


def format_three_cards(drawn, deck: TarotDeck) -> str:
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


def format_triplet(drawn, deck: TarotDeck) -> str:
    lines = [f"🌀 Расклад «Динамический триплет» — {deck.name}", ""]
    for i, (card, rev) in enumerate(drawn[:3]):
        orient = "перевёрнуто" if rev else "прямо"
        lines.append(f"【{TRIPLET_POSITIONS[i]}】 {card.name} ({orient})")
        if card.arcana != "oracle":
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
