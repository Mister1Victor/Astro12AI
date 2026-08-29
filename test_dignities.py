"""Тест достоинств стихий на примерах из ТЗ."""
from core.tarot.models import TarotCard
from core.tarot import dignities as dg

fire      = TarotCard(card_id='wands_ace',  name='Туз Жезлов',      arcana='minor', suit='wands')
air       = TarotCard(card_id='swords_8',   name='8 Мечей',         arcana='minor', suit='swords')
air_major = TarotCard(card_id='major_01',   name='Маг (I)',         arcana='major')

print("Пример 1 (синергия):")
print("  Огонь->Воздух :", dg.pair_dignity(fire, air))
print("  Воздух->Старш.:", dg.pair_dignity(air, air_major))
print()

fire3 = TarotCard(card_id='wands_3',    name='3 Жезлов',        arcana='minor', suit='wands')
water = TarotCard(card_id='cups_queen', name='Королева Кубков', arcana='minor', suit='cups')
air5  = TarotCard(card_id='swords_5',   name='5 Мечей',         arcana='minor', suit='swords')

print("Пример 2 (антагонизм):")
print("  Огонь->Вода   :", dg.pair_dignity(fire3, water))
print("  Вода->Воздух  :", dg.pair_dignity(water, air5))
