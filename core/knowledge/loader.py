import os

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_knowledge_base(folder_path="knowledge_base"):

    split_docs = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
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
                    split_docs.extend(
                        splitter.split_documents([page])
                    )

                print(f"PDF: {file}")

            elif file.endswith(".docx"):

                loader = Docx2txtLoader(path)

                for doc in loader.lazy_load():
                    doc.metadata["source"] = file
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

    return split_docs