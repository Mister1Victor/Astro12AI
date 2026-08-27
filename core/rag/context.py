"""Статистика контекста RAG — всегда возвращает str."""
from typing import Any


def context_statistics(context_docs: Any) -> str:
    """
    Безопасная статистика контекста RAG.
    Принимает что угодно (list Document, dict, None) и всегда возвращает str.
    """
    if not context_docs:
        return "Контекст пуст"

    # Если это список Document-ов (стандартный RAG)
    if isinstance(context_docs, (list, tuple)):
        try:
            total_chars = 0
            sources = set()
            for doc in context_docs:
                content = getattr(doc, "page_content", "") or getattr(
                    doc, "content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                meta = getattr(doc, "metadata", {}) or {}
                if isinstance(meta, dict) and "source" in meta:
                    sources.add(meta["source"])
            src_info = f"\nИсточники: {', '.join(sorted(sources))}" if sources else ""
            return (
                f"Всего документов: {len(context_docs)}\n"
                f"Всего символов: {total_chars}{src_info}"
            )
        except Exception as e:
            return f"Контекст получен (нестандартный формат): {e}"

    # Если это dict (fallback или кастомный формат)
    if isinstance(context_docs, dict):
        try:
            return f"Контекст-dict: {len(context_docs)} ключей → {list(context_docs.keys())[:5]}"
        except Exception:
            return f"Контекст-dict (неиндексируемый)"

    # Всё остальное
    return f"Контекст типа {type(context_docs).__name__}, размер ~{len(str(context_docs))} символов"
