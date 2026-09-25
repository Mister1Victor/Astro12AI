#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оракульная система 12 планет — генератор карт
Создаёт 144 карты планет в знаках + 2 карты затмений
Размер карты: 600×900 px
"""

import os
import sys
import re
from PIL import Image, ImageDraw, ImageFont


# ═════════════════════════════════════════════════════════════════
# 1. НАСТРОЙКА ШРИФТОВ
# ═════════════════════════════════════════════════════════════════
def _find_font(candidates):
    """Возвращает первый существующий шрифт из списка кандидатов."""
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Не найден ни один подходящий шрифт")


if sys.platform.startswith('win'):
    FONT_TEXT = "C:/Windows/Fonts/arial.ttf"
    FONT_TEXT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
    FONT_TEXT_MEDIUM = "C:/Windows/Fonts/arial.ttf"
    FONT_SYMBOLS = "C:/Windows/Fonts/seguisym.ttf"
    FONT_SYMBOLS_BOLD = "C:/Windows/Fonts/seguisym.ttf"
else:
    FONT_TEXT = "/usr/share/fonts/truetype/noto/NotoSans-SemiCondensedLight.ttf"
    FONT_TEXT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-ExtraCondensedBold.ttf"
    FONT_TEXT_MEDIUM = "/usr/share/fonts/truetype/noto/NotoSans-SemiCondensedMedium.ttf"
    FONT_SYMBOLS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_SYMBOLS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

FONT_TEXT = _find_font([FONT_TEXT, "C:/Windows/Fonts/arial.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
FONT_TEXT_BOLD = _find_font([FONT_TEXT_BOLD, "C:/Windows/Fonts/arialbd.ttf",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
FONT_TEXT_MEDIUM = _find_font([FONT_TEXT_MEDIUM, "C:/Windows/Fonts/arial.ttf",
                              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
FONT_SYMBOLS = _find_font([FONT_SYMBOLS, "C:/Windows/Fonts/seguisym.ttf",
                          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
FONT_SYMBOLS_BOLD = _find_font([FONT_SYMBOLS_BOLD, "C:/Windows/Fonts/seguisym.ttf",
                               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])


# ═════════════════════════════════════════════════════════════════
# 2. ПАЛИТРА ЦВЕТОВ ПО СТИХИЯМ
# ═════════════════════════════════════════════════════════════════
PALETTE = {
    "огонь": {
        "bg_top": (45, 12, 8), "bg_bottom": (160, 50, 15),
        "accent": (255, 130, 50), "accent2": (255, 200, 120),
        "text": (255, 248, 240), "subtext": (230, 180, 140),
        "border": (220, 90, 30), "panel": (25, 8, 5),
    },
    "земля": {
        "bg_top": (12, 30, 10), "bg_bottom": (50, 90, 35),
        "accent": (140, 200, 80), "accent2": (200, 230, 150),
        "text": (245, 255, 235), "subtext": (190, 210, 160),
        "border": (100, 150, 50), "panel": (8, 20, 6),
    },
    "воздух": {
        "bg_top": (190, 215, 255),       # светло-синий верх
        "bg_bottom": (230, 240, 255),    # почти белый низ
        "accent": (40, 80, 160),         # тёмно-синий для заголовков
        # насыщенный синий для стихий и символов
        "accent2": (80, 130, 220),
        "text": (20, 30, 60),            # тёмно-синий основной текст
        # приглушённый синий для номера и подписей
        "subtext": (70, 100, 170),
        "border": (100, 150, 230),       # светло-синяя рамка
        "panel": (240, 245, 255),        # очень светлая панель
    },

    "вода": {
        "bg_top": (8, 12, 35), "bg_bottom": (30, 50, 100),
        "accent": (100, 150, 255), "accent2": (160, 190, 255),
        "text": (230, 235, 255), "subtext": (160, 180, 230),
        "border": (70, 110, 200), "panel": (6, 10, 25),
    }
}

ECLIPSE_PALETTE = {
    "bg_top": (3, 3, 3), "bg_bottom": (35, 25, 15),
    "accent": (255, 190, 60), "accent2": (255, 230, 150),
    "text": (255, 250, 240), "subtext": (210, 180, 130),
    "border": (180, 140, 50), "panel": (15, 12, 8),
}


# ═════════════════════════════════════════════════════════════════
# 3. ДАННЫЕ СИСТЕМЫ
# ═════════════════════════════════════════════════════════════════
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
    "Меркурий": {"symbol": "☿", "element": "воздух", "motto": "Я узнаю и общаюсь",
                 "keywords": ["общение", "мышление", "учёба", "информация", "передвижение"]},
    "Луна": {"symbol": "☽", "element": "вода", "motto": "Я чувствую и забочусь",
             "keywords": ["эмоции", "интуиция", "семья", "забота", "привычки"]},
    "Солнце": {"symbol": "☉", "element": "огонь", "motto": "Привет холмики, Я - гора!",
               "keywords": ["личность", "лидерство", "власть", "харизма", "жизненная сила"]},
    "Эрида": {"symbol": "ERa", "element": "земля",
              "motto": "Я исправляю / исцеляю и довожу до совершенства",
              "keywords": ["здоровье", "ремонтировать", "лечить болезни", "ремонт", "работа"]},
    "Плутон": {"symbol": "♇", "element": "воздух", "motto": "Я с тобой — или против тебя",
               "keywords": ["партнёрство", "переговоры", "союз", "взаимодействие", "конфликт"]},
    "Нептун": {"symbol": "♆", "element": "вода", "motto": "Я хочу и потребляю",
               "keywords": ["желание", "финансы", "прибыль", "потребление", "страсть"]},
    "Уран": {"symbol": "♅", "element": "огонь", "motto": "Я знаю и объясняю",
             "keywords": ["знания", "путешествия", "неожиданность", "скорость", "открытия"]},
    "Сатурн": {"symbol": "♄", "element": "земля", "motto": "Я работаю и контролирую",
               "keywords": ["дисциплина", "карьера", "ответственность", "порядок", "время"]},
    "Юпитер": {"symbol": "♃", "element": "воздух", "motto": "Я вижу людей и вдохновляю",
               "keywords": ["люди", "дружба", "общество", "наблюдение", "вдохновение"]},
    "Церера": {"symbol": "⚳", "element": "вода", "motto": "Я верю и помогаю",
               "keywords": ["помощь", "сострадание", "вера", "жертвенность", "мечта"]},
}

RULERS_ORDER = ["Марс", "Венера", "Меркурий", "Луна", "Солнце",
                "Эрида", "Плутон", "Нептун", "Уран", "Сатурн", "Юпитер", "Церера"]

PREPOSITIONAL_PHRASE = {
    "Овен": "в Овне", "Телец": "в Тельце", "Близнецы": "в Близнецах",
    "Рак": "в Раке", "Лев": "во Льве", "Дева": "в Деве",
    "Весы": "в Весах", "Скорпион": "в Скорпионе", "Стрелец": "в Стрельце",
    "Козерог": "в Козероге", "Водолей": "в Водолее", "Рыбы": "в Рыбах"
}

ELEMENT_NAMES = {
    "огонь": "Огонь",
    "земля": "Земля",
    "воздух": "Воздух",
    "вода": "Вода"
}


# ═════════════════════════════════════════════════════════════════
# 4. УТИЛИТЫ РИСОВАНИЯ
# ═════════════════════════════════════════════════════════════════
def draw_gradient(draw, width, height, color_top, color_bottom):
    for y in range(height):
        ratio = y / height
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""
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
        p1 = (center_x, y_top)
        p2 = (center_x - half, y_top + size)
        p3 = (center_x + half, y_top + size)
        draw.polygon([p1, p2, p3], outline=color, width=2)
        if element == "воздух":
            y_line = y_top + size * 0.6
            draw.line([(center_x - half, y_line), (center_x + half, y_line)],
                      fill=color, width=2)
    elif element in ("земля", "вода"):
        p1 = (center_x, y_top + size)
        p2 = (center_x - half, y_top)
        p3 = (center_x + half, y_top)
        draw.polygon([p1, p2, p3], outline=color, width=2)
        if element == "земля":
            y_line = y_top + size * 0.4
            draw.line([(center_x - half, y_line), (center_x + half, y_line)],
                      fill=color, width=2)


# ═════════════════════════════════════════════════════════════════
# 5. ЗАГРУЗКА ТЕКСТОВ КАРТ ИЗ ФАЙЛА
# ═════════════════════════════════════════════════════════════════
def load_card_texts(filename="core/tarot/card_data.txt"):
    """Читает файл с описаниями карт и возвращает словарь {номер: (значение, совет, предупреждение)}."""
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Файл {filename} не найден. Создайте его и вставьте тексты карт.")
    with open(filename, encoding="utf-8") as f:
        raw = f.read()
    return parse_card_texts(raw)


def parse_card_texts(raw_text):
    card_texts = {}
    pattern = (r'\*\*Карта №(\d+):.*?\*\*Значение:\*\*\s*(.*?)\s*'
               r'\*\*Совет:\*\*\s*(.*?)\s*'
               r'\*\*Предупреждение:\*\*\s*(.*?)(?=\*\*Карта №|\Z)')
    for match in re.finditer(pattern, raw_text, re.DOTALL):
        num = int(match.group(1))
        meaning = match.group(2).strip()
        advice = match.group(3).strip()
        warning = match.group(4).strip()
        card_texts[num] = (meaning, advice, warning)
    return card_texts


# ═════════════════════════════════════════════════════════════════
# 6. РИСОВАЛЬЩИК КАРТ
# ═════════════════════════════════════════════════════════════════
def draw_oracle_card(planet_name, sign, card_num, meaning, advice, warning,
                     is_eclipse=False, eclipse_type=None):
    W, H = 600, 900
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    if is_eclipse:
        c = ECLIPSE_PALETTE
        title = "СОЛНЕЧНОЕ ЗАТМЕНИЕ" if eclipse_type == "sun" else "ЛУННОЕ ЗАТМЕНИЕ"
        subtitle = "Новолуние" if eclipse_type == "sun" else "Полнолуние"
        planet_symbol = "☉" if eclipse_type == "sun" else "☽"
        sign_symbol = "●" if eclipse_type == "sun" else "○"
        element_name = "Затмение"
        is_ruler = False
    else:
        c = PALETTE[sign["element"]]
        p = PLANETS[planet_name]
        title = planet_name
        subtitle = PREPOSITIONAL_PHRASE[sign["name"]]
        planet_symbol = p["symbol"]
        sign_symbol = sign["symbol"]
        element_name = ELEMENT_NAMES[sign["element"]]
        is_ruler = sign["ruler"] == planet_name

    draw_gradient(draw, W, H, c["bg_top"], c["bg_bottom"])

    margin = 18
    draw.rounded_rectangle([margin, margin, W - margin, H - margin],
                           radius=16, outline=c["border"], width=2)
    draw.rounded_rectangle([margin + 6, margin + 6, W - margin - 6, H - margin - 6],
                           radius=13, outline=c["accent"], width=1)

    f_num = ImageFont.truetype(FONT_TEXT_BOLD, 56)
    f_title = ImageFont.truetype(FONT_TEXT_BOLD, 42)
    f_subtitle = ImageFont.truetype(FONT_TEXT_MEDIUM, 26)
    f_header = ImageFont.truetype(FONT_TEXT_BOLD, 20)
    f_body = ImageFont.truetype(FONT_TEXT, 16)
    f_symbol = ImageFont.truetype(FONT_SYMBOLS, 90)
    f_small_sym = ImageFont.truetype(FONT_SYMBOLS, 60)
    f_motto = ImageFont.truetype(FONT_TEXT_MEDIUM, 20)
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

        draw.rounded_rectangle([40, 520, W - 40, H - 65],
                               radius=12, fill=c["panel"])
        y = 540
        draw.text((55, y), "ЗНАЧЕНИЕ", font=f_header, fill=c["accent"])
        lines = wrap_text(shorten_text(meaning, 320), f_body, W - 110, draw)
        y += 28
        for line in lines[:5]:
            draw.text((55, y), line, font=f_body, fill=c["text"])
            y += 22

        y += 8
        draw.text((55, y), "СОВЕТ", font=f_header, fill=c["accent"])
        lines = wrap_text(shorten_text(advice, 200), f_body, W - 110, draw)
        y += 28
        for line in lines[:3]:
            draw.text((55, y), line, font=f_body, fill=c["text"])
            y += 22

        y += 8
        draw.text((55, y), "ПРЕДУПРЕЖДЕНИЕ", font=f_header, fill=c["accent"])
        lines = wrap_text(shorten_text(warning, 250), f_body, W - 110, draw)
        y += 28
        for line in lines[:3]:
            draw.text((55, y), line, font=f_body, fill=c["text"])
            y += 22
    else:
        draw.text((W // 2, 150), planet_symbol, font=f_symbol,
                  fill=c["accent"], anchor="mm")
        draw.text((W // 2, 235), sign_symbol, font=f_small_sym,
                  fill=c["subtext"], anchor="mm")
        draw.text((W // 2, 325), title, font=f_title,
                  fill=c["text"], anchor="mm")

        planet_element = PLANETS[planet_name]["element"]
        planet_element_name = ELEMENT_NAMES[planet_element]
        symbol_size = 22
        symbol_x = W // 2 - 80
        symbol_y = 365
        draw_alchemy_symbol(draw, planet_element, symbol_x, symbol_y,
                            symbol_size, c["accent2"])
        draw.text((W // 2, 375), planet_element_name, font=f_element,
                  fill=c["accent2"], anchor="mm")

        draw.text((W // 2, 420), subtitle, font=f_subtitle,
                  fill=c["subtext"], anchor="mm")

        sign_element = sign["element"]
        sign_element_name = ELEMENT_NAMES[sign_element]
        symbol_size = 22
        symbol_x = W // 2 - 80
        symbol_y = 460
        draw_alchemy_symbol(draw, sign_element, symbol_x, symbol_y,
                            symbol_size, c["accent2"])
        draw.text((W // 2, 470), sign_element_name, font=f_element,
                  fill=c["accent2"], anchor="mm")

        y_offset = 0
        if is_ruler:
            draw.rounded_rectangle(
                [170, 510, W - 170, 545], radius=8, fill=c["accent"])
            draw.text((W // 2, 527), "УПРАВИТЕЛЬ ЗНАКА",
                      font=f_element, fill=c["bg_top"], anchor="mm")
            y_offset = 30

        motto = PLANETS[planet_name]["motto"]
        draw.text((W // 2, 555 + y_offset),
                  f"«{motto}»", font=f_motto, fill=c["accent2"], anchor="mm")

        y_line = 565 + y_offset
        draw.line([(60, y_line), (W - 60, y_line)], fill=c["border"], width=1)
        draw.rounded_rectangle(
            [35, y_line + 15, W - 35, H - 55], radius=12, fill=c["panel"])

        y = y_line + 28
        draw.text((50, y), "ЗНАЧЕНИЕ", font=f_header, fill=c["accent"])
        lines = wrap_text(shorten_text(meaning, 340), f_body, W - 100, draw)
        y += 28
        for line in lines[:5]:
            draw.text((50, y), line, font=f_body, fill=c["text"])
            y += 20

        y += 6
        draw.text((50, y), "СОВЕТ", font=f_header, fill=c["accent"])
        lines = wrap_text(shorten_text(advice, 220), f_body, W - 100, draw)
        y += 28
        for line in lines[:3]:
            draw.text((50, y), line, font=f_body, fill=c["text"])
            y += 22

        y += 6
        draw.text((50, y), "ПРЕДУПРЕЖДЕНИЕ", font=f_header, fill=c["accent"])
        lines = wrap_text(shorten_text(warning, 280), f_body, W - 100, draw)
        y += 28
        for line in lines[:3]:
            draw.text((50, y), line, font=f_body, fill=c["text"])
            y += 22

    draw.line([(60, H - 55), (W - 60, H - 55)], fill=c["border"], width=1)
    draw.text((W // 2, H - 35), "ОРАКУЛ 12 ПЛАНЕТ",
              font=f_element, fill=c["subtext"], anchor="mm")

    return img


# ═════════════════════════════════════════════════════════════════
# 7. ГЛАВНЫЙ ЦИКЛ ГЕНЕРАЦИИ
# ═════════════════════════════════════════════════════════════════
def generate_all_cards(output_dir="oracle_cards"):
    os.makedirs(output_dir, exist_ok=True)
    card_texts = load_card_texts()   # загрузка из файла

    card_num = 0
    for sign in SIGNS:
        # Порядок планет одинаков для всех знаков
        for planet in RULERS_ORDER:
            card_num += 1
            if card_num not in card_texts:
                print(f"Пропущена карта №{card_num}: нет текста")
                continue
            meaning, advice, warning = card_texts[card_num]
            img = draw_oracle_card(
                planet, sign, card_num, meaning, advice, warning)
            fname = f"{card_num:03d}_{planet}_{sign['name']}.png"
            img.save(os.path.join(output_dir, fname))
            print(f"✓ {fname}")

    # Затмения
    for num, etype, fname in [(145, "sun", "145_eclipse_sun.png"),
                              (146, "moon", "146_eclipse_moon.png")]:
        if num in card_texts:
            meaning, advice, warning = card_texts[num]
            img = draw_oracle_card(None, None, num, meaning, advice, warning,
                                   is_eclipse=True, eclipse_type=etype)
            img.save(os.path.join(output_dir, fname))
            print(f"✓ {fname}")
        else:
            print(f"Нет текста для карты {num}")

    print(f"\nГотово! Карты сохранены в: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    generate_all_cards("oracle_cards")
