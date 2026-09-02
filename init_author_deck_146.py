#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оракул «12 Планет» — генератор авторской колоды (146 карт).

Читает авторские тексты карт (Значение/Совет/Предупреждение) из:
  1. файла core/tarot/card_data.txt  (основной источник),
  2. переменной RAW_CARD_DATA в oracle_generator.py (если файл с текстом есть).

Генерирует:
  - изображения 600×900  -> data/tarot/decks/author_deck_146/images/
  - deck.json (формат ядра Таро) -> data/tarot/decks/author_deck_146/deck.json

Запуск:
    pip install Pillow
    python init_author_deck_146.py [--force]
"""
import re
import sys
import os
import json
from pathlib import Path

# Защита консоли Windows (cp1251 не умеет эмодзи)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 0. ПУТИ (файл лежит в КОРНЕ проекта)
# ============================================================
ROOT = Path(__file__).resolve().parent
DECK_DIR = ROOT / "data" / "tarot" / "decks" / "author_deck_146"
IMAGES_DIR = DECK_DIR / "images"
CARD_DATA_FILE = ROOT / "core" / "tarot" / "card_data.txt"


# ============================================================
# 0.1. ЗАГРУЗКА АВТОРСКИХ ТЕКСТОВ
# ============================================================
def _load_raw_texts() -> str:
    # Приоритет 1: файл с текстами
    if CARD_DATA_FILE.exists():
        with open(CARD_DATA_FILE, encoding="utf-8") as f:
            print(f"📖 Тексты карт взяты из: {CARD_DATA_FILE}")
            return f.read()
    # Приоритет 2: переменная в генераторе (первая версия)
    try:
        from oracle_generator import RAW_CARD_DATA
        print("📖 Тексты карт взяты из: oracle_generator.RAW_CARD_DATA")
        return RAW_CARD_DATA
    except ImportError:
        pass
    print("❌ Не найден источник текстов карт.")
    print("   Ожидается один из:")
    print(f"     - {CARD_DATA_FILE}")
    print("     - переменная RAW_CARD_DATA в oracle_generator.py")
    sys.exit(1)


def parse_card_texts(raw: str) -> dict:
    """
    Парсит тексты в словарь {номер: (значение, совет, предупреждение)}.
    Устойчив к ** разметке, переносам строк и служебным заголовкам.
    """
    text = raw.replace("**", "")
    parts = re.split(r"Карта №(\d+):", text)
    headers_re = re.compile(
        r"^\s*(?:-{2,}|#+.*|КАРТЫ ДЛЯ ЗНАКА.*|ДОПОЛНИТЕЛЬНЫЕ КАРТЫ.*|"
        r"144 КАРТЫ.*|146 КАРТЫ.*|Заменить:.*)\s*$",
        re.MULTILINE)

    cards = {}
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""

        def section(label, stop_label):
            stop_pat = f"(?=\\n\\s*{stop_label}:|\\Z)" if stop_label else "(?=\\Z)"
            m = re.search(rf"{label}:\s*(.*?){stop_pat}", body, re.DOTALL)
            if not m:
                return ""
            cleaned = headers_re.sub(" ", m.group(1))
            return " ".join(cleaned.split())

        meaning = section("Значение", "Совет")
        advice = section("Совет", "Предупреждение")
        warning = section("Предупреждение", "")
        cards[num] = (meaning, advice, warning)
    return cards


RAW_CARD_DATA = _load_raw_texts()
CARD_TEXTS = parse_card_texts(RAW_CARD_DATA)
print(f"📖 Распознано карт: {len(CARD_TEXTS)}")
if len(CARD_TEXTS) < 146:
    print("⚠️ Ожидалось 146 карт. Проверьте формат файла с текстами.")


# ============================================================
# 1. ШРИФТЫ
# ============================================================
def _find_font(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Не найден ни один шрифт: {candidates}")


if sys.platform.startswith("win"):
    FONT_TEXT = "C:/Windows/Fonts/arial.ttf"
    FONT_TEXT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
    FONT_SYMBOLS = "C:/Windows/Fonts/seguisym.ttf"
else:
    FONT_TEXT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_TEXT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_SYMBOLS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

FONT_TEXT = _find_font(
    [FONT_TEXT, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
FONT_TEXT_BOLD = _find_font(
    [FONT_TEXT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
FONT_TEXT_MEDIUM = FONT_TEXT
FONT_SYMBOLS = _find_font(
    [FONT_SYMBOLS, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])


# ============================================================
# 2. ПАЛИТРА ПО СТИХИЯМ
# ============================================================
PALETTE = {
    "огонь": {"bg_top": (45, 12, 8), "bg_bottom": (160, 50, 15),
              "accent": (255, 130, 50), "accent2": (255, 200, 120),
              "text": (255, 248, 240), "subtext": (230, 180, 140),
              "border": (220, 90, 30), "panel": (25, 8, 5)},
    "земля": {"bg_top": (12, 30, 10), "bg_bottom": (50, 90, 35),
              "accent": (140, 200, 80), "accent2": (200, 230, 150),
              "text": (245, 255, 235), "subtext": (190, 210, 160),
              "border": (100, 150, 50), "panel": (8, 20, 6)},
    "воздух": {"bg_top": (10, 20, 40), "bg_bottom": (45, 80, 120),
               "accent": (120, 190, 255), "accent2": (180, 220, 255),
               "text": (235, 245, 255), "subtext": (170, 200, 230),
               "border": (80, 150, 220), "panel": (8, 15, 30)},
    "вода": {"bg_top": (8, 12, 35), "bg_bottom": (30, 50, 100),
             "accent": (100, 150, 255), "accent2": (160, 190, 255),
             "text": (230, 235, 255), "subtext": (160, 180, 230),
             "border": (70, 110, 200), "panel": (6, 10, 25)},
}
ECLIPSE_PALETTE = {"bg_top": (3, 3, 3), "bg_bottom": (35, 25, 15),
                   "accent": (255, 190, 60), "accent2": (255, 230, 150),
                   "text": (255, 250, 240), "subtext": (210, 180, 130),
                   "border": (180, 140, 50), "panel": (15, 12, 8)}


# ============================================================
# 3. ДАННЫЕ СИСТЕМЫ
# ============================================================
SIGNS = [
    {"name": "Овен", "symbol": "♈", "ruler": "Марс", "element": "огонь",
     "house": "1 дом", "sphere": "сфера активных действий"},
    {"name": "Телец", "symbol": "♉", "ruler": "Венера", "element": "земля",
     "house": "2 дом", "sphere": "материальная сфера и накопления"},
    {"name": "Близнецы", "symbol": "♊", "ruler": "Меркурий", "element": "воздух",
     "house": "3 дом", "sphere": "сфера коммуникаций и обучения"},
    {"name": "Рак", "symbol": "♋", "ruler": "Луна", "element": "вода",
     "house": "4 дом", "sphere": "семейная сфера и жильё"},
    {"name": "Лев", "symbol": "♌", "ruler": "Солнце", "element": "огонь",
     "house": "5 дом", "sphere": "сфера творчества и выступлений"},
    {"name": "Дева", "symbol": "♍", "ruler": "Эрида", "element": "земля",
     "house": "6 дом", "sphere": "сфера здоровья и работы/услуг"},
    {"name": "Весы", "symbol": "♎", "ruler": "Плутон", "element": "воздух",
     "house": "7 дом", "sphere": "сфера партнёрства и отношений"},
    {"name": "Скорпион", "symbol": "♏", "ruler": "Нептун", "element": "вода",
     "house": "8 дом", "sphere": "финансовая и сексуальная сфера"},
    {"name": "Стрелец", "symbol": "♐", "ruler": "Уран", "element": "огонь",
     "house": "9 дом", "sphere": "сфера знаний и путешествий"},
    {"name": "Козерог", "symbol": "♑", "ruler": "Сатурн", "element": "земля",
     "house": "10 дом", "sphere": "деловая сфера и карьера"},
    {"name": "Водолей", "symbol": "♒", "ruler": "Юпитер", "element": "воздух",
     "house": "11 дом", "sphere": "социальная сфера"},
    {"name": "Рыбы", "symbol": "♓", "ruler": "Церера", "element": "вода",
     "house": "12 дом", "sphere": "духовная сфера"},
]

PLANETS = {
    "Марс": {"symbol": "♂", "element": "огонь", "motto": "Я действую!",
             "keywords": ["воля", "действие", "энергия", "борьба", "победа", "инициатива"]},
    "Венера": {"symbol": "♀", "element": "земля", "motto": "Я приобретаю и наслаждаюсь",
               "keywords": ["красота", "удовольствие", "гармония", "ценность", "накопление"]},
    "Меркурий": {"symbol": "☿", "element": "воздух", "motto": "Я узнаю и передаю",
                 "keywords": ["общение", "мышление", "учёба", "информация", "передвижение"]},
    "Луна": {"symbol": "☽", "element": "вода", "motto": "Я чувствую и забочусь",
             "keywords": ["эмоции", "интуиция", "семья", "забота", "привычки"]},
    "Солнце": {"symbol": "☉", "element": "огонь", "motto": "Привет холмики, Я - гора!!",
               "keywords": ["личность", "лидерство", "власть", "харизма", "жизненная сила"]},
    "Эрида": {"symbol": "ERa", "element": "земля",
              "motto": "Я исправляю / исцеляю и довожу до совершенства",
              "keywords": ["здоровье", "ремонтировать", "лечить болезни", "ремонт", "работа", "оздоровление"]},
    "Плутон": {"symbol": "♇", "element": "воздух", "motto": "Я с тобой — или против тебя",
               "keywords": ["партнёрство", "переговоры", "союз", "взаимодействие", "конфликт"]},
    "Нептун": {"symbol": "♆", "element": "вода", "motto": "Я хочу и получаю",
               "keywords": ["желание", "финансы", "прибыль", "потребление", "страсть"]},
    "Уран": {"symbol": "♅", "element": "огонь", "motto": "Я знаю и объясняю",
             "keywords": ["знания", "путешествия", "неожиданность", "скорость", "открытия"]},
    "Сатурн": {"symbol": "♄", "element": "земля", "motto": "Я работаю и контролирую",
               "keywords": ["дисциплина", "карьера", "ответственность", "порядок", "время"]},
    "Юпитер": {"symbol": "♃", "element": "воздух", "motto": "Я вижу людей и вдохновляю",
               "keywords": ["люди", "дружба", "общество", "наблюдение", "вдохновение"]},
    "Церера": {"symbol": "⚳", "element": "вода", "motto": "Я чувствую и помогаю",
               "keywords": ["помощь", "сострадание", "вера", "жертвенность", "мечта"]},
}

# Фиксированный порядок планет (одинаков для всех знаков — как в card_data.txt)
RULERS_ORDER = ["Марс", "Венера", "Меркурий", "Луна", "Солнце",
                "Эрида", "Плутон", "Нептун", "Уран", "Сатурн", "Юпитер", "Церера"]

PREPOSITIONAL_PHRASE = {
    "Овен": "в Овне", "Телец": "в Тельце", "Близнецы": "в Близнецах",
    "Рак": "в Раке", "Лев": "во Льве", "Дева": "в Деве",
    "Весы": "в Весах", "Скорпион": "в Скорпионе", "Стрелец": "в Стрельце",
    "Козерог": "в Козероге", "Водолей": "в Водолее", "Рыбы": "в Рыбах",
}

ELEMENT_NAMES = {"огонь": "Огонь", "земля": "Земля",
                 "воздух": "Воздух", "вода": "Вода"}


# ============================================================
# 4. УТИЛИТЫ РИСОВАНИЯ
# ============================================================
def draw_gradient(draw, width, height, color_top, color_bottom):
    for y in range(height):
        ratio = y / height
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def wrap_text(text, font, max_width, draw):
    words, lines, current = text.split(), [], ""
    for word in words:
        test = current + " " + word if current else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def shorten_text(text, max_chars=280):
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def draw_alchemy_symbol(draw, element, center_x, y_top, size, color):
    half = size / 2
    if element in ("огонь", "воздух"):
        draw.polygon([(center_x, y_top), (center_x - half, y_top + size),
                      (center_x + half, y_top + size)], outline=color, width=2)
        if element == "воздух":
            y_line = y_top + size * 0.6
            draw.line([(center_x - half, y_line),
                      (center_x + half, y_line)], fill=color, width=2)
    elif element in ("земля", "вода"):
        draw.polygon([(center_x, y_top + size), (center_x - half, y_top),
                      (center_x + half, y_top)], outline=color, width=2)
        if element == "земля":
            y_line = y_top + size * 0.4
            draw.line([(center_x - half, y_line),
                      (center_x + half, y_line)], fill=color, width=2)


# ============================================================
# 5. РИСОВАЛЬЩИК КАРТ
# ============================================================
def draw_oracle_card(planet_name, sign, card_num, meaning, advice, warning,
                     is_eclipse=False, eclipse_type=None):
    W, H = 600, 900
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    if is_eclipse:
        c = ECLIPSE_PALETTE
        title = "СОЛНЕЧНОЕ ЗАТМЕНИЕ" if eclipse_type == "sun" else "ЛУННОЕ ЗАТМЕНИЕ"
        subtitle = "☉ Новолуние" if eclipse_type == "sun" else "☽ Полнолуние"
        planet_symbol = "☉" if eclipse_type == "sun" else "☽"
        sign_symbol = "●" if eclipse_type == "sun" else "○"
        is_ruler = False
    else:
        c = PALETTE[sign["element"]]
        p = PLANETS[planet_name]
        title = planet_name
        subtitle = PREPOSITIONAL_PHRASE[sign["name"]]
        planet_symbol = p["symbol"]
        sign_symbol = sign["symbol"]
        is_ruler = sign["ruler"] == planet_name

    draw_gradient(draw, W, H, c["bg_top"], c["bg_bottom"])
    margin = 18
    draw.rounded_rectangle([margin, margin, W - margin,
                           H - margin], radius=16, outline=c["border"], width=2)
    draw.rounded_rectangle([margin + 6, margin + 6, W - margin - 6,
                           H - margin - 6], radius=13, outline=c["accent"], width=1)

    f_num = ImageFont.truetype(FONT_TEXT_BOLD, 56)
    f_title = ImageFont.truetype(FONT_TEXT_BOLD, 42)
    f_subtitle = ImageFont.truetype(FONT_TEXT_MEDIUM, 26)
    f_header = ImageFont.truetype(FONT_TEXT_BOLD, 20)
    f_body = ImageFont.truetype(FONT_TEXT, 16)
    f_symbol = ImageFont.truetype(FONT_SYMBOLS, 90)
    f_small_sym = ImageFont.truetype(FONT_SYMBOLS, 60)
    f_motto = ImageFont.truetype(FONT_TEXT_MEDIUM, 16)
    f_element = ImageFont.truetype(FONT_TEXT_BOLD, 22)

    draw.text((W // 2, 45), str(card_num), font=f_num,
              fill=c["subtext"], anchor="mm")
    draw.line([(70, 75), (W - 70, 75)], fill=c["border"], width=1)

    if is_eclipse:
        draw.text((W // 2, 165), planet_symbol, font=f_symbol,
                  fill=c["accent"], anchor="mm")
        draw.text((W // 2, 265), sign_symbol, font=f_symbol,
                  fill=c["accent2"], anchor="mm")
        draw.text((W // 2, 385), title, font=f_title,
                  fill=c["text"], anchor="mm")
        draw.text((W // 2, 435), subtitle, font=f_subtitle,
                  fill=c["subtext"], anchor="mm")
        draw.rounded_rectangle([170, 475, W - 170, 510],
                               radius=8, fill=c["accent"])
        draw.text((W // 2, 492), "ОСОБАЯ КАРТА",
                  font=f_element, fill=c["bg_top"], anchor="mm")
        panel_top, y = 520, 540
    else:
        draw.text((W // 2, 150), planet_symbol, font=f_symbol,
                  fill=c["accent"], anchor="mm")
        draw.text((W // 2, 235), sign_symbol, font=f_small_sym,
                  fill=c["subtext"], anchor="mm")
        draw.text((W // 2, 325), title, font=f_title,
                  fill=c["text"], anchor="mm")
        planet_element = PLANETS[planet_name]["element"]
        draw_alchemy_symbol(draw, planet_element, W //
                            2 - 80, 365, 22, c["accent2"])
        draw.text((W // 2, 375), ELEMENT_NAMES[planet_element],
                  font=f_element, fill=c["accent2"], anchor="mm")
        draw.text((W // 2, 420), subtitle, font=f_subtitle,
                  fill=c["subtext"], anchor="mm")
        draw_alchemy_symbol(draw, sign["element"],
                            W // 2 - 80, 460, 22, c["accent2"])
        draw.text((W // 2, 470), ELEMENT_NAMES[sign["element"]],
                  font=f_element, fill=c["accent2"], anchor="mm")
        y_offset = 0
        if is_ruler:
            draw.rounded_rectangle(
                [170, 510, W - 170, 545], radius=8, fill=c["accent"])
            draw.text((W // 2, 527), "УПРАВИТЕЛЬ ЗНАКА",
                      font=f_element, fill=c["bg_top"], anchor="mm")
            y_offset = 30
        draw.text((W // 2, 555 + y_offset), f"«{PLANETS[planet_name]['motto']}»",
                  font=f_motto, fill=c["accent2"], anchor="mm")
        panel_top = 585 + y_offset
        draw.line([(60, panel_top - 15), (W - 60, panel_top - 15)],
                  fill=c["border"], width=1)

    draw.rounded_rectangle(
        [35, panel_top + 15, W - 35, H - 65], radius=12, fill=c["panel"])
    y = panel_top + 30
    for label, text, max_chars, max_lines in [("ЗНАЧЕНИЕ", meaning, 340, 3),
                                              ("СОВЕТ", advice, 220, 2),
                                              ("ПРЕДУПРЕЖДЕНИЕ", warning, 280, 2)]:
        draw.text((50, y), label, font=f_header, fill=c["accent"])
        y += 28
        for line in wrap_text(shorten_text(text, max_chars), f_body, W - 100, draw)[:max_lines]:
            draw.text((50, y), line, font=f_body, fill=c["text"])
            y += 24
        y += 6

    draw.line([(60, H - 55), (W - 60, H - 55)], fill=c["border"], width=1)
    draw.text((W // 2, H - 35), "ОРАКУЛ 12 ПЛАНЕТ",
              font=f_element, fill=c["subtext"], anchor="mm")
    return img


# ============================================================
# 6. ЭКСПОРТ deck.json
# ============================================================
def build_cards_meta():
    cards = []
    card_num = 0
    for sign in SIGNS:
        for planet in RULERS_ORDER:
            card_num += 1
            if card_num not in CARD_TEXTS:
                continue
            meaning, advice, warning = CARD_TEXTS[card_num]
            p = PLANETS[planet]
            cards.append({
                "id": f"oracle_{card_num:03d}",
                "name": f"{planet} {PREPOSITIONAL_PHRASE[sign['name']]}",
                "arcana": "oracle",
                "group": sign["name"],
                "number": card_num,
                "image": f"{card_num:03d}_{planet}_{sign['name']}.png",
                "astrology": (f"{planet} {p['symbol']} в {sign['name']} {sign['symbol']} · "
                              f"{sign['house']} · {sign['sphere']}"),
                "keywords": p["keywords"],
                "upright": meaning,
                "advice": advice,
                "warning": warning,
                "description": (f"Девиз: «{p['motto']}». Стихия планеты: "
                                f"{ELEMENT_NAMES[p['element']]}, стихия знака: "
                                f"{ELEMENT_NAMES[sign['element']]}."
                                + (" Управитель знака." if sign["ruler"] == planet else "")),
            })
    for num, etype, title in [(145, "sun", "Солнечное затмение"),
                              (146, "moon", "Лунное затмение")]:
        if num in CARD_TEXTS:
            meaning, advice, warning = CARD_TEXTS[num]
            cards.append({
                "id": f"oracle_{num:03d}", "name": title, "arcana": "oracle",
                "group": "Затмения", "number": num, "image": f"{num}_eclipse_{etype}.png",
                "astrology": "☉ Новолуние" if etype == "sun" else "☽ Полнолуние",
                "keywords": ["затмение", "перелом", "кризис", "перезагрузка"],
                "upright": meaning, "advice": advice, "warning": warning,
                "description": "Особая карта Оракула.",
            })
    return cards


def export_deck_json(cards_meta, force):
    json_path = DECK_DIR / "deck.json"
    if json_path.exists() and not force:
        print(
            f"⏭️ deck.json уже существует (пропущено). Используйте --force для перезаписи.")
        return
    deck = {
        "id": "author_deck_146",
        "name": "Оракул «12 Планет» (авторская колода)",
        "author": "Школа Астрологии «12 Планет»",
        "description": ("Авторская оракульная система: 12 планет в 12 знаках + Солнечное и Лунное затмения. "
                        "Каждая карта содержит Значение, Совет и Предупреждение."),
        "deck_type": "oracle",
        "cards": cards_meta,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2)
    print(f"✅ deck.json записан: {json_path} ({len(cards_meta)} карт)")


# ============================================================
# 7. ГЛАВНЫЙ ЦИКЛ ГЕНЕРАЦИИ
# ============================================================
def generate_all_cards(force=False):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📂 Папка изображений: {IMAGES_DIR}")

    card_num = 0
    for sign in SIGNS:
        for planet in RULERS_ORDER:
            card_num += 1
            if card_num not in CARD_TEXTS:
                print(f"⚠️ Пропуск карты №{card_num}: текст не найден")
                continue
            meaning, advice, warning = CARD_TEXTS[card_num]
            img = draw_oracle_card(
                planet, sign, card_num, meaning, advice, warning)
            img.save(IMAGES_DIR /
                     f"{card_num:03d}_{planet}_{sign['name']}.png")
    print(f"✓ Сгенерировано {card_num} карт знаков")

    for num, etype in [(145, "sun"), (146, "moon")]:
        if num in CARD_TEXTS:
            meaning, advice, warning = CARD_TEXTS[num]
            img = draw_oracle_card(None, None, num, meaning, advice, warning,
                                   is_eclipse=True, eclipse_type=etype)
            img.save(IMAGES_DIR / f"{num}_eclipse_{etype}.png")
            print(f"✓ {num}_eclipse_{etype}.png")

    export_deck_json(build_cards_meta(), force)
    print(f"\n🎉 Готово! Колода сохранена в: {DECK_DIR}")


if __name__ == "__main__":
    generate_all_cards(force="--force" in sys.argv)
