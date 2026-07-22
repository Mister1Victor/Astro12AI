import re
from collections import Counter
from typing import List, Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from core.knowledge.weights import (
    ASTRO_TERMS,
    get_document_weight,
    AUTHOR_DEFINITIONS,
)
from backend.logger import get_logger

logger = get_logger()


class AstroRetriever(BaseRetriever):
    """
    Центральный поисковый движок Astro12AI.
    """

    REPLACE = {
        "квадратура": "квадрат", "квадрате": "квадрат", "квадратуры": "квадрат",
        "тригон": "трин", "тригоне": "трин", "трина": "трин", "трине": "трин",
        "секстиля": "секстиль", "секстиле": "секстиль",
        "соединения": "соединение", "соединении": "соединение", "слияние": "соединение",
        "оппозиции": "оппозиция", "квиконсе": "квиконс"
    }

    PLANETS = {"солнце", "луна", "меркурий", "венера", "марс",
               "юпитер", "сатурн", "уран", "нептун", "плутон", "церера", "эрида"}
    SIGNS = {"овен", "телец", "близнецы", "рак", "лев", "дева",
             "весы", "скорпион", "стрелец", "козерог", "водолей", "рыбы"}
    ASPECTS = {"соединение", "квадрат",
               "оппозиция", "трин", "секстиль", "квиконс"}
    HOUSES = {f"{i} дом" for i in range(1, 13)}
    LUNAR_DAYS = {
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

    FORBIDDEN = {
        "плутон": ["трансформация", "планета трансформации", "перерождение", "глубинные изменения", "власть", "разрушения", "массы", "большие ресурсы", "чужие деньги", "ядерное оружие"],
        "нептун": ["иллюзии", "духовность", "самообман", "вера", "религия", "безусловная любовь", "идеализм", "идеализация", "мечты", "нереалистично", "сострадание", "духовные практики"],
        "уран": ["революция", "планета революций", "революции", "переворот", "перевороты", "коллективы", "единомышленники", "друзья", "группы людей", "люди"],
        "юпитер": ["удача", "везение", "расширение", "рост", "успех", "победа", "благодетель", "возможности", "финансы", "философия"],
        "церера": ["материнство", "уход", "питание", "уход за другим", "материнский инстинкт"],
        "эрида": ["конфликты", "протесты", "революции", "революционные идеи", "перевороты", "бунты"],
    }

    def __init__(self, documents, k=4):  # 4 или 5
        self.documents = documents
        for doc in self.documents:
            source = doc.metadata.get("source", "")
            filename = source.split("/")[-1].split("\\")[-1]
            doc.metadata["weight"] = get_document_weight(filename)
        self.retriever = BM25Retriever.from_documents(self.documents)
        self.retriever.k = k

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def search(self, query):
        expanded_query = self.expand_query(query)

        print("\nPARSED CHART")
        print(self.parse_chart(query))
        print()

        # 1. Базовый поиск и первичная фильтрация
        docs = self.retriever.invoke(expanded_query)[:10]
        docs = self.remove_duplicates(docs)
        docs = self.filter_short_documents(docs)
        docs = self.filter_by_entities(query, docs)
        docs = self.limit_same_source(docs)

        # 2. Специфичные фильтрации и обогащение
        docs = self.force_school_definition(query, docs)
        docs = self.inject_context_blocks(query, docs)

        # 3. Фильтрация по запрещённым словам (удаляем документ целиком, а не портим текст)
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

        # 4. Добавление контекста авторитета (безопасно, только если документы остались)
        if self.is_entity_query(query) and docs:
            authority = self.build_authority_context(query)
            if authority:
                docs[0].metadata["authority_context"] = authority

        # 5. Логирование результатов
        print("\nTOP DOCUMENTS")
        for i, doc in enumerate(docs[:5], 1):
            print(f"{i}. {doc.metadata.get('source')} | weight={doc.metadata.get('weight')} | score={self.calculate_score(query, doc)}")

        print("\nCONTEXT\n")
        for doc in docs[:3]:
            print("=" * 80)
            print(doc.metadata.get("source"))
            print()
            print(doc.page_content[:1000])

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

    def get_retriever(self):
        return self.retriever

    def stats(self):
        return {"documents": len(self.documents), "k": self.retriever.k}

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
        query = self.normalize_query(query)
        expanded = [query]

        for entity in self.extract_entities(query):
            # ИСПРАВЛЕНО: было extend(entity), что разбивало слово на буквы!
            expanded.append(entity)

            if entity not in ASTRO_TERMS:
                continue

            for keyword in ASTRO_TERMS[entity][:8]:
                expanded.append(keyword)

        print("=" * 80)
        print("QUERY:", query)
        print("EXPANDED QUERY:", " | ".join(expanded))
        print("=" * 80)

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

# 🆕 ДОБАВЬТЕ ЭТОТ МЕТОД. Он скажет LangChain использовать ваш метод search
    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Document]:
        """Этот метод автоматически вызывается LangChain при запросе к ретриверу"""
        return self.search(query)

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
        authority_score = self.authority_score(query, document)
        weight = document.metadata.get("weight", 5)

        return (
            authority_score * 500 +
            chart_score * 200 +
            entity_score * 120 +
            exact_score * 80 +
            astro_score * 30 +
            keyword_score * 10 +
            weight
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
        entities = self.extract_entities(query)
        score = 0
        text = self.normalize_query(document.page_content)
        for entity in entities:
            for word in ASTRO_TERMS.get(entity, []):
                if word in text:
                    score += 1
        return score

    def astro_terms_score(self, query, document):
        score = 0
        document_text = self.normalize_query(document.page_content)
        for entity in self.extract_entities(query):
            for word in ASTRO_TERMS.get(entity, []):
                if word in document_text:
                    score += 1
        return score

    def sort_documents(self, query, docs):
        docs.sort(key=lambda doc: self.calculate_score(
            query, doc), reverse=True)
        return docs
