#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точечный редактор контекстных полей карты в deck.json.

Показать текущие значения:
  python scripts/edit_card.py rider_waite major_01 --show

Изменить одно поле:
  python scripts/edit_card.py rider_waite major_01 business "Новый текст про бизнес."

Поля: business, relationships, inspires, warns, day_meaning
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["business", "relationships", "inspires", "warns", "day_meaning"]


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print(__doc__)
        sys.exit(1)

    deck_name, card_id = args[0], args[1]
    path = ROOT / "data" / "tarot" / "decks" / deck_name / "deck.json"
    if not path.exists():
        print(f"❌ Не найден файл: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        deck = json.load(f)

    card = next((c for c in deck["cards"] if c["id"] == card_id), None)
    if card is None:
        print(f"❌ Карта '{card_id}' не найдена в колоде '{deck_name}'")
        sys.exit(1)

    # Режим просмотра
    if args[2] == "--show":
        print(f"🎴 {deck_name} / {card_id} ({card.get('name', '')})")
        for f_ in FIELDS:
            print(f"   {f_}: {repr(card.get(f_, ''))}")
        return

    # Режим записи
    if len(args) < 4:
        print(__doc__)
        sys.exit(1)
    field, value = args[2], args[3]
    if field not in FIELDS:
        print(f"❌ Неизвестное поле '{field}'. Допустимые: {', '.join(FIELDS)}")
        sys.exit(1)

    card[field] = value
    with open(path, "w", encoding="utf-8") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2)
    print(f"✅ Обновлено: {deck_name}/{card_id} → {field}")


if __name__ == "__main__":
    main()
