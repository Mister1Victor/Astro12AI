import re

from collections import Counter, OrderedDict
from langchain_community.retrievers import BM25Retriever

from core.knowledge.weights import get_document_weight


class AstroRetriever:
    """
    Собственный поисковый движок Astro12AI.

    Вся логика поиска постепенно переносится сюда.
    main.py изменять не потребуется.
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
        "1 дом",
        "2 дом",
        "3 дом",
        "4 дом",
        "5 дом",
        "6 дом",
        "7 дом",
        "8 дом",
        "9 дом",
        "10 дом",
        "11 дом",
        "12 дом",
    }

    def __init__(self, documents, k=8):

        self.documents = documents

        for doc in self.documents:

            source = doc.metadata.get("source", "")

            filename = source.split("/")[-1].split("\\")[-1]

            doc.metadata["weight"] = get_document_weight(filename)

        self.retriever = BM25Retriever.from_documents(self.documents)
        self.retriever.k = k

    # =====================================================
    # PUBLIC
    # =====================================================

    def search(self, query):

        query = self.normalize_query(query)

        docs = self.retriever.invoke(query)

        docs = self.remove_duplicates(docs)

        docs = self.filter_short_documents(docs)

        docs = self.filter_by_entities(
            query,
            docs,
        )

        docs = self.limit_same_source(docs)

        docs = self.sort_documents(
            query,
            docs,
        )

        return docs

    def get_retriever(self):
        """
        Пока оставляем совместимость
        с create_retrieval_chain().
        """

        return self.retriever

    def stats(self):

        return {
            "documents": len(self.documents),
            "k": self.retriever.k,
        }

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def normalize_query(self, query):

        query = query.lower()

        query = re.sub(r"[^\w\s]", " ", query)

        for old, new in self.REPLACE.items():
            query = query.replace(old, new)

        query = re.sub(r"\s+", " ", query)

        return query.strip()

    def tokenize(self, text):

        text = self.normalize_query(text)

        return [
            word
            for word in text.split()
            if len(word) > 2
        ]

    # =====================================================
    # ENTITIES
    # =====================================================

    def extract_entities(self, text):

        text = self.normalize_query(text)

        entities = set()

        for planet in self.PLANETS:
            if planet in text:
                entities.add(planet)

        for sign in self.SIGNS:
            if sign in text:
                entities.add(sign)

        for aspect in self.ASPECTS:
            if aspect in text:
                entities.add(aspect)

        for house in self.HOUSES:
            if house in text:
                entities.add(house)

        return entities

    def entity_score(
        self,
        query,
        document,
    ):

        q = self.extract_entities(query)

        d = self.extract_entities(
            document.page_content
        )

        return len(q & d)

    # =====================================================
    # FILTERS
    # =====================================================

    def remove_duplicates(self, docs):

        unique = OrderedDict()

        for doc in docs:

            text = doc.page_content.strip()

            if text not in unique:
                unique[text] = doc

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

        for doc in docs:

            doc_entities = self.extract_entities(
                doc.page_content
            )

            matches = len(
                query_entities & doc_entities
            )

            if matches >= max(
                1,
                len(query_entities) // 2,
            ):
                result.append(doc)

        return result

    def limit_same_source(
        self,
        docs,
        max_per_source=2,
    ):

        counter = {}

        result = []

        for doc in docs:

            source = doc.metadata.get(
                "source",
                "",
            )

            counter[source] = counter.get(
                source,
                0,
            )

            if counter[source] >= max_per_source:
                continue

            counter[source] += 1

            result.append(doc)

        return result

    # =====================================================
    # RANKING
    # =====================================================

    def calculate_score(
        self,
        query,
        document,
    ):

        query_words = Counter(
            self.tokenize(query)
        )

        document_words = Counter(
            self.tokenize(
                document.page_content
            )
        )

        keyword_score = 0

        for word, count in query_words.items():

            keyword_score += (
                document_words[word] * count
            )

        entity_score = self.entity_score(
            query,
            document,
        )

        weight = document.metadata.get(
            "weight",
            5,
        )

        score = (
            entity_score * 100
            + keyword_score * 10
            + weight
        )

        return score

    def sort_documents(
        self,
        query,
        docs,
    ):

        docs.sort(
            key=lambda doc: self.calculate_score(
                query,
                doc,
            ),
            reverse=True,
        )

        return docs
