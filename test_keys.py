from core.knowledge.weights import AUTHOR_DEFINITIONS, ASTRO_TERMS

print("=== ПРОВЕРКА СЛОВАРЕЙ ===")

# Проверяем строчные ключи (именно так их ищет код)
keys_to_check = ["нептун", "плутон", "овен", "водолей", "секстиль"]

for key in keys_to_check:
    in_auth = key in AUTHOR_DEFINITIONS
    in_terms = key in ASTRO_TERMS

    if in_auth:
        print(f"✅ '{key}' есть в AUTHOR_DEFINITIONS")
    elif in_terms and ASTRO_TERMS[key]:
        print(f"⚠️ '{key}' есть в ASTRO_TERMS (ключевые слова)")
    else:
        print(
            f"❌ '{key}' ОТСУТСТВУЕТ или пуст! Проверьте регистр букв в weights.py")
