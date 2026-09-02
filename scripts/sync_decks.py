#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/sync_decks.py
Синхронизация колод Таро с текстовыми файлами значений (источник истины).

Поведение:
  - Если текстовый файл колоды НЕ существует — создаёт его из встроенных данных (миграция).
  - Если текстовый файл существует — читает его и пересобирает deck.json.

Рабочий цикл пользователя:
  1. Отредактировать core/tarot/texts/<колода>.txt (добавить/удалить значения).
     ВАЖНО: каждое значение пишется в ОДНУ строку (без переносов внутри поля).
  2. python scripts/sync_decks.py
  3. git commit + git push (деплой).

Скрипт НЕ импортирует модуль core (самодостаточный), поэтому запускается
из любой папки без ошибок путей:
  python scripts/sync_decks.py
"""
import init_author_deck as iad
import init_tarot_data as itd
import os
import sys
import json
from pathlib import Path

# Защита консоли (Windows cp1251)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# === Пути (вычисляются от самого файла — работают из любой папки) ===
_SCRIPT_DIR = Path(__file__).resolve().parent          # .../Astro12AI/scripts
_PROJECT_ROOT = _SCRIPT_DIR.parent                     # .../Astro12AI
TEXTS_DIR = _PROJECT_ROOT / "core" / "tarot" / "texts"
DECKS_DIR = _PROJECT_ROOT / "data" / "tarot" / "decks"

# Генераторы лежат в той же папке scripts/ — добавляем её в sys.path
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


DECK_NAMES = ["rider_waite", "thoth", "author_deck"]
RANK_NUMBERS = {rank: num for rank, (_, num) in itd.RANK_NAMES.items()}
NEW_FIELDS = ("business", "relationships", "inspires", "warns", "day_meaning")

# === Формат текстового файла: «метка в файле» -> «поле в deck.json» ===
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

HEADER_TEMPLATE = """# ═══════════════════════════════════════════════════════════════
# Текстовый файл значений карт: {deck_name_display}
# Источник истины: правьте этот файл, затем запускайте scripts/sync_decks.py
# Формат: блоки '### Карта: <id>' с полями 'Ключ: значение'.
# Каждое значение пишется в ОДНУ строку (без переносов внутри поля).
#
# Поля: Название, Астрология, КлючевыеСлова, Прямое, Перевёрнутое, Описание,
#        ВБизнесеИРаботе, ВОтношениях, КартаСоветует, КартаПредупреждает, КартаДня.
#
# Поля ВБизнесеИРаботе / ВОтношениях / КартаСоветует / КартаПредупреждает /
# КартаДня заполните авторскими материалами Школы.
# ═══════════════════════════════════════════════════════════════"""


# ============================================================
# ЧТЕНИЕ / ЗАПИСЬ текстовых файлов
# ============================================================
def parse_deck_text(text):
    """Парсит текст файла в {card_id: {field: value}}."""
    cards = {}
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


def load_deck_texts(deck_name):
    path = TEXTS_DIR / f"{deck_name}.txt"
    if not path.exists():
        return None
    return parse_deck_text(path.read_text(encoding="utf-8"))


def card_to_block(card_id, fields):
    lines = [f"### Карта: {card_id}"]
    for label, field in FIELD_KEYS:
        value = fields.get(field, "")
        if field == "keywords" and isinstance(value, list):
            value = ", ".join(value)
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def write_deck_text_file(deck_name, cards, header=""):
    TEXTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TEXTS_DIR / f"{deck_name}.txt"
    blocks = [header] if header else []
    for card_id, fields in cards.items():
        blocks.append(card_to_block(card_id, fields))
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return path


# ============================================================
# ПРЕОБРАЗОВАНИЯ карт
# ============================================================
def card_to_fields(card):
    """card dict -> поля для текстового файла (миграция)."""
    return {
        "name": card.get("name", ""),
        "astrology": card.get("astrology", ""),
        "keywords": card.get("keywords", []),
        "upright": card.get("upright", ""),
        "reversed": card.get("reversed", ""),
        "description": card.get("description", ""),
        "business": card.get("business", ""),
        "relationships": card.get("relationships", ""),
        "inspires": card.get("inspires", ""),
        "warns": card.get("warns", ""),
        "day_meaning": card.get("day_meaning", ""),
    }


def fields_to_card(card_id, fields):
    """Поля из текстового файла -> card dict."""
    kw_raw = fields.get("keywords", "")
    card = {
        "id": card_id,
        "name": fields.get("name", ""),
        "image": f"{card_id}.jpg",
        "astrology": fields.get("astrology", ""),
        "keywords": [k.strip() for k in kw_raw.split(",") if k.strip()],
        "upright": fields.get("upright", ""),
        "reversed": fields.get("reversed", ""),
        "description": fields.get("description", ""),
        "business": fields.get("business", ""),
        "relationships": fields.get("relationships", ""),
        "inspires": fields.get("inspires", ""),
        "warns": fields.get("warns", ""),
        "day_meaning": fields.get("day_meaning", ""),
    }
    if card_id.startswith("major_"):
        card["arcana"] = "major"
        try:
            card["number"] = int(card_id.split("_")[1])
        except (ValueError, IndexError):
            card["number"] = 0
    else:
        suit, _, rank = card_id.partition("_")
        card["arcana"] = "minor"
        card["suit"] = suit
        card["number"] = RANK_NUMBERS.get(rank, 0)
    return card


def builtin_cards(deck_name):
    if deck_name == "rider_waite":
        return itd.build_rider_waite()["cards"]
    if deck_name == "thoth":
        return itd.build_thoth()["cards"]
    if deck_name == "author_deck":
        return iad.build_author_deck()["cards"]
    raise ValueError(f"Неизвестная колода: {deck_name}")


def builtin_deck_meta(deck_name):
    if deck_name == "rider_waite":
        d = itd.build_rider_waite()
    elif deck_name == "thoth":
        d = itd.build_thoth()
    else:
        d = iad.build_author_deck()
    return {k: v for k, v in d.items() if k != "cards"}


# ============================================================
# СИНХРОНИЗАЦИЯ
# ============================================================
def sync_deck(deck_name):
    builtin = builtin_cards(deck_name)
    builtin_by_id = {c["id"]: c for c in builtin}
    meta = builtin_deck_meta(deck_name)
    text_data = load_deck_texts(deck_name)

    if text_data is None:
        # --- МИГРАЦИЯ: создаём текстовый файл из встроенных данных ---
        cards_dict = {c["id"]: card_to_fields(c) for c in builtin}
        header = HEADER_TEMPLATE.format(
            deck_name_display=meta.get("name", deck_name))
        path = write_deck_text_file(deck_name, cards_dict, header)
        print(
            f"✅ МИГРАЦИЯ: создан текстовый файл {path} ({len(cards_dict)} карт)")
        final_cards = []
        for c in builtin:
            card = dict(c)
            for f in NEW_FIELDS:
                card.setdefault(f, "")
            final_cards.append(card)
    else:
        # --- СИНХРОНИЗАЦИЯ: читаем текстовый файл ---
        final_cards = []
        for cid, fields in text_data.items():
            card = fields_to_card(cid, fields)
            # Сохраняем корректное имя картинки из встроенных данных
            if cid in builtin_by_id and builtin_by_id[cid].get("image"):
                card["image"] = builtin_by_id[cid]["image"]
            final_cards.append(card)
        print(
            f"📖 {deck_name}: загружено из текстового файла {len(final_cards)} карт")

    deck = dict(meta)
    deck["cards"] = final_cards
    out_path = DECKS_DIR / deck_name / "deck.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2)
    print(f"✅ {deck_name}: записан {out_path} ({len(final_cards)} карт)")


def main():
    print("🔄 Синхронизация колод с текстовыми файлами...")
    print(f"   Корень проекта: {_PROJECT_ROOT}")
    for deck_name in DECK_NAMES:
        sync_deck(deck_name)
    print("\n🎉 Готово. Теперь можно править core/tarot/texts/*.txt и запускать скрипт повторно.")


if __name__ == "__main__":
    main()
