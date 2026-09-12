"""Снимок полного состояния проекта Astro12AI (v2: бот + Mini App + модули)."""
import os
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "project_snapshot.txt"

IGNORE_DIRS = {
    "__pycache__", ".venv", "venv", ".git", ".vscode", "node_modules",
    ".gradle", "cache", "output", "images", "android", ".idea",
}

KEY_FILES = [
    "core/tarot/deck_texts.py",
    "core/tarot/texts/rider_waite.txt",
    "core/tarot/texts/thoth.txt",
    "core/tarot/texts/author_deck.txt",
    "core/knowledge/weights.py",
    "scripts/sync_decks.py",
    "scripts/add_card_sections.py",
    "scripts/fill_tarot_fields.py",
    "scripts/fill_rider_minor.py",
    "scripts/fill_thoth_fields.py",
    "scripts/edit_card.py",
    "docs/CHANGELOG.md",
    "docs/PROJECT_STATE.md",
    "docs/AI_MEMORY.md",
    ".env.example",
]


def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              cwd=ROOT, timeout=20).stdout
    except Exception as e:
        return f"[ошибка запуска {cmd}: {e}]\n"


def read_file(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[не прочитан: {e}]\n"


with open(OUT, "w", encoding="utf-8") as f:
    f.write(f"# СНИМОК ПРОЕКТА Astro12AI (v2)\n")
    f.write(f"# Дата: {datetime.now().isoformat()}\n")
    f.write(f"# Корень: {ROOT}\n")
    f.write("=" * 80 + "\n# 1. СТРУКТУРА (tree)\n" + "=" * 80 + "\n")
    for root, dirs, files in os.walk(ROOT):
        rel = Path(root).relative_to(ROOT)
        dirs[:] = sorted(d for d in dirs
                         if d not in IGNORE_DIRS and not d.startswith("."))
        indent = "  " * len(rel.parts)
        f.write(f"{indent}{rel.name or '.'}/\n")
        for name in sorted(files):
            f.write(f"{indent}  {name}\n")

    f.write("\n" + "=" * 80 + "\n# 2. GIT\n" + "=" * 80 + "\n")
    f.write("\n## git status\n" + run("git status"))
    f.write("\n## git log --oneline -20\n" + run("git log --oneline -20"))
    f.write("\n## git remote -v\n" + run("git remote -v"))

    f.write("\n" + "=" * 80 + "\n# 3. .gitignore (полный)\n" + "=" * 80 + "\n")
    f.write(read_file(ROOT / ".gitignore"))

    f.write("\n" + "=" * 80 + "\n# 4. КЛЮЧЕВЫЕ ФАЙЛЫ\n" + "=" * 80 + "\n")
    for rel in KEY_FILES:
        p = ROOT / rel
        f.write(f"\n{'─' * 80}\n### {rel} "
                f"{'[ЕСТЬ]' if p.exists() else '[НЕТ]'}\n{'─' * 80}\n")
        f.write(read_file(p) if p.exists() else "[файл отсутствует]\n")

    f.write("\n" + "=" * 80 + "\n# 5. СВОДКА КОЛОД\n" + "=" * 80 + "\n")
    decks_root = ROOT / "data" / "tarot" / "decks"
    if decks_root.exists():
        for d in sorted(decks_root.iterdir()):
            if not d.is_dir():
                continue
            dj = d / "deck.json"
            imgs = d / "images"
            n_imgs = len(list(imgs.glob("*"))) if imgs.exists() else 0
            f.write(f"\n[{d.name}]\n")
            f.write(f"  deck.json : {'есть' if dj.exists() else 'НЕТ'} "
                    f"({dj.stat().st_size if dj.exists() else 0} байт)\n")
            f.write(f"  images/   : {n_imgs} файлов\n")

print(f"✅ Снимок: {OUT} ({OUT.stat().st_size / 1024:.1f} КБ)")
print("   Прикрепите project_snapshot.txt следующим сообщением в чат.")
