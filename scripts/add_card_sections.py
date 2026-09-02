"""
Одноразовая миграция: добавляет 5 новых разделов во ВСЕ карты всех колод.
Разделы (пустые, для ручного заполнения):
  business      — В бизнесе и работе
  relationships — В отношениях
  inspires      — Карта советует (вдохновляет)
  warns         — Карта предупреждает
  day_meaning   — Карта дня

Запуск:
    python scripts/add_card_sections.py
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DECKS = ROOT / "data" / "tarot" / "decks"

NEW_FIELDS = ["business", "relationships", "inspires", "warns", "day_meaning"]


def migrate_deck(deck_json: Path):
    with open(deck_json, encoding="utf-8") as f:
        data = json.load(f)
    cards = data.get("cards", [])
    added = 0
    for card in cards:
        for field in NEW_FIELDS:
            if field not in card:
                card[field] = ""
                added += 1
    if added:
        with open(deck_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return added, len(cards)


def main():
    if not DECKS.exists():
        print(f"❌ Папка не найдена: {DECKS}")
        return
    total = 0
    for deck_dir in sorted(DECKS.iterdir()):
        if not deck_dir.is_dir():
            continue
        dj = deck_dir / "deck.json"
        if not dj.exists():
            continue
        added, n_cards = migrate_deck(dj)
        mark = "✅" if added else "⏭️ "
        print(f"{mark} {deck_dir.name}: карт={n_cards}, добавлено полей={added}")
        total += added
    print(f"\n🎉 Готово. Всего добавлено полей: {total}")
    print("Теперь вручную впишите значения в deck.json")
    print("(поля: business, relationships, inspires, warns, day_meaning).")


if __name__ == "__main__":
    main()
