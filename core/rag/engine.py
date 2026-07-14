from langchain_community.retrievers import BM25Retriever


class AstroRetriever:

    def __init__(self, documents, k=4):
        self.retriever = BM25Retriever.from_documents(documents)
        self.retriever.k = k

    def search(self, query: str):
        return self.retriever.invoke(query)