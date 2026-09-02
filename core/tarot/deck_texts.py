"""
core/tarot/deck_texts.py
Источник истины для значений карт — текстовые файлы в core/tarot/texts/.
Формат: блоки '### Карта: <id>' с полями 'Ключ: значение' (значение в одну строку).
Пользователь правит текстовые файлы вручную, затем запускает scripts/sync_decks.py.
"""
from pathlib import Path
from typing import Dict, Optional

TEXTS_DIR = Path(__file__).resolve().parent / "texts"

# (метка в файле -> имя поля в card dict). Порядок определяет порядок записи.
FIELD_KEYS = [
    ("Название", "name"),
    ("Астрология", "astrology"),
    ("КлючевыеСлова", "keywords"),
    ("Прямое", "upright"),
    ("Перевёрнутое", "reversed"),
    ("Описание", "description"),
    ("ВБизнесеИРаботе", "business"),
    ("ВОтношениях", "relationships"),
    ("КартаСоветует", "inspires"),
    ("КартаПредупреждает", "warns"),
    ("КартаДня", "day_meaning"),
]
LABEL_TO_FIELD = {label: field for label, field in FIELD_KEYS}


def parse_deck_text(text: str) -> Dict[str, dict]:
    """Парсит текст файла колоды -> {card_id: {field: value}}."""
    cards: Dict[str, dict] = {}
    current_id = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("### Карта:"):
            current_id = line.split(":", 1)[1].strip()
            cards[current_id] = {}
            continue
        if not line.strip() or line.startswith("#"):
            continue
        if current_id is None or ":" not in line:
            continue
        label, _, value = line.partition(":")
        field = LABEL_TO_FIELD.get(label.strip())
        if field:
            cards[current_id][field] = value.strip()
    return cards


def load_deck_texts(deck_name: str) -> Optional[Dict[str, dict]]:
    """Загружает текстовый файл колоды. Возвращает None, если файла нет."""
    path = TEXTS_DIR / f"{deck_name}.txt"
    if not path.exists():
        return None
    return parse_deck_text(path.read_text(encoding="utf-8"))


def card_to_block(card_id: str, fields: dict) -> str:
    lines = [f"### Карта: {card_id}"]
    for label, field in FIELD_KEYS:
        value = fields.get(field, "")
        if field == "keywords" and isinstance(value, list):
            value = ", ".join(value)
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def write_deck_text_file(deck_name: str, cards: Dict[str, dict], header: str = "") -> Path:
    """Записывает карты в текстовый файл (используется миграцией)."""
    TEXTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TEXTS_DIR / f"{deck_name}.txt"
    blocks = [header] if header else []
    for card_id, fields in cards.items():
        blocks.append(card_to_block(card_id, fields))
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return path
