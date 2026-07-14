from typing import List


def context_statistics(documents: List):

    total_chars = 0
    total_docs = len(documents)

    sources = set()

    for doc in documents:
        total_chars += len(doc.page_content)

        source = doc.metadata.get("source")

        if source:
            sources.add(source)

    return {
        "documents": total_docs,
        "characters": total_chars,
        "sources": sorted(sources),
    }