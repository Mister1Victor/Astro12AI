#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
АСТРОЛОГИЧЕСКАЯ КАРТА ТАРО
Старшие Арканы Уэйта, знаки зодиака и планеты-управители.
Поддержка реальных изображений карт (PNG).
Символы планет на картах с полупрозрачным фоном.
Стрелки внешнего круга сдвинуты на 15° по часовой стрелке.
Подписи карт вынесены вниз под изображение, белые с тёмным фоном.
"""

from matplotlib.patches import Wedge, Circle, FancyBboxPatch, Arc
import matplotlib.pyplot as plt
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')


# ============================================================================
#  НАСТРОЙКИ
# ============================================================================
CONFIG = {
    'USE_IMAGES': True,
    'SCALE': 1.0,
    'ZODIAC_SCALE': 1.2,
    'ZODIAC_WIDTH': 0.85,
    'ZODIAC_LINE_START_RADIUS': 0.35,
    'CARD_W_OUTER': 0.20,
    'CARD_H_OUTER': 0.30,
    'CARD_W_INNER': 0.20,
    'CARD_H_INNER': 0.30,
    'R_ZODIAC': 1.0,
    'R_ZODIAC_LABEL': 0.92,
    'R_HOUSE': 1.025,
    'HOUSE_CIRCLE_R': 0.038,
    'RING_RADII': [1.2, 0.99, 0.60, 0.36, 0.35],
    'RING_LW': [4.0, 3.0, 1.5, 2.5, 5.0],
    'RING_ALPHA': [0.9, 0.7, 0.5, 0.5, 0.7],
    'OUTER_RAD_CARD': 0.9,
    'OUTER_ARROW_R': 1.02,
    'OUTER_ARROW_SPAN': 5,
    'INNER_RAD_CARD': 0.60,
    'INNER_ARROW_R': 0.36,
    'INNER_ARROW_SPAN': 5,
    'GLOBAL_INNER_RADIUS': 0.28,
    'ROTATE_OUTER': -23.9,
    'ROTATE_INNER': -12,
    'OUTER_ORDER': True,
    'INNER_ORDER': False,
    'COLORS': {
        'FIRE': '#E74C3C',
        'EARTH': '#27AE60',
        'AIR': '#F39C12',
        'WATER': '#3498DB',
        'DARK': '#2C3E50',
        'CREAM': '#FDFDFD',
        'BORDER': '#C9A227',
        'ASC': '#C0392B',
    },
    'FONTSIZE': {
        'ZODIAC_SYMBOL': 24,
        'ZODIAC_NAME': 18,
        'PLANET_SYMBOL': 24,
        'HOUSE_NUM': 20,
        'CARD_NUM': 14,
        'CARD_SYMBOL': 28,
        'CARD_PLANET': 30,
        'CARD_NAME': 12,
        'EXTRA': 16,
        'LEGEND': 13,
        'LEGEND_SMALL': 11,
    },
    'PLANET_BBOX': {
        'boxstyle': 'round,pad=0.15',
        'facecolor': 'black',
        'alpha': 0.5,
    },
    'LABEL_BBOX': {                      # ← новый параметр для подписи
        'boxstyle': 'round,pad=0.15',
        'facecolor': 'black',
        'alpha': 0.5,
    },
    'CARD_LABEL_OFFSET': 0.00,
}

# ============================================================================
#  ЗАГРУЗКА ИЗОБРАЖЕНИЙ
# ============================================================================
image_cache = {}
image_dir = os.path.join(os.path.dirname(__file__), 'images')

if CONFIG['USE_IMAGES'] and os.path.exists(image_dir):
    card_names = {
        '0': '00_durak',
        'I': '01_mag',
        'II': '02_high_priestess',
        'III': '03_empress',
        'IV': '04_emperor',
        'V': '05_hierophant',
        'VI': '06_lovers',
        'VII': '07_chariot',
        'VIII': '08_strength',
        'IX': '09_hermit',
        'X': '10_wheel',
        'XI': '11_justice',
        'XII': '12_hanged_man',
        'XIII': '13_death',
        'XIV': '14_temperance',
        'XV': '15_devil',
        'XVI': '16_tower',
        'XVII': '17_star',
        'XVIII': '18_moon',
        'XIX': '19_sun',
        'XX': '20_judgement',
        'XXI': '21_world'
    }
    for num, fname in card_names.items():
        img_path = os.path.join(image_dir, f'{fname}.png')
        if os.path.exists(img_path):
            try:
                image_cache[num] = plt.imread(img_path)
            except Exception as e:
                print(f"Не удалось загрузить {img_path}: {e}")
        else:
            print(f"Файл {img_path} не найден.")


# ----------------------------------------------------------------------------
#  Вспомогательные функции
# ----------------------------------------------------------------------------

def draw_card(ax, cx, cy, w, h, num, name, color, symbol='', planet_sym='', extra=''):
    fs = CONFIG['FONTSIZE']
    bbox_planet = CONFIG['PLANET_BBOX']
    bbox_label = CONFIG['LABEL_BBOX']
    label_offset = CONFIG['CARD_LABEL_OFFSET'] * CONFIG['SCALE']

    if CONFIG['USE_IMAGES'] and num in image_cache:
        img = image_cache[num]
        left, right = cx - w/2, cx + w/2
        bottom, top = cy - h/2, cy + h/2
        ax.imshow(img, extent=(left, right, bottom, top),
                  aspect='auto', zorder=7)

        # Номер карты (римская цифра)
        ax.text(cx, top - 0.015, num, ha='center', va='top',
                fontsize=fs['CARD_NUM'], color='white', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2",
                          facecolor='black', alpha=0.6),
                zorder=8)

        # Символ планеты с полупрозрачным фоном
        if planet_sym:
            ax.text(cx, bottom + 0.015, planet_sym, ha='center', va='bottom',
                    fontsize=fs['CARD_PLANET'], color='white', fontweight='bold',
                    bbox=bbox_planet, zorder=9)

        # ---- ПОДПИСЬ КАРТЫ (белая с тёмным фоном) ----
        label_y = bottom - label_offset
        ax.text(cx, label_y, name, ha='center', va='top',
                fontsize=fs['CARD_NAME'], color='white', fontweight='bold',
                bbox=bbox_label, zorder=9)

        # Дополнительный текст (разворот) – тоже белый с фоном
        if extra:
            extra_y = label_y - 0.02 * CONFIG['SCALE']
            ax.text(cx, extra_y, extra, ha='center', va='top',
                    fontsize=fs['EXTRA'], color='white', fontweight='bold',
                    bbox=bbox_label, zorder=9)
        return

    # Текстовый режим (fallback)
    rect = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                          boxstyle="round,pad=0.005",
                          facecolor='white', edgecolor=color,
                          linewidth=2.5, zorder=7)
    ax.add_patch(rect)
    inner = FancyBboxPatch((cx - w/2 + 0.008, cy - h/2 + 0.008),
                           w - 0.016, h - 0.016,
                           boxstyle="round,pad=0.003",
                           fill=False, edgecolor=color,
                           linewidth=0.8, alpha=0.4, zorder=8)
    ax.add_patch(inner)

    ax.text(cx, cy + h/2 - 0.020, num, ha='center', va='top',
            fontsize=fs['CARD_NUM'], color=color, fontweight='bold', zorder=9)
    if symbol:
        ax.text(cx, cy + 0.02, symbol, ha='center', va='center',
                fontsize=fs['CARD_SYMBOL'], color=color, zorder=9)
    if planet_sym:
        ax.text(cx, cy - 0.025, planet_sym, ha='center', va='center',
                fontsize=fs['CARD_PLANET'], color=CONFIG['COLORS']['DARK'],
                alpha=0.8, fontweight='bold', zorder=9)
    ax.text(cx, cy - h/2 + 0.022, name, ha='center', va='bottom',
            fontsize=fs['CARD_NAME'], color=CONFIG['COLORS']['DARK'],
            fontweight='bold', zorder=9)
    if extra:
        ax.text(cx, cy - h/2 - 0.015, extra, ha='center', va='top',
                fontsize=fs['EXTRA'], color=CONFIG['COLORS']['BORDER'],
                fontweight='bold', zorder=9)


def draw_arc_arrow(ax, angle_deg, radius, direction, color, span=5, **kwargs):
    theta1 = angle_deg - span
    theta2 = angle_deg + span
    if direction == 'cw':
        start, end = theta2, theta1
        arrow_off = span * 0.4
    else:
        start, end = theta1, theta2
        arrow_off = -span * 0.4

    arc = Arc((0, 0), 2*radius, 2*radius, angle=0,
              theta1=start, theta2=end,
              color=color, linewidth=kwargs.get('lw', 2),
              linestyle=kwargs.get('linestyle', '--'))
    ax.add_patch(arc)

    x_end = radius * np.cos(np.radians(end))
    y_end = radius * np.sin(np.radians(end))
    x_start = radius * np.cos(np.radians(end + arrow_off))
    y_start = radius * np.sin(np.radians(end + arrow_off))

    ax.annotate('', xy=(x_end, y_end), xytext=(x_start, y_start),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=kwargs.get('lw', 2)))


def get_zodiac_index(angle):
    a = angle % 360
    if a < 0:
        a += 360
    if a < 180:
        a += 360
    for i in range(12):
        start = 180 + i * 30
        end = 180 + (i + 1) * 30
        if start <= a < end:
            return i
    return 0


# ----------------------------------------------------------------------------
#  Основная программа
# ----------------------------------------------------------------------------

def main():
    cfg = CONFIG
    scale = cfg['SCALE']
    z_scale = cfg['ZODIAC_SCALE']
    z_width = cfg['ZODIAC_WIDTH']
    line_start = cfg['ZODIAC_LINE_START_RADIUS']
    colors = cfg['COLORS']
    fs = cfg['FONTSIZE']

    fig, ax = plt.subplots(figsize=(24, 24), facecolor=colors['CREAM'])
    ax.set_facecolor(colors['CREAM'])
    lim = 1.5 * scale
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect('equal')
    ax.axis('off')

    signs = [
        ('Овен', '♈', colors['FIRE'], 1),
        ('Телец', '♉', colors['EARTH'], 2),
        ('Близнецы', '♊', colors['AIR'], 3),
        ('Рак', '♋', colors['WATER'], 4),
        ('Лев', '♌', colors['FIRE'], 5),
        ('Дева', '♍', colors['EARTH'], 6),
        ('Весы', '♎', colors['AIR'], 7),
        ('Скорпион', '♏', colors['WATER'], 8),
        ('Стрелец', '♐', colors['FIRE'], 9),
        ('Козерог', '♑', colors['EARTH'], 10),
        ('Водолей', '♒', colors['AIR'], 11),
        ('Рыбы', '♓', colors['WATER'], 12),
    ]

    planet_symbols = [
        '♂', '♀', '☿', '☽', '☉', 'ER', '♇', '♆', '♅', '♄', '♃', '⚳'  # \u2BF0 '⚸'
    ]

    r_z = cfg['R_ZODIAC'] * z_scale * scale
    r_label = cfg['R_ZODIAC_LABEL'] * z_scale * scale
    r_house = cfg['R_HOUSE'] * z_scale * scale
    house_circ_r = cfg['HOUSE_CIRCLE_R'] * scale

    for i, (name, sym, color, house_num) in enumerate(signs):
        t1 = 180 + i * 30
        t2 = 180 + (i + 1) * 30
        wedge = Wedge((0, 0), r_z, t1, t2,
                      width=z_width * scale,
                      facecolor=color, edgecolor=colors['BORDER'],
                      linewidth=2, alpha=0.15)
        ax.add_patch(wedge)

        mid_deg = (t1 + t2) / 2
        mid_rad = np.radians(mid_deg)
        x = r_label * np.cos(mid_rad)
        y = r_label * np.sin(mid_rad)

        ax.text(x, y, f'{sym}\n{name}', ha='center', va='center',
                fontsize=fs['ZODIAC_SYMBOL'], color=colors['DARK'],
                fontweight='bold')

        y_planet = y - 0.055 * scale
        ax.text(x, y_planet, planet_symbols[i], ha='center', va='top',
                fontsize=fs['PLANET_SYMBOL'], color='black',
                alpha=0.9, fontweight='bold')

        xh = r_house * np.cos(mid_rad)
        yh = r_house * np.sin(mid_rad)
        circle_bg = Circle((xh, yh), house_circ_r,
                           facecolor='white', edgecolor=colors['BORDER'],
                           linewidth=1.5, zorder=5)
        ax.add_patch(circle_bg)
        ax.text(xh, yh, str(house_num), ha='center', va='center',
                fontsize=fs['HOUSE_NUM'], color=colors['BORDER'],
                fontweight='bold', zorder=6)

    start_r = line_start * scale
    for i in range(12):
        t = 180 + i * 30
        rad = np.radians(t)
        ax.plot([start_r * np.cos(rad), r_z * np.cos(rad)],
                [start_r * np.sin(rad), r_z * np.sin(rad)],
                color=colors['BORDER'], linewidth=1.2, alpha=0.5)

    ax.plot([-1.10 * scale, -0.999 * scale], [0, 0],
            color=colors['ASC'], linewidth=5, zorder=10)
    ax.text(-1.15 * scale, 0, 'ASC', ha='center', va='center',
            fontsize=22, color=colors['ASC'], fontweight='bold', zorder=10)

    r_inner_global = cfg['GLOBAL_INNER_RADIUS'] * scale
    theta_arc = np.radians(np.linspace(165, 15, 100))
    x_arc = r_inner_global * np.cos(theta_arc)
    y_arc = r_inner_global * np.sin(theta_arc)
    ax.plot(x_arc, y_arc, color=colors['BORDER'], linewidth=2,
            linestyle='--', zorder=5)
    x_end = r_inner_global * np.cos(np.radians(15))
    y_end = r_inner_global * np.sin(np.radians(15))
    x_start = r_inner_global * np.cos(np.radians(20))
    y_start = r_inner_global * np.sin(np.radians(20))
    ax.annotate('', xy=(x_end, y_end), xytext=(x_start, y_start),
                arrowprops=dict(arrowstyle='->', color=colors['BORDER'], lw=2))

    boundaries_outer = [210, 240, 270, 300, 330, 0, 30, 60, 90, 120, 150, 180]
    boundaries_inner = boundaries_outer[:-1]

    # *** Перестановки: VII↔VIII, XI↔XII, XVIII↔XIX ***
    arcana_outer = [
        ('0', 'ДУРАК', '✿'),
        ('I', 'МАГ', '∞'),
        ('II', 'ЖРИЦА', '☽'),
        ('III', 'ИМПЕРАТРИЦА', '♀'),
        ('IV', 'ИМПЕРАТОР', '♔'),
        ('V', 'ИЕРОФАНТ', '✚'),
        ('VI', 'ВЛЮБЛЁННЫЕ', '♥'),
        ('VIII', 'СИЛА', '♌'),     # ('VII', 'КОЛЕСНИЦА', '⏣'),
        ('VII', 'КОЛЕСНИЦА', '⏣'),          # ('VIII', 'СИЛА', '♌'),
        ('IX', 'ОТШЕЛЬНИК', '▼'),
        ('X', 'КОЛЕСО ФОРТУНЫ', '☸'),
        ('XII', 'ПОВЕШЕННЫЙ', '♣'),   # ('XI', 'СПРАВЕДЛИВОСТЬ', '⚖'),
    ]

    arcana_inner = [
        # ('XII', 'ПОВЕШЕННЫЙ', '♣'),
        ('XI', 'СПРАВЕДЛИВОСТЬ', '⚖'),
        ('XIII', 'СМЕРТЬ', '☠'),
        ('XIV', 'УМЕРЕННОСТЬ', '⚱'),
        ('XV', 'ДЬЯВОЛ', '♦'),
        ('XVI', 'БАШНЯ', '⌁'),
        ('XVII', 'ЗВЕЗДА', '★'),
        ('XIX', 'СОЛНЦЕ', '☉'),           # ('XVIII', 'ЛУНА', '●'),
        ('XVIII', 'ЛУНА', '●'),           # ('XIX', 'СОЛНЦЕ', '☉'),
        ('XX', 'СУД', '♪'),
        ('XXI', 'МИР', '◉'),
    ]

    # Внешний круг
    outer_order = cfg['OUTER_ORDER']
    rotate_outer = cfg['ROTATE_OUTER']
    r_card_outer = cfg['OUTER_RAD_CARD'] * scale
    r_arrow_outer = cfg['OUTER_ARROW_R'] * scale
    span_outer = cfg['OUTER_ARROW_SPAN']
    card_w_outer = cfg['CARD_W_OUTER'] * scale
    card_h_outer = cfg['CARD_H_OUTER'] * scale

    for i, (num, name, sym) in enumerate(arcana_outer):
        if outer_order:
            idx = i
        else:
            idx = len(boundaries_outer) - 1 - i
        angle = (boundaries_outer[idx] + rotate_outer) % 360

        zi = get_zodiac_index(angle)
        planet = planet_symbols[zi]
        color = signs[zi][2]

        mid_rad = np.radians(angle)
        cx = r_card_outer * np.cos(mid_rad)
        cy = r_card_outer * np.sin(mid_rad)
        extra = '↻' if name == 'ПОВЕШЕННЫЙ' else ''
        draw_card(ax, cx, cy, card_w_outer, card_h_outer, num, name,
                  color, sym, planet, extra)

        arrow_angle = (angle - 15) % 360
        draw_arc_arrow(ax, arrow_angle, r_arrow_outer, 'ccw',
                       colors['BORDER'], span=span_outer, lw=2, linestyle='--')

    # Внутренний круг
    inner_order = cfg['INNER_ORDER']
    rotate_inner = cfg['ROTATE_INNER']
    r_card_inner = cfg['INNER_RAD_CARD'] * scale
    r_arrow_inner = cfg['INNER_ARROW_R'] * scale
    span_inner = cfg['INNER_ARROW_SPAN']
    card_w_inner = cfg['CARD_W_INNER'] * scale
    card_h_inner = cfg['CARD_H_INNER'] * scale

    for i, (num, name, sym) in enumerate(arcana_inner):
        if inner_order:
            idx = i
        else:
            idx = len(boundaries_inner) - 1 - i
        angle = (boundaries_inner[idx] + rotate_inner) % 360

        zi = get_zodiac_index(angle)
        planet = planet_symbols[zi]
        color = signs[zi][2]

        mid_rad = np.radians(angle)
        cx = r_card_inner * np.cos(mid_rad)
        cy = r_card_inner * np.sin(mid_rad)
        extra = '↻' if name == 'ПОВЕШЕННЫЙ' else ''
        draw_card(ax, cx, cy, card_w_inner, card_h_inner, num, name,
                  color, sym, planet, extra)

        draw_arc_arrow(ax, angle, r_arrow_inner, 'cw',
                       colors['BORDER'], span=span_inner, lw=2, linestyle='--')

    # Кольца
    for r, lw, alpha in zip(cfg['RING_RADII'], cfg['RING_LW'], cfg['RING_ALPHA']):
        circle = Circle((0, 0), r * scale, fill=False,
                        color=colors['BORDER'],
                        linewidth=lw, alpha=alpha)
        ax.add_patch(circle)

    # Центральный круг
    center_bg = Circle((0, 0), 0.20 * scale, facecolor='white',
                       edgecolor=colors['BORDER'], linewidth=2)
    ax.add_patch(center_bg)
    ax.text(0, 0.02 * scale, '✧', ha='center', va='center',
            fontsize=32, color=colors['BORDER'])
    ax.text(0, -0.06 * scale, 'TAROT', ha='center', va='center',
            fontsize=10, color=colors['BORDER'], alpha=0.7)

    # Легенда
    leg_x = 0.88 * scale
    leg_y = -1.08 * scale
    ax.text(leg_x, leg_y, 'Перестановки:',
            ha='left', va='center', fontsize=fs['LEGEND_SMALL'],
            color=colors['DARK'], fontweight='bold')
    ax.text(leg_x, leg_y - 0.06 * scale, 'VII↔VIII, XI↔XII, XVIII↔XIX',
            ha='left', va='center', fontsize=fs['LEGEND_SMALL'],
            color=colors['DARK'], alpha=0.8)

    # Сохранение
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(script_dir, 'output')
    os.makedirs(out_dir, exist_ok=True)
    save_path = os.path.join(out_dir, 'astrology_tarot_final.png')

    plt.tight_layout(pad=0.5)
    plt.savefig(save_path, dpi=300, bbox_inches='tight',
                facecolor=colors['CREAM'], edgecolor='none')
    print(f"Сохранено в {save_path}")
    if CONFIG['USE_IMAGES']:
        print(
            f"Использовано изображений: {len(image_cache)} из {len(card_names)}")
    else:
        print("Режим изображений выключен (USE_IMAGES=False)")


if __name__ == '__main__':
    main()
