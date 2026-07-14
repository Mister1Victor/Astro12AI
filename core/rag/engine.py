from langchain_community.retrievers import BM25Retriever


class AstroRetriever:
    """
    Собственный поисковый движок Astro12AI.

    Пока внутри использует BM25, но вся логика поиска
    будет постепенно переноситься сюда.
    """

    def __init__(self, documents, k=4):
        self.documents = documents

        self.retriever = BM25Retriever.from_documents(documents)
        self.retriever.k = k

    def search(self, query: str):
        """
        Выполняет поиск документов.
        """

        docs = self.retriever.invoke(query)

        docs.sort(
            key=lambda d: d.metadata.get("weight", 5),
            reverse=True
        )

        return docs

    def get_retriever(self):
        """
        Временно возвращает стандартный BM25Retriever.
        Нужно для совместимости с create_retrieval_chain().
        """

        return self.retriever

    def stats(self):
        """
        Информация о поисковом индексе.
        """

        return {
            "documents": len(self.documents),
            "k": self.retriever.k,
        }