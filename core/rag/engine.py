import re

from collections import Counter
from collections import OrderedDict
from langchain_community.retrievers import BM25Retriever
from core.knowledge.weights import get_document_weight


class AstroRetriever:

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

    """
        Поисковый движок Astro12AI.

        Сейчас используется BM25.
        В дальнейшем сюда будет перенесён весь интеллектуальный поиск,
        не меняя main.py.
        """

    def __init__(self, documents, k=8):

        self.documents = documents

        # Назначаем вес каждому документу
        for doc in self.documents:

            source = doc.metadata.get("source", "")

            filename = source.split("/")[-1].split("\\")[-1]

            doc.metadata["weight"] = get_document_weight(filename)

        self.retriever = BM25Retriever.from_documents(self.documents)
        self.retriever.k = k

    def search(self, query):
        """
        Полноценный поиск Astro12AI.
        """
        query = self.normalize_query(query)
        docs = self.retriever.invoke(query)
        docs = self.remove_duplicates(docs)
        docs = self.filter_short_documents(docs)
        docs = self.limit_same_source(docs)
        docs = self.sort_by_weight(
            docs,
            query,
        )
        return docs

    def limit_same_source(self, docs, max_per_source=2):

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

    def get_retriever(self):
        """
        Пока возвращаем BM25Retriever
        для совместимости с LangChain.
        """

        return self.retriever

    def stats(self):

        return {
            "documents": len(self.documents),
            "k": self.retriever.k,
        }

    def remove_duplicates(self, docs):
        """
        Удаляет одинаковые куски текста.
        """

        unique = OrderedDict()

        for doc in docs:

            text = doc.page_content.strip()

            if text not in unique:
                unique[text] = doc

        return list(unique.values())

    def filter_short_documents(self, docs, min_chars=350):
        """
        Убирает слишком короткие куски.
        """

        result = []

        for doc in docs:

            if len(doc.page_content) >= min_chars:
                result.append(doc)

        return result

    def sort_by_weight(
        self,
        docs,
        query,
    ):

        docs.sort(
            key=lambda doc:
                self.calculate_score(
                    query,
                    doc,
                ),
            reverse=True,
        )

        return docs

    def normalize_query(self, query: str):

        query = query.lower()
        query = re.sub(r"[^\w\s]", " ", query)

        for old, new in self.REPLACE.items():
            query = query.replace(old, new)
            query = re.sub(r"\s+", " ", query)
        return query.strip()

    def tokenize(self, text: str):

        text = self.normalize_query(text)

        return [word for word in text.split() if len(word) > 2]

    def calculate_score(
        self,
        query,
        document,
    ):

        query_words = Counter(self.tokenize(query))

        document_words = Counter(self.tokenize(document.page_content))

        score = 0

        for word, count in query_words.items():

            score += document_words[word] * count

        score *= document.metadata.get(
            "weight",
            5,
        )

        return score
