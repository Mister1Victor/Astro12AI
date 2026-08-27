"""Смоук-тест модуля Таро. Запуск: python test_tarot_smoke.py"""
from core.tarot.loader import load_all_decks
from core.tarot.service import TarotService
from core.tarot import render


def main():
    decks = load_all_decks()
    assert decks, "❌ Колоды не загружены!"
    print(f"✅ Загружено колод: {len(decks)}")

    svc = TarotService(decks)
    deck = svc.get_deck()
    print(f"✅ Колода по умолчанию: {deck.name} ({deck.cards_count} карт)")
    assert deck.cards_count == 78, f"❌ Ожидалось 78 карт, получено {deck.cards_count}"

    # Перемешивание
    shuffled = svc.shuffle(deck.deck_id)
    assert len(shuffled) == 78, "❌ Перемешивание потеряло карты"
    print("✅ Перемешивание OK (78 карт)")

    # Карта Дня — 10 прогонов, проверяем случайность и корректность
    seen = set()
    for _ in range(10):
        card, rev = svc.card_of_the_day(deck.deck_id)
        assert card is not None
        seen.add(card.card_id)
    print(f"✅ Карта Дня OK: за 10 прогонов выпало {len(seen)} разных карт")

    # Расклад 3 карты — уникальность
    drawn = svc.draw_cards(3, deck.deck_id)
    ids = [c.card_id for c, _ in drawn]
    assert len(set(ids)) == 3, "❌ В раскладе дубликаты карт"
    print("✅ Расклад из 3 карт OK (без дубликатов)")

    # Рендер подписей
    card, rev = svc.card_of_the_day(deck.deck_id)
    caption = render.format_card_of_day(card, rev, deck)
    assert len(caption) > 20
    print("✅ Форматирование Карты Дня OK")

    print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()