import os

from core.knowledge.weights import get_document_weight
from core.knowledge.cache import load_cache, save_cache
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_knowledge_base(folder_path="knowledge_base"):
    cached = load_cache()

    if cached is not None:
        print("⚡ Загружена база знаний из кэша.")
        return cached

    split_docs = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,         # ← не больше 1000 для астрологии
        chunk_overlap=100,       # ← перекрытие 10-15%
        separators=["\n\n", "\n", ". ", " "]
    )

    if not os.path.exists(folder_path):
        raise FileNotFoundError(
            f"Папка '{folder_path}' не найдена."
        )

    files = os.listdir(folder_path)

    print(f"Загрузка базы знаний: {files}")

    for file in files:

        if file.startswith(".") or file.startswith("~$"):
            continue

        path = os.path.join(folder_path, file)

        try:

            if file.endswith(".pdf"):

                loader = PyPDFLoader(path)

                for page in loader.lazy_load():
                    page.metadata["source"] = file
                    doc.metadata["weight"] = get_document_weight(file)
                    split_docs.extend(
                        splitter.split_documents([page])
                    )

                print(f"PDF: {file}")

            elif file.endswith(".docx"):

                loader = Docx2txtLoader(path)

                for doc in loader.lazy_load():
                    doc.metadata["source"] = file
                    doc.metadata["weight"] = get_document_weight(file)
                    split_docs.extend(
                        splitter.split_documents([doc])
                    )

                print(f"DOCX: {file}")

        except Exception as e:

            print(e)

    if not split_docs:
        raise RuntimeError(
            "База знаний пустая."
        )
    save_cache(split_docs)

    return split_docs
