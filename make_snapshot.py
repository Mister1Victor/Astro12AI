"""Снимок полного состояния проекта Astro12AI для передачи ассистенту."""
import os
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "project_snapshot.txt"

# Ключевые файлы проекта (полное содержимое)
KEY_FILES = [
    # Точка входа
    "main.py",
    # Бэкенд
    "backend/config.py",
    "backend/logger.py",
    "backend/validators.py",
    # Ядро — RAG и промпты
    "core/prompts/system_prompt.py",
    "core/prompts/tarot_prompt.py",
    "core/rag/engine.py",
    "core/rag/context.py",
    "core/rag/classifier.py",
    "core/llm/model.py",
    "core/knowledge/loader.py",
    # Таро
    "core/tarot/models.py",
    "core/tarot/loader.py",
    "core/tarot/service.py",
    "core/tarot/render.py",
    "core/tarot/keyboards.py",
    "core/tarot/dignities.py",
    # Скрипты генерации колод
    "scripts/init_tarot_data.py",
    "scripts/init_author_deck.py",
    "init_author_deck_146.py",
    "oracle_generator.py",
    # Конфиги
    ".gitignore",
    "requirements.txt",
    ".env.example",
    "README.md",
]


def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=ROOT, timeout=15).stdout
    except Exception as e:
        return f"[ошибка запуска {cmd}: {e}]\n"


def read_file(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[не прочитан: {e}]\n"


with open(OUT, "w", encoding="utf-8") as f:
    f.write(f"# СНИМОК ПРОЕКТА Astro12AI\n")
    f.write(f"# Дата: {datetime.now().isoformat()}\n")
    f.write(f"# Корень: {ROOT}\n\n")

    # 1. Структура (дерево, без __pycache__/.venv/.git/data/images)
    f.write("=" * 80 + "\n# 1. СТРУКТУРА ПРОЕКТА (tree)\n" + "=" * 80 + "\n")
    ignore = ("__pycache__", ".venv", ".git", "node_modules",
              "data/tarot/decks/rider_waite/images",
              "data/tarot/decks/thoth/images",
              "data/tarot/decks/author_deck/images",
              "data/tarot/decks/author_deck_146/images",
              "oracle_cards", "Astro12AI")
    for root, dirs, files in os.walk(ROOT):
        rel = Path(root).relative_to(ROOT)
        if any(part in ignore for part in rel.parts):
            dirs[:] = []
            continue
        dirs[:] = [
            d for d in dirs if d not in ignore and not d.startswith(".")]
        indent = "  " * len(rel.parts)
        f.write(f"{indent}{rel.name or '.'}/\n")
        for file in sorted(files):
            f.write(f"{indent}  {file}\n")

    # 2. git status / git log / remote
    f.write("\n" + "=" * 80 + "\n# 2. GIT\n" + "=" * 80 + "\n")
    f.write("\n## git status\n" + run("git status"))
    f.write("\n## git log --oneline -15\n" + run("git log --oneline -15"))
    f.write("\n## git remote -v\n" + run("git remote -v"))
    f.write("\n## git branch -a\n" + run("git branch -a"))

    # 3. .gitignore полностью
    f.write("\n" + "=" * 80 + "\n# 3. .gitignore (полный)\n" + "=" * 80 + "\n")
    f.write(read_file(ROOT / ".gitignore"))

    # 4. Содержимое ключевых файлов
    f.write("\n" + "=" * 80 + "\n# 4. КЛЮЧЕВЫЕ ФАЙЛЫ\n" + "=" * 80 + "\n")
    for rel in KEY_FILES:
        p = ROOT / rel
        f.write(
            f"\n{'─' * 80}\n### {rel} {'[ЕСТЬ]' if p.exists() else '[НЕТ]'}\n{'─' * 80}\n")
        f.write(read_file(p) if p.exists() else "[файл отсутствует]\n")

    # 5. Сводка колод
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

print(f"✅ Снимок записан: {OUT}")
print(f"   Размер: {OUT.stat().st_size / 1024:.1f} КБ")
print("   Пришлите его содержимое — я запомню состояние проекта.")
