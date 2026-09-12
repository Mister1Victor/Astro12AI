import re
from collections import Counter
from typing import List, Any, ClassVar  # 🆕 Добавлен ClassVar
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from pydantic import PrivateAttr  # 🆕 Добавлен импорт PrivateAttr

from core.knowledge.weights import (
    ASTRO_TERMS,
    get_document_weight,
    AUTHOR_DEFINITIONS,
)
from core.rag.classifier import classify_question, ASTRO_TOPICS
from backend.logger import get_logger

logger = get_logger()


class AstroRetriever(BaseRetriever):
    """
    Центральный поисковый движок Astro12AI.
    """
# 🆕 Приватные атрибуты Pydantic (не проверяются как поля модели)
    _documents: List[Document] = PrivateAttr()
    _retriever: Any = PrivateAttr()

    # 🆕 Все константы класса теперь имеют аннотацию ClassVar[тип]
    REPLACE: ClassVar[dict] = {
        "квадратура": "квадрат", "квадрате": "квадрат", "квадратуры": "квадрат",
        "тригон": "трин", "тригоне": "трин", "трина": "трин", "трине": "трин",
        "секстиля": "секстиль", "секстиле": "секстиль",
        "соединения": "соединение", "соединении": "соединение", "слияние": "соединение",
        "оппозиции": "оппозиция", "квиконсе": "квиконс",
        "овне": "овен", "овнах": "овен",
        "тельце": "телец", "тельцах": "телец",
        "близнеце": "близницы", "близнецах": "близнецы", "близнеци": "близнецы", "близницах": "близнецы", "близнице": "близнецы",
        "раке": "рак", "раках": "рак",
        "льве": "лев", "львах": "лев",
        "деве": "дева", "девах": "дева",
        "весах": "весы", "висы": "весы", "висах": "весы",
        "скорпионе": "скорпион", "скорпионах": "скорпион", "скорпеоне": "скорпион", "скорпеонах": "скорпион",
        "стрельце": "стрелец", "стрельцах": "стрелец",
        "козероге": "козерог", "козерогах": "козерог", "козироге": "козерог", "козирогах": "козерог",
        "водолее": "водолей", "водолеях": "водолей",
        "рыбах": "рыбы", "рыбами": "рыбы",
        "I": "1 дом", "II": "2 дом", "III": "3 дом", "IV": "4 дом", "V": "5 дом", "VI": "6 дом",
        "VII": "7 дом", "VIII": "8 дом", "IX": "9 дом", "X": "10 дом", "XI": "11 дом", "XII": "12 дом",
        "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы", "Can": "Рак", "Leo": "Лев", "Vir": "Дева",
        "Lib": "Весы", "Sco": "Скорпион", "Sgr": "Стрелец", "Cap": "Козерог", "Aqr": "Водолей", "Psc": "Рыбы"
    }

    PLANETS: ClassVar[set] = {"солнце", "луна", "меркурий", "венера", "марс",
                              "юпитер", "сатурн", "уран", "нептун", "плутон", "церера", "эрида"}

    SIGNS: ClassVar[set] = {"овен", "телец", "близнецы", "рак", "лев", "дева",
                            "весы", "скорпион", "стрелец", "козерог", "водолей", "рыбы"}

    ASPECTS: ClassVar[set] = {
        "соединение", "квадрат", "оппозиция", "трин", "секстиль", "квиконс",
        # 🆕 Добавляем варианты с латинскими буквами (частая опечатка при копировании)
        "cоединение", "квадрат", "оппозиция", "трин", "cекстиль", "квиконс"
    }

    HOUSES: ClassVar[set] = {f"{i} дом" for i in range(1, 13)}

    # 🆕 Не забудьте про Лунные дни, если добавляли их ранее
    LUNAR_DAYS: ClassVar[set] = {
        "1 лунный день", "2 лунный день", "3 лунный день", "4 лунный день", "5 лунный день",
        "6 лунный день", "7 лунный день", "8 лунный день", "9 лунный день", "10 лунный день",
        "11 лунный день", "12 лунный день", "13 лунный день", "14 лунный день", "15 лунный день",
        "16 лунный день", "17 лунный день", "18 лунный день", "19 лунный день", "20 лунный день",
        "21 лунный день", "22 лунный день", "23 лунный день", "24 лунный день", "25 лунный день",
        "26 лунный день", "27 лунный день", "28 лунный день", "29 лунный день", "30 лунный день",
        # Добавляем словесные варианты для надежности
        "первый лунный день", "второй лунный день", "третий лунный день", "четвертый лунный день",
        "пятый лунный день", "шестой лунный день", "седьмой лунный день", "восьмой лунный день",
        "девятый лунный день", "десятый лунный день", "одиннадцатый лунный день", "двенадцатый лунный день",
        "тринадцатый лунный день", "четырнадцатый лунный день", "пятнадцатый лунный день",
        "шестнадцатый лунный день", "семнадцатый лунный день", "восемнадцатый лунный день",
        "девятнадцатый лунный день", "двадцатый лунный день", "двадцать первый лунный день",
        "двадцать второй лунный день", "двадцать третий лунный день", "двадцать четвертый лунный день",
        "двадцать пятый лунный день", "двадцать шестой лунный день", "двадцать седьмой лунный день",
        "двадцать восьмой лунный день", "двадцать девятый лунный день", "тридцатый лунный день"
    }

    FORBIDDEN: ClassVar[dict] = {
        "плутон": ["трансформация", "планета трансформации", "перерождение", "глубинные изменения", "власть", "разрушения", "массы", "большие ресурсы", "чужие деньги", "ядерное оружие"],
        "нептун": ["иллюзии", "духовность", "самообман", "вера", "религия", "безусловная любовь", "идеализм", "идеализация", "мечты", "нереалистично", "сострадание", "духовные практики"],
        "уран": ["революция", "планета революций", "революции", "переворот", "перевороты", "коллективы", "единомышленники", "друзья", "группы людей", "люди"],
        "юпитер": ["удача", "везение", "расширение", "рост", "успех", "победа", "благодетель", "возможности", "финансы", "философия"],
        "церера": ["материнство", "уход", "питание", "уход за другим", "материнский инстинкт"],
        "эрида": ["конфликты", "протесты", "революции", "революционные идеи", "перевороты", "бунты"],
    }

    # 🆕 Человеко-читаемые названия тем вопроса (для «Задачи» в main.py)
    TOPIC_LABELS: ClassVar[dict] = {
        "love": "отношения и любовь",
        "money": "деньги, работа, финансы",
        "health": "здоровье и самочувствие",
        "spirit": "духовность, карма, предназначение",
        "general": "общий разбор",
    }

    # 🆕 Краткие названия сфер домов (из AUTHOR_DEFINITIONS Школы) — для «Задачи»
    HOUSE_SPHERE_LABELS: ClassVar[dict] = {
        "1 дом": "сфера активных действий",
        "2 дом": "материальная сфера и накопления",
        "3 дом": "сфера коммуникаций и обучения",
        "4 дом": "семейная сфера и жильё",
        "5 дом": "сфера творчества и выступлений",
        "6 дом": "сфера здоровья и работы/услуг",
        "7 дом": "сфера партнёрства и отношений",
        "8 дом": "финансовая и сексуальная сфера",
        "9 дом": "сфера знаний и путешествий",
        "10 дом": "деловая сфера и карьера",
        "11 дом": "социальная сфера",
        "12 дом": "духовная сфера",
    }

    def __init__(self, documents: List[Document], k: int = 4, **kwargs):
        super().__init__(**kwargs)  # 🆕 Обязательно вызываем init базового класса!

        self._documents = documents  # 🆕 Используем _documents вместо documents
        for doc in self._documents:
            source = doc.metadata.get("source", "")
            filename = source.split("/")[-1].split("\\")[-1]
            doc.metadata["weight"] = get_document_weight(filename)

        self._retriever = BM25Retriever.from_documents(
            self._documents)  # 🆕 Используем _retriever
        self._retriever.k = k

    # Этот метод заставляет LangChain использовать ваш кастомный поиск
    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Document]:
        return self.search(query)

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def search(self, query):
        expanded_query = self.expand_query(query)

        # 1. Базовый поиск и первичная фильтрация
        docs = self._retriever.invoke(expanded_query)[:10]
        docs = self.remove_duplicates(docs)
        docs = self.filter_short_documents(docs)
        docs = self.filter_by_entities(query, docs)
        docs = self.limit_same_source(docs)

        # 2. Специфичные фильтрации
        docs = self.force_school_definition(query, docs)

        # 🆕 3. ФИЛЬТРАЦИЯ ПО ЗАПРЕЩЕННЫМ СЛОВАМ (ДОЛЖНА БЫТЬ ДО ИНЖЕКЦИИ!)
        # Иначе фильтр удалит документ, увидев запрещенные слова в нашем же списке "ЗАПРЕЩЕНО"
        parsed = self.parse_chart(query)
        active_forbidden_words = set()
        for planet in parsed["planets"]:
            if planet in self.FORBIDDEN:
                active_forbidden_words.update(self.FORBIDDEN[planet])

        if active_forbidden_words:
            docs = [
                doc for doc in docs
                if not any(word in doc.page_content.lower() for word in active_forbidden_words)
            ]

        # 🆕 4. РАНЖИРОВАНИЕ по авторским ключевым словам Школы + теме вопроса.
        # Раньше было мёртвым кодом: порядок документов полностью определялся BM25.
        # Теперь: документы с авторскими ключевыми словами сущностей запроса
        # и релевантные теме вопроса поднимаются выше (буст, без удаления остальных).
        docs = self.sort_documents(query, docs)

        # 🆕 5. ИНЖЕКЦИЯ АВТОРСКИХ ОПРЕДЕЛЕНИЙ (теперь в чистые, отфильтрованные и ранжированные документы)
        docs = self.inject_context_blocks(query, docs)

        # 6. Логирование результатов (для отладки)
        logger.info("\nTOP DOCUMENTS ПОСЛЕ ВСЕХ ФИЛЬТРОВ И РАНЖИРОВАНИЯ:")
        for i, doc in enumerate(docs[:5], 1):
            logger.info(
                f"{i}. {doc.metadata.get('source')} | weight={doc.metadata.get('weight')} | size={len(doc.page_content)}")

        return docs

    def force_school_definition(self, query, docs):
        entities = self.extract_entities(query)
        if len(entities) != 1:
            return docs

        entity = next(iter(entities))
        school_terms = ASTRO_TERMS.get(entity)
        if not school_terms:
            return docs

        result = []
        for doc in docs:
            text = self.normalize_query(doc.page_content)
            # text уже в нижнем регистре
            matches = sum(word in text for word in school_terms)
            if matches >= 3:
                result.append(doc)

        return result or docs

    def build_task_hint(self, query):
        """
        🆕 Детектор типа запроса → строка «Задачи» для LLM.
        Заменяет жёсткий «Комплексный анализ по всем фундаментальным сферам».
        Логика (по запросу пользователя):
          • 1 планета + 1 знак           → разбор ситуации (функция планеты через качества знака)
          • 2+ планеты + аспект          → анализ взаимодействия планет через аспект
          • + дом(а)                     → анализ в контексте сферы жизни (по авторскому определению)
          • + тема вопроса (love/...)    → анализ в контексте вопроса
          • общий разбор                 → комплексный анализ
        """
        chart = self.parse_chart(query)
        planets = chart["planets"]
        signs = chart["signs"]
        houses = chart["houses"]
        aspects = chart["aspects"]
        topic = classify_question(query)

        has_aspect = bool(aspects)
        multi_planets = len(planets) >= 2
        has_sign = bool(signs)
        has_house = bool(houses)
        has_topic = topic != "general"

        parts = []

        # Базовый тип анализа по астрологической структуре запроса
        if multi_planets and has_aspect:
            parts.append("анализ взаимодействия планет через аспект")
        elif planets and has_sign:
            parts.append("разбор ситуации: функции планеты через качества знака")
        elif planets:
            parts.append("разбор функций и ролей планеты")
        elif has_sign:
            parts.append("разбор качеств знака Зодиака")
        else:
            parts.append("комплексный разбор")

        # Если указан дом — анализ в контексте сферы жизни (по авторскому определению Школы)
        if has_house:
            spheres = [self.HOUSE_SPHERE_LABELS.get(h, h) for h in houses]
            parts.append("в контексте сферы жизни: " + ", ".join(spheres))

        # Если есть конкретная тема вопроса — анализ в контексте вопроса
        if has_topic:
            parts.append(f"в контексте вопроса: {self.TOPIC_LABELS.get(topic, topic)}")

        task = ", ".join(parts)
        # Если распознали только общий разбор и больше ничего — сохраняем прежнее поведение
        if not has_aspect and not multi_planets and not planets and not has_sign and not has_house and not has_topic:
            task = "комплексный анализ по фундаментальным сферам"

        logger.info(f"🧭 Тип запроса: {task}")
        return task

    def get_retriever(self):
        return self._retriever  # 🆕 _retriever

    def stats(self):
        # 🆕 _documents и _retriever
        return {"documents": len(self._documents), "k": self._retriever.k}

    # ==========================================================
    # NORMALIZATION & EXTRACTION
    # ==========================================================

    def normalize_query(self, text):
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        for old, new in self.REPLACE.items():
            text = text.replace(old, new)
        return re.sub(r"\s+", " ", text).strip()

    def tokenize(self, text):
        return [word for word in self.normalize_query(text).split() if len(word) > 2]

    def extract_entities(self, text):
        text = self.normalize_query(text)
        entities = set()
        # 🆕 Добавлено self.LUNAR_DAYS в кортеж коллекций
        for collection in (self.PLANETS, self.SIGNS, self.ASPECTS, self.HOUSES, self.LUNAR_DAYS):
            for value in collection:
                if value in text:
                    entities.add(value)
        return entities

    def parse_chart(self, text):
        text = self.normalize_query(text)
        return {
            "planets": [p for p in self.PLANETS if p in text],
            "signs": [s for s in self.SIGNS if s in text],
            "houses": [h for h in self.HOUSES if h in text],
            "aspects": [a for a in self.ASPECTS if a in text],
        }

    def expand_query(self, query):
        """
        Расширение запроса для BM25.
        🆕 Уменьшено раздувание: вместо [:8] ключевых слов на каждую сущность — [:5],
        плюс добавляются слова темы вопроса (если запрос конкретный).
        """
        query = self.normalize_query(query)
        expanded = [query]

        for entity in self.extract_entities(query):
            # ИСПРАВЛЕНО: было extend(entity), что разбивало слово на буквы!
            expanded.append(entity)

            if entity not in ASTRO_TERMS:
                continue

            # 🆕 Было [:8] — резкое раздувание запроса при нескольких сущностях.
            for keyword in ASTRO_TERMS[entity][:5]:
                expanded.append(keyword)

        # 🆕 Добавляем слова темы вопроса (конкретный вопрос → контекст в поиске)
        topic = classify_question(query)
        if topic != "general":
            expanded.extend(ASTRO_TOPICS.get(topic, []))

        print("QUERY:", query)
        print("EXPANDED QUERY:", " | ".join(expanded))

        return " ".join(expanded)

    def build_authority_context(self, query):
        entities = self.extract_entities(query)
        if not entities:
            return ""

        parts = ["=== АВТОРСКИЕ ОПРЕДЕЛЕНИЯ ШКОЛЫ ===", ""]
        for entity in entities:
            if entity not in ASTRO_TERMS:
                continue
            parts.append(entity.upper())
            for term in ASTRO_TERMS[entity]:
                parts.append(f"• {term}")
            parts.append("")

        parts.extend([
            "Используй только определения Школы.",
            "Игнорируй любые общеастрологические трактовки.",
            "Если информация отсутствует — не придумывай её."
        ])
        return "\n".join(parts)

    def is_entity_query(self, query):
        return len(self.extract_entities(query)) == 1

    def inject_context_blocks(self, query, docs):
        from langchain_core.documents import Document

        entities = self.extract_entities(query)
        logger.info(f"🔍 1. Извлечённые сущности из запроса: {entities}")

        blocks = []

        # 1. Инжекция авторских определений планет
        for entity in entities:
            if entity in AUTHOR_DEFINITIONS:
                logger.info(
                    f"✅ 2. НАЙДЕНО авторское определение для: '{entity}'")
                blocks.append(AUTHOR_DEFINITIONS[entity])
            else:
                logger.warning(
                    f"⚠️ 2. НЕ НАЙДЕНО авторское определение для: '{entity}' (проверьте weights.py)")

        # 2. Инжекция ключевых слов знаков и домов
        for entity in entities:
            if entity in self.PLANETS:
                continue
            if entity in ASTRO_TERMS and ASTRO_TERMS[entity]:
                logger.info(f"✅ 3. НАЙДЕНЫ ключевые слова для: '{entity}'")
                block = [f"=== КЛЮЧЕВЫЕ СЛОВА: {entity.upper()} ==="]
                for term in ASTRO_TERMS[entity]:
                    block.append(f"• {term}")
                blocks.append("\n".join(block))

        logger.info(
            f"📦 4. Всего подготовлено блоков для инжекции: {len(blocks)}")

        # 3. Логика применения блоков
        if not docs:
            logger.warning(
                "⚠️ 5. BM25 не нашёл ни одного документа! Создаём fallback.")
            if blocks:
                fallback_content = "\n\n".join(blocks)
                fallback_doc = Document(
                    page_content=fallback_content,
                    metadata={
                        "source": "AUTHOR_DEFINITIONS (fallback)", "weight": 10}
                )
                return [fallback_doc]
            return []

        # Если документы есть, впрыскиваем наши блоки в самое начало ПЕРВОГО документа
        if blocks:
            combined = "\n\n".join(blocks)
            docs[0].page_content = combined + \
                "\n\n=== НАЙДЕННЫЕ ФРАГМЕНТЫ ИЗ БАЗЫ ===\n\n" + \
                docs[0].page_content
            logger.info(
                f"✅ 5. УСПЕШНО инжектировано {len(blocks)} блоков в начало документа '{docs[0].metadata.get('source')}'")
        else:
            logger.warning(
                "⚠️ 5. Блоков для инжекции нет, возвращаем документы как есть.")

        return docs

    # ==========================================================
    # FILTERS
    # ==========================================================

    def remove_duplicates(self, docs):
        unique = {}
        for doc in docs:
            # dict сохраняет порядок в Python 3.7+
            unique[doc.page_content.strip()] = doc
        return list(unique.values())

    def filter_short_documents(self, docs, min_chars=350):
        return [doc for doc in docs if len(doc.page_content) >= min_chars]

    def filter_by_entities(self, query, docs):
        query_entities = self.extract_entities(query)
        if not query_entities:
            return docs

        result = []
        minimum = max(1, len(query_entities) // 2)

        for doc in docs:
            matches = len(query_entities &
                          self.extract_entities(doc.page_content))
            if matches >= minimum:
                result.append(doc)
        return result

    def limit_same_source(self, docs, max_per_source=2):
        result = []
        counter = {}
        for doc in docs:
            source = doc.metadata.get("source", "")
            counter[source] = counter.get(source, 0) + 1
            if counter[source] > max_per_source:
                continue
            result.append(doc)
        return result

    # ==========================================================
    # RANKING
    # ==========================================================

    def calculate_score(self, query, document):
        query_words = Counter(self.tokenize(query))
        document_words = Counter(self.tokenize(document.page_content))

        keyword_score = sum(
            document_words[word] * count for word, count in query_words.items())
        entity_score = self.entity_score(query, document)
        astro_score = self.astro_terms_score(query, document)
        chart_score = self.chart_score(query, document)
        exact_score = self.exact_entity_match(query, document)
        topic_score = self.topic_score(query, document)
        weight = document.metadata.get("weight", 5)

        # 🆕 Ранжирование по авторским ключевым словам Школы + теме вопроса.
        # authority_score убран (дублировал astro_terms_score).
        return (
            astro_score * 500 +      # авторские ключевые слова Школы (главный буст)
            topic_score * 150 +      # 🆕 релевантность теме вопроса (буст контекста)
            chart_score * 200 +      # совпадение планет/знаков/домов/аспектов
            entity_score * 120 +     # совпадение астрологических сущностей
            exact_score * 80 +       # точное совпадение набора сущностей
            keyword_score * 10 +     # общее совпадение слов
            weight                   # вес документа-источника
        )

    def entity_score(self, query, document):
        return len(self.extract_entities(query) & self.extract_entities(document.page_content))

    def exact_entity_match(self, query, document):
        q = self.extract_entities(query)
        d = self.extract_entities(document.page_content)
        if not q:
            return 0
        if q == d:
            return 5
        if q.issubset(d):
            return 3
        return 0

    def chart_score(self, query, document):
        q = self.parse_chart(query)
        d = self.parse_chart(document.page_content)
        return (
            len(set(q["planets"]) & set(d["planets"])) * 5 +
            len(set(q["signs"]) & set(d["signs"])) * 4 +
            len(set(q["houses"]) & set(d["houses"])) * 4 +
            len(set(q["aspects"]) & set(d["aspects"])) * 6
        )

    def authority_score(self, query, document):
        # 🆕 УБРАН: полностью дублировал astro_terms_score. Оставлен как тонкая
        # обёртка для обратной совместимости, если где-то вызывался напрямую.
        return self.astro_terms_score(query, document)

    def astro_terms_score(self, query, document):
        # Сколько авторских ключевых слов сущностей запроса встречаются в документе.
        # Главный буст «ответ на основе ключевых слов Школы».
        score = 0
        document_text = self.normalize_query(document.page_content)
        for entity in self.extract_entities(query):
            for word in ASTRO_TERMS.get(entity, []):
                if word in document_text:
                    score += 1
        return score

    def topic_score(self, query, document):
        """
        🆕 Буст по теме вопроса (love/money/health/spirit).
        Реализует «конкретный вопрос → приоритет словам контекста вопроса».
        Если в запросе есть тема жизни — поднимаем документы, где она проявлена.
        """
        topic = classify_question(query)
        if topic == "general":
            return 0
        document_text = self.normalize_query(document.page_content)
        score = 0
        for word in ASTRO_TOPICS.get(topic, []):
            if word in document_text:
                score += 1
        return score

    def sort_documents(self, query, docs):
        docs.sort(key=lambda doc: self.calculate_score(
            query, doc), reverse=True)
        return docs
