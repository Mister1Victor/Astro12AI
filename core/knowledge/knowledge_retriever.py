"""
Service for intelligent retrieval of astrological knowledge.
Loads Markdown files from knowledge_base and selects relevant context based on user query.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class KnowledgeRetriever:
    def __init__(self, base_path: str = "knowledge_base"):
        self.base_path = Path(base_path)
        self.cache: Dict[str, str] = {}  # filename -> content
        self.index: Dict[str, List[str]] = {
            'planets': [],
            'signs': [],
            'houses': [],
            'aspects': []
        }

        # Словари для нормализации поиска (русский -> файл)
        # Ключи в нижнем регистре
        self.planet_map = {
            'солнце': 'sun',
            'луна': 'moon',
            'меркурий': 'mercury',
            'венера': 'venus',
            'марс': 'mars',
            'церера': 'ceres',
            'юпитер': 'jupiter',
            'сатурн': 'saturn',
            'уран': 'uranus',
            'нептун': 'neptune',
            'плутон': 'pluto',
            'эрида': 'eris'
        }

        self.sign_map = {
            'овен': 'aries', 'телец': 'taurus', 'близнецы': 'gemini',
            'рак': 'cancer', 'лев': 'leo', 'дева': 'virgo',
            'весы': 'libra', 'скорпион': 'scorpio', 'стрелец': 'sagittarius',
            'козерог': 'capricorn', 'водолей': 'aquarius', 'рыбы': 'pisces'
        }

        # Дома (просто числа или слова "первый дом" и т.д.)
        self.house_map = {
            '1': 'house_1', 'первый': 'house_1', '1 дом': 'house_1',
            '2': 'house_2', 'второй': 'house_2', '2 дом': 'house_2',
            '3': 'house_3', 'третий': 'house_3', '3 дом': 'house_3',
            '4': 'house_4', 'четвертый': 'house_4', '4 дом': 'house_4',
            '5': 'house_5', 'пятый': 'house_5', '5 дом': 'house_5',
            '6': 'house_6', 'шестой': 'house_6', '6 дом': 'house_6',
            '7': 'house_7', 'седьмой': 'house_7', '7 дом': 'house_7',
            '8': 'house_8', 'восьмой': 'house_8', '8 дом': 'house_8',
            '9': 'house_9', 'девятый': 'house_9', '9 дом': 'house_9',
            '10': 'house_10', 'десятый': 'house_10', '10 дом': 'house_10',
            '11': 'house_11', 'одиннадцатый': 'house_11', '11 дом': 'house_11',
            '12': 'house_12', 'двенадцатый': 'house_12', '12 дом': 'house_12'
        }

        self.aspect_map = {
            'соединение': 'conjunction', 'трин': 'trine', 'квадрат': 'square',
            'оппозиция': 'opposition', 'секстиль': 'sextile', 'квиконс': 'quincunx',
            'полуквадрат': 'semisquare', 'полутораквадрат': 'sesquiquadrate'
        }

        self._load_all_files()

    def _load_all_files(self):
        """Загружает все .md файлы из подпапок в кэш."""
        if not self.base_path.exists():
            print(
                f"⚠️ Папка знаний {self.base_path} не найдена. Создайте её и заполните файлами.")
            return

        for category in ['planets', 'signs', 'houses', 'aspects']:
            cat_path = self.base_path / category
            if cat_path.exists():
                for file in cat_path.glob("*.md"):
                    try:
                        content = file.read_text(encoding='utf-8')
                        self.cache[file.name] = content
                        self.index[category].append(file.stem)
                    except Exception as e:
                        print(f"❌ Ошибка чтения файла {file}: {e}")

    def _normalize_text(self, text: str) -> str:
        return text.lower().strip()

    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Извлекает сущности (планеты, знаки, дома, аспекты) из запроса.
        Возвращает словарь со списками найденных ключей (английские имена файлов).
        """
        found = {
            'planets': [],
            'signs': [],
            'houses': [],
            'aspects': []
        }

        normalized_query = self._normalize_text(query)

        # Поиск планет
        for ru_name, en_file in self.planet_map.items():
            # Используем regex для поиска целого слова, чтобы "марс" не находилось в "марсианский" (хотя в астрологии это ок)
            if re.search(rf'\b{re.escape(ru_name)}\b', normalized_query):
                if en_file not in found['planets']:
                    found['planets'].append(en_file)

        # Поиск знаков
        for ru_name, en_file in self.sign_map.items():
            if re.search(rf'\b{re.escape(ru_name)}\b', normalized_query):
                if en_file not in found['signs']:
                    found['signs'].append(en_file)

        # Поиск домов (приоритет длинным фразам)
        # Сортируем ключи по длине (убывание), чтобы "10 дом" нашлось раньше чем "1"
        sorted_houses = sorted(self.house_map.keys(), key=len, reverse=True)
        for ru_name, en_file in [(k, self.house_map[k]) for k in sorted_houses]:
            if re.search(rf'\b{re.escape(ru_name)}\b', normalized_query):
                if en_file not in found['houses']:
                    found['houses'].append(en_file)
                break  # Нашли конкретное упоминание дома, дальше не ищем цифры отдельно для этого дома

        # Поиск аспектов
        for ru_name, en_file in self.aspect_map.items():
            if re.search(rf'\b{re.escape(ru_name)}\b', normalized_query):
                if en_file not in found['aspects']:
                    found['aspects'].append(en_file)

        return found

    def get_context(self, query: str) -> str:
        """
        Главный метод. Принимает вопрос пользователя, находит релевантные файлы
        и возвращает объединенный текст контекста.
        """
        entities = self.extract_entities(query)
        context_parts = []
        used_files = []

        # Собираем контент из найденных категорий
        for category, file_stems in entities.items():
            for stem in file_stems:
                filename = f"{stem}.md"
                if filename in self.cache:
                    content = self.cache[filename]
                    # Добавляем заголовок раздела для ясности
                    header = f"\n---\n### Материал Школы: {category.capitalize()} ({stem.replace('_', ' ').title()})\n---\n"
                    context_parts.append(header + content)
                    used_files.append(filename)

        if not context_parts:
            # Если ничего не найдено, возвращаем пустую строку или общий совет
            # В продакшене можно вернуть общий промт "Используй общие знания"
            return ""

        full_context = "\n".join(context_parts)
        # Для отладки можно логировать used_files
        # print(f"🧠 Контекст построен из файлов: {used_files}")

        return full_context

    def get_all_planets_context(self) -> str:
        """Возвращает контекст по всем планетам (для общих вопросов)."""
        return self._get_category_context('planets')

    def get_all_signs_context(self) -> str:
        """Возвращает контекст по всем знакам."""
        return self._get_category_context('signs')

    def _get_category_context(self, category: str) -> str:
        parts = []
        for stem in self.index.get(category, []):
            filename = f"{stem}.md"
            if filename in self.cache:
                parts.append(self.cache[filename])
        return "\n".join(parts)


# Пример использования (для тестирования локально)
if __name__ == "__main__":
    retriever = KnowledgeRetriever()
    test_query = "Как Солнце в Овне влияет на карьеру в 10 доме?"
    context = retriever.get_context(test_query)
    print(f"Запрос: {test_query}")
    print(f"Найден контекст (длина: {len(context)}):")
    print(context[:500] + "..." if len(context) > 500 else context)
# Совместимость с импортом в main.py (Шаг 1 интеграции)
AstroKnowledgeRetriever = KnowledgeRetriever
