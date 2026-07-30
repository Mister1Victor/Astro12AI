import numpy as np
from matplotlib.patches import Wedge, Circle, FancyBboxPatch
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import os
import matplotlib
matplotlib.use('Agg')   # отключаем GUI, чтобы избежать ошибок Tcl/Tk


# Создаём папку для сохранения рядом со скриптом
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'output')
os.makedirs(output_dir, exist_ok=True)
save_path = os.path.join(output_dir, 'astrology_tarot_light_v4.png')

fig, ax = plt.subplots(figsize=(20, 20), facecolor='#FAF8F3')
ax.set_facecolor('#FAF8F3')
ax.set_xlim(-1.4, 1.4)
ax.set_ylim(-1.4, 1.4)
ax.set_aspect('equal')
ax.axis('off')

# ===== ЦВЕТА =====
FIRE = '#E74C3C'
EARTH = '#27AE60'
AIR = '#F39C12'
WATER = '#3498DB'
GOLD = '#B8860B'
DARK = '#2C3E50'
CREAM = '#FAF8F3'
BORDER = '#C9A227'


def draw_card(ax, cx, cy, w, h, num, name, color, symbol=''):
    """Рисует карту Таро как прямоугольник с рамками и текстом"""
    rect = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                          boxstyle="round,pad=0.005",
                          facecolor='white', edgecolor=color, linewidth=2.5, zorder=7)
    ax.add_patch(rect)
    inner = FancyBboxPatch((cx - w/2 + 0.008, cy - h/2 + 0.008), w - 0.016, h - 0.016,
                           boxstyle="round,pad=0.003",
                           fill=False, edgecolor=color, linewidth=0.8, alpha=0.4, zorder=8)
    ax.add_patch(inner)

    ax.text(cx, cy + h/2 - 0.018, num, ha='center', va='top',
            fontsize=8, color=color, fontweight='bold', zorder=9)

    if symbol:
        ax.text(cx, cy + 0.01, symbol, ha='center', va='center',
                fontsize=20, color=color, zorder=9)

    ax.text(cx, cy - h/2 + 0.018, name, ha='center', va='bottom',
            fontsize=6.5, color=DARK, fontweight='bold', zorder=9)


# ===== ЗНАКИ ЗОДИАКА =====
signs = [
    ('Овен', '♈', FIRE, 1),
    ('Телец', '♉', EARTH, 2),
    ('Близнецы', '♊', AIR, 3),
    ('Рак', '♋', WATER, 4),
    ('Лев', '♌', FIRE, 5),
    ('Дева', '♍', EARTH, 6),
    ('Весы', '♎', AIR, 7),
    ('Скорпион', '♏', WATER, 8),
    ('Стрелец', '♐', FIRE, 9),
    ('Козерог', '♑', EARTH, 10),
    ('Водолей', '♒', AIR, 11),
    ('Рыбы', '♓', WATER, 12),
]

sign_angles = [(180 + i*30, 180 + (i+1)*30) for i in range(12)]

for i, (name, symbol, color, house_num) in enumerate(signs):
    t1, t2 = sign_angles[i]
    wedge = Wedge((0, 0), 1.0, t1, t2, width=0.14,
                  facecolor=color, edgecolor=BORDER, linewidth=2, alpha=0.15)
    ax.add_patch(wedge)

    mid = np.radians((t1 + t2) / 2)
    r_name = 0.93
    x, y = r_name * np.cos(mid), r_name * np.sin(mid)
    ax.text(x, y, f'{symbol}\n{name}', ha='center', va='center',
            fontsize=12, color=DARK, fontweight='bold')

    r_house = 0.80
    xh, yh = r_house * np.cos(mid), r_house * np.sin(mid)
    circle_bg = Circle((xh, yh), 0.038, facecolor='white',
                       edgecolor=BORDER, linewidth=1.5, zorder=5)
    ax.add_patch(circle_bg)
    ax.text(xh, yh, str(house_num), ha='center', va='center',
            fontsize=15, color=BORDER, fontweight='bold', zorder=6)

for i in range(12):
    t = 180 + i * 30
    rad = np.radians(t)
    ax.plot([0.62*np.cos(rad), 1.0*np.cos(rad)],
            [0.62*np.sin(rad), 1.0*np.sin(rad)],
            color=BORDER, linewidth=1.2, alpha=0.5)

# ===== АСЦЕНДЕНТ =====
ax.plot([-1.12, -0.62], [0, 0], color='#C0392B', linewidth=5, zorder=10)
ax.text(-1.20, 0, 'ASC', ha='center', va='center', fontsize=18,
        color='#C0392B', fontweight='bold', zorder=10)

# Стрелка направления
arrow_arc = patches.Arc((0, 0), 2.15, 2.15, angle=0, theta1=195, theta2=345,
                        color=BORDER, linewidth=2, linestyle='--')
ax.add_patch(arrow_arc)
ax.annotate('', xy=(0.93, -0.48), xytext=(0.86, -0.58),
            arrowprops=dict(arrowstyle='->', color=BORDER, lw=2))
ax.text(0.78, -0.72, 'Против часовой', ha='center', va='center',
        fontsize=11, color=BORDER, fontstyle='italic')

# ===== АРКАНЫ =====
boundaries = [210, 240, 270, 300, 330, 0, 30, 60, 90, 120, 150]

# Символы - используем только базовые Unicode, поддерживаемые DejaVu Sans
arcana_cw = [
    ('I', 'МАГ', '#6C3483', '∞'),
    ('II', 'ЖРИЦА', '#8E44AD', '☽'),
    ('III', 'ИМПЕРА\nТРИЦА', '#C2185B', '♀'),
    ('IV', 'ИМПЕРА\nТОР', '#922B21', '♔'),
    ('V', 'ИЕРО\nФАНТ', '#D68910', '✚'),
    ('VI', 'ВЛЮБ\nЛЁННЫЕ', '#CB4335', '♥'),
    ('VII', 'КОЛЕ\nСНИЦА', '#E67E22', '⚔'),
    ('VIII', 'СИЛА', '#A04000', '♌'),
    ('IX', 'ОТШЕЛЬ\nНИК', '#5D6D7E', '▲'),
    ('X', 'КОЛЕСО\nФОРТУНЫ', '#1E8449', '☸'),
    ('XI', 'СПРАВЕД\nЛИВОСТЬ', '#2471A3', '⚖'),
]

arcana_ccw = [
    ('XII', 'ПОВЕ\nШЕННЫЙ', '#148F77', '♣'),
    ('XIII', 'СМЕРТЬ', '#1C2833', '☠'),
    ('XIV', 'УМЕРЕН\nНОСТЬ', '#2E86C1', '⚱'),
    ('XV', 'ДЬЯВОЛ', '#6C3483', '♦'),
    ('XVI', 'БАШНЯ', '#922B21', '⌁'),
    ('XVII', 'ЗВЕЗДА', '#D4AC0D', '★'),
    ('XVIII', 'ЛУНА', '#7D3C98', '●'),
    ('XIX', 'СОЛНЦЕ', '#D68910', '☉'),
    ('XX', 'СУД', '#C0392B', '♪'),
    ('XXI', 'МИР', '#239B56', '◉'),
    ('XXII', 'ДУРАК', '#CA6F1E', '✿'),
]

# Рисуем арканы I-XI (r=0.64)
for i, (num, name, color, sym) in enumerate(arcana_cw):
    ca = boundaries[i]
    t1, t2 = ca - 15, ca + 15

    wedge = Wedge((0, 0), 0.72, t1, t2, width=0.16,
                  facecolor=color, edgecolor='white', linewidth=1, alpha=0.08)
    ax.add_patch(wedge)

    mid = np.radians(ca)
    r_card = 0.64
    xc, yc = r_card * np.cos(mid), r_card * np.sin(mid)

    draw_card(ax, xc, yc, 0.13, 0.17, num, name, color, sym)

# Рисуем арканы XII-XXII (r=0.44)
for i, (num, name, color, sym) in enumerate(arcana_ccw):
    ca = boundaries[10 - i]
    t1, t2 = ca - 15, ca + 15

    wedge = Wedge((0, 0), 0.52, t1, t2, width=0.16,
                  facecolor=color, edgecolor='white', linewidth=1, alpha=0.08)
    ax.add_patch(wedge)

    mid = np.radians(ca)
    r_card = 0.44
    xc, yc = r_card * np.cos(mid), r_card * np.sin(mid)

    draw_card(ax, xc, yc, 0.12, 0.16, num, name, color, sym)

# ===== КОЛЬЦА =====
for r, lw, alpha in [(1.0, 2.5, 0.9), (0.86, 1.5, 0.7), (0.72, 1, 0.5),
                     (0.56, 1, 0.5), (0.36, 1.5, 0.7)]:
    circle = Circle((0, 0), r, fill=False, color=BORDER,
                    linewidth=lw, alpha=alpha)
    ax.add_patch(circle)

# Центральный круг
center_bg = Circle((0, 0), 0.20, facecolor='white',
                   edgecolor=BORDER, linewidth=2)
ax.add_patch(center_bg)
ax.text(0, 0.02, '⚹', ha='center', va='center', fontsize=28, color=BORDER)
ax.text(0, -0.06, 'TAROT', ha='center', va='center',
        fontsize=8, color=BORDER, alpha=0.7)

# ===== ЗАГОЛОВОК =====
ax.text(0, 1.28, 'АСТРОЛОГИЧЕСКАЯ КАРТА', ha='center', va='center',
        fontsize=24, color=DARK, fontweight='bold')
ax.text(0, 1.20, 'Старшие Аркана Таро Уэйта', ha='center', va='center',
        fontsize=14, color=BORDER)

# ===== ЛЕГЕНДА =====
ax.text(1.08, -1.08, '→ I – XI  (по часовой)', ha='left', va='center',
        fontsize=11, color='#6C3483', fontweight='bold')
ax.text(1.08, -1.15, '← XII – XXII (против часовой)', ha='left', va='center',
        fontsize=11, color='#148F77', fontweight='bold')

plt.tight_layout()
plt.savefig(save_path, dpi=200, bbox_inches='tight',
            facecolor='#FAF8F3', edgecolor='none')
# plt.show()  # отключено для автоматического сохранения без окна
print(f"Сохранено в {save_path}")
