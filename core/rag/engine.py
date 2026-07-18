import re

from collections import Counter, OrderedDict
from langchain_community.retrievers import BM25Retriever
from core.knowledge.weights import (
    ASTRO_TERMS,
    get_document_weight,
)

from core.knowledge.weights import AUTHOR_DEFINITIONS


class AstroRetriever:
    """
    Центральный поисковый движок Astro12AI.

    В дальнейшем весь интеллектуальный поиск будет
    реализован именно здесь без изменения main.py.
    """

    REPLACE = {
        "квадратура": "квадрат",
        "квадрате": "квадрат",
        "квадратуры": "квадрат",
        "тригон": "трин",
        "трина": "трин",
        "секстиля": "секстиль",
        "соединения": "соединение",
        "оппозиции": "оппозиция",
    }

    PLANETS = {
        "солнце",
        "луна",
        "меркурий",
        "венера",
        "марс",
        "юпитер",
        "сатурн",
        "уран",
        "нептун",
        "плутон",
    }

    SIGNS = {
        "овен",
        "телец",
        "близнецы",
        "рак",
        "лев",
        "дева",
        "весы",
        "скорпион",
        "стрелец",
        "козерог",
        "водолей",
        "рыбы",
    }

    ASPECTS = {
        "соединение",
        "квадрат",
        "оппозиция",
        "трин",
        "секстиль",
    }

    HOUSES = {
        f"{i} дом"
        for i in range(1, 13)
    }

    # ==========================================================
    # КОНФИГУРАЦИЯ ФИЛЬТРАЦИИ
    # ==========================================================
    FORBIDDEN = {
        "плутон": [
            "трансформация",
            "перерождение",
            "глубинные изменения",
            "власть",
            "разрушения",
            "массы",
            "большие ресурсы",
            "чужие деньги",
            "ядерное оружие",
        ],
        "нептун": [
            "иллюзии",
            "духовность",
            "самообман",
            "вера",
            "религия",
            "безусловная любовь",
            "идеализм",
            "мечты",
            "сострадание",
        ],
        # Пример: удаляем документы, содержащие запрещённые слова для планеты Плутон
        # (но сначала нужно определить, какая планета активна в запросе)
        # В будущем легко добавить другие планеты:
        # "сатурн": ["кризис", "ограничение", "карма"],
    }

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self, documents, k=8):

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
        if self.is_entity_query(query):
            authority = self.build_authority_context(
                query
            )
        else:
            authority = ""
        expanded_query = self.expand_query(query)
        print("\nPARSED CHART")
        print(self.parse_chart(query))
        print()

        docs = self.retriever.invoke(expanded_query)[:20]
        docs = self.remove_duplicates(docs)
        docs = self.filter_short_documents(docs)
        docs = self.filter_by_entities(query, docs)
        docs = self.limit_same_source(docs)
        docs = self.sort_documents(query, docs)
        docs = self.force_school_definition(query, docs)
        docs = self.inject_author_definition(query, docs)

        docs = self.remove_forbidden_terms(query, docs)

        if authority and docs:

            docs[0].metadata[
                "authority_context"
            ] = authority
        docs = self.force_school_definition(query, docs)

        # Добавляем контекст авторитета
        authority = self.build_authority_context(
            query,
        )

        if authority:

            docs[0].metadata[
                "authority_context"
            ] = authority

        # Фильтрация по запрещённым словам для активных планет

        parsed = self.parse_chart(query)
        active_forbidden_words = set()

        # Собираем все запрещённые слова для планет, найденных в запросе
        for planet in parsed["planets"]:
            if planet in self.FORBIDDEN:
                active_forbidden_words.update(self.FORBIDDEN[planet])

        # Фильтруем документы, только если есть что проверять
        if active_forbidden_words:
            docs = [
                doc for doc in docs
                if not any(word in doc.page_content.lower() for word in active_forbidden_words)
            ]

        print("\nTOP DOCUMENTS")
        for i, doc in enumerate(docs[:5], 1):

            print(
                f"{i}. "
                f"{doc.metadata.get('source')} | "
                f"weight={doc.metadata.get('weight')} | "
                f"score={self.calculate_score(query, doc)}"
            )

        print("\nCONTEXT\n")

        for doc in docs[:3]:

            print("=" * 80)
            print(doc.metadata.get("source"))
            print()
            print(doc.page_content[:1000])

        return docs

    def remove_forbidden_terms(
        self,
        query,
        docs,
    ):

        entities = self.extract_entities(query)

        if not entities:
            return docs

        for entity in entities:

            forbidden = FORBIDDEN.get(entity)

            if not forbidden:
                continue

            for doc in docs:

                text = doc.page_content

                for word in forbidden:

                    text = re.sub(
                        word,
                        "",
                        text,
                        flags=re.IGNORECASE,
                    )

                doc.page_content = text

        return docs

    def force_school_definition(
        self,
        query,
        docs,
    ):
        """
        Если пользователь спрашивает одну сущность,
        оставляем только документы,
        содержащие авторское описание Школы.
        """

        entities = self.extract_entities(query)

        if len(entities) != 1:
            return docs

        entity = next(iter(entities))

        school_terms = ASTRO_TERMS.get(entity)

        if not school_terms:
            return docs

        result = []

        for doc in docs:

            text = self.normalize_query(
                doc.page_content
            )

            matches = sum(
                word.lower() in text
                for word in school_terms
            )

            if matches >= 3:
                result.append(doc)

        return result or docs

    def get_retriever(self):
        return self.retriever

    def stats(self):
        return {
            "documents": len(self.documents),
            "k": self.retriever.k,
        }

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    def normalize_query(self, text):

        text = text.lower()

        text = re.sub(r"[^\w\s]", " ", text)

        for old, new in self.REPLACE.items():
            text = text.replace(old, new)

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def tokenize(self, text):

        return [
            word
            for word in self.normalize_query(text).split()
            if len(word) > 2
        ]

    # ==========================================================
    # ENTITY EXTRACTION
    # ==========================================================

    def extract_entities(self, text):

        text = self.normalize_query(text)

        entities = set()

        for collection in (
            self.PLANETS,
            self.SIGNS,
            self.ASPECTS,
            self.HOUSES,
        ):
            for value in collection:
                if value in text:
                    entities.add(value)

        return entities

    def parse_chart(self, text):
        """
        Разбирает запрос на астрологические сущности.
        """

        text = self.normalize_query(text)

        return {
            "planets": [
                p for p in self.PLANETS
                if p in text
            ],

            "signs": [
                s for s in self.SIGNS
                if s in text
            ],

            "houses": [
                h for h in self.HOUSES
                if h in text
            ],

            "aspects": [
                a for a in self.ASPECTS
                if a in text
            ],
        }

    def chart_score(
        self,
        query,
        document,
    ):
        """
        Совпадение полной астрологической конструкции.
        """

        q = self.parse_chart(query)

        d = self.parse_chart(document.page_content)

        score = 0

        score += len(
            set(q["planets"])
            &
            set(d["planets"])
        ) * 5

        score += len(
            set(q["signs"])
            &
            set(d["signs"])
        ) * 4

        score += len(
            set(q["houses"])
            &
            set(d["houses"])
        ) * 4

        score += len(
            set(q["aspects"])
            &
            set(d["aspects"])
        ) * 6

        return score

    def expand_query(self, query):

        query = self.normalize_query(query)

        expanded = [query]

        for entity in self.extract_entities(query):

            expanded.extend([entity, entity])

            if entity not in ASTRO_TERMS:
                continue

            for keyword in ASTRO_TERMS[entity][:8]:
                expanded.append(keyword)

        print("=" * 80)
        print("QUERY")
        print(query)
        print()
        print("EXPANDED")
        print("\nEXPANDED QUERY")
        for word in expanded:
            print("•", word)
        print("=" * 80)

        return " ".join(expanded)

    def build_authority_context(
        self,
        query,
    ):
        """
        Собирает авторские определения
        для найденных сущностей.

        Этот текст будет помещаться
        В НАЧАЛО контекста.
        """

        entities = self.extract_entities(query)

        if not entities:
            return ""

        parts = [
            "=== АВТОРСКИЕ ОПРЕДЕЛЕНИЯ ШКОЛЫ ===",
            "",
        ]

        for entity in entities:

            if entity not in ASTRO_TERMS:
                continue

            parts.append(entity.upper())

            for term in ASTRO_TERMS[entity]:

                parts.append(f"• {term}")

            parts.append("")

        parts.append("")

        parts.append(
            "Используй только определения Школы."
        )

        parts.append(
            "Игнорируй любые общеастрологические трактовки."
        )

        parts.append(
            "Если информация отсутствует — не придумывай её."
        )

        return "\n".join(parts)

    def inject_author_definition(
        self,
        query,
        docs,
    ):

        entities = self.extract_entities(query)

        if not docs:
            return docs

        definitions = []

        for entity in entities:

            if entity in AUTHOR_DEFINITIONS:

                definitions.append(
                    AUTHOR_DEFINITIONS[entity]
                )

        if definitions:

            docs[0].page_content = (

                "\n\n".join(definitions)

                + "\n\n"

                + docs[0].page_content

            )

        return docs

    def is_entity_query(
        self,
        query,
    ):

        return len(
            self.extract_entities(query)
        ) == 1

    # ==========================================================
    # FILTERS
    # ==========================================================

    def remove_duplicates(self, docs):

        unique = OrderedDict()

        for doc in docs:

            unique.setdefault(doc.page_content.strip(), doc)

        return list(unique.values())

    def filter_short_documents(
        self,
        docs,
        min_chars=350,
    ):

        return [
            doc
            for doc in docs
            if len(doc.page_content) >= min_chars
        ]

    def filter_by_entities(
        self,
        query,
        docs,
    ):

        query_entities = self.extract_entities(query)

        if not query_entities:
            return docs

        result = []

        minimum = max(
            1,
            len(query_entities) // 2,
        )

        for doc in docs:

            matches = len(
                query_entities &
                self.extract_entities(doc.page_content)
            )

            if matches >= minimum:
                result.append(doc)

        return result

    def limit_same_source(
        self,
        docs,
        max_per_source=2,
    ):

        result = []
        counter = {}

        for doc in docs:

            source = doc.metadata.get("source", "")

            counter[source] = counter.get(source, 0)

            if counter[source] >= max_per_source:
                continue

            counter[source] += 1

            result.append(doc)

        return result

    # ==========================================================
    # RANKING
    # ==========================================================

    def entity_score(
        self,
        query,
        document,
    ):

        return len(
            self.extract_entities(query)
            &
            self.extract_entities(document.page_content)
        )

    def exact_entity_match(
        self,
        query,
        document,
    ):

        q = self.extract_entities(query)
        d = self.extract_entities(document.page_content)

        if not q:
            return 0

        if q == d:
            return 5

        if q.issubset(d):
            return 3

        return 0

    def calculate_score(self, query, document):

        query_words = Counter(
            self.tokenize(query)
        )

        document_words = Counter(
            self.tokenize(document.page_content)
        )

        keyword_score = sum(
            document_words[word] * count
            for word, count in query_words.items()
        )

        entity_score = self.entity_score(
            query,
            document,
        )

        astro_score = self.astro_terms_score(
            query,
            document,
        )

        chart_score = self.chart_score(
            query,
            document,
        )

        exact_score = self.exact_entity_match(
            query,
            document,
        )

        weight = document.metadata.get(
            "weight",
            5,
        )

        authority_score = self.authority_score(
            query,
            document,
        )

        weight = document.metadata.get(
            "weight",
            5,
        )

        return (
            authority_score * 500
            + chart_score * 200
            + entity_score * 120
            + exact_score * 80
            + astro_score * 30
            + keyword_score * 10
            + weight
        )

    def authority_score(
        self,
        query,
        document,
    ):

        entities = self.extract_entities(query)
        score = 0
        text = self.normalize_query(
            document.page_content
        )

        for entity in entities:
            for word in ASTRO_TERMS.get(entity, []):
                if word in text:
                    score += 1

        return score

    def astro_terms_score(
        self,
        query,
        document,
    ):

        score = 0

        document_text = self.normalize_query(
            document.page_content
        )

        for entity in self.extract_entities(query):

            for word in ASTRO_TERMS.get(entity, []):

                if word in document_text:
                    score += 1

        return score

    def sort_documents(
        self,
        query,
        docs,
    ):

        docs.sort(
            key=lambda doc: self.calculate_score(query, doc),
            reverse=True,
        )

        return docs
