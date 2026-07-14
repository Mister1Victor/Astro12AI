DOCUMENT_WEIGHTS = {
    "Astrobook_Victor_Slobodniuk.docx": 10,
    "АстроКурс Виктор Слободнюк.docx": 9,
    "Синастрия_ai.docx": 8,
}


def get_document_weight(filename: str) -> int:
    return DOCUMENT_WEIGHTS.get(filename, 5)