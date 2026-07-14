from langchain_community.retrievers import BM25Retriever
from collections import OrderedDict

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

    def search(self, query):

        docs = self.retriever.invoke(query)

        docs = self.remove_duplicates(docs)

        docs = self.filter_short_documents(docs)

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
        
    def remove_duplicates(self, docs):
        """
        Удаляет одинаковые фрагменты.
        """

        unique = OrderedDict()

        for doc in docs:

            text = doc.page_content.strip()

            if text not in unique:
                unique[text] = doc

        return list(unique.values())
    
    def filter_short_documents(self, docs, min_chars=250):
        """
        Удаляет слишком короткие документы.
        """

        result = []

        for doc in docs:

            if len(doc.page_content) >= min_chars:
                result.append(doc)

        return result
    