# Архитектура Astro12AI

**Версия:** 2.0.8

## Поток запроса (реальный код)

```
Пользователь (Telegram)
        │
        ▼
main.py  ── парсинг ZET-лога / текста вопроса
        │
        ▼
AstroRetriever.search(query)        core/rag/engine.py
        │
        ├─ expand_query()           нормализация + сущности + ключевые слова ASTRO_TERMS
        ├─ BM25Retriever.invoke()   → топ-10 документов
        ├─ remove_duplicates()
        ├─ filter_short_documents()  min 350 символов
        ├─ filter_by_entities()      ≥ половины сущностей запроса в документе
        ├─ limit_same_source()       ≤ 2 документов на источник
        ├─ force_school_definition() ровно 1 сущность → ≥3 совпадений терминов Школы
        ├─ FORBIDDEN-фильтр          удаление документов с запрещёнными словами
        ├─ inject_context_blocks()   AUTHOR_DEFINITIONS + ASTRO_TERMS в начало 1-го документа
        │                            (или fallback-документ, если BM25 ничего не нашёл)
        │
        ▼
LLM (Groq / OpenRouter / Gemini)    core/llm/model.py
        │   контекст: SYSTEM_PROMPT + найденные документы
        ▼
Ответ пользователю в Telegram
```

## Источник истины — Школа Слободнюка

Все определения берутся **только** из `core/knowledge/weights.py`:

| Блок | Назначение | Приоритет |
|------|-----------|-----------|
| `AUTHOR_DEFINITIONS` | Абсолютная истина: планеты, дома, аспекты, лунные дни. Инжектируется в начало контекста. Содержит явные запреты слов. | 1 |
| `ASTRO_TERMS` | Ключевые слова знаков и домов. Расширение запроса + инжекция после определений. | 2 |
| `DOCUMENT_WEIGHTS` | Веса Word-файлов базы знаний (приоритет источников). | — |
| `FORBIDDEN` | Чёрный список общеастрологических слов по планетам. Документы с ними удаляются. | — |

## Источники знаний (Word-файлы)

- `knowledge_base/Astrobook_Victor_Slobodniuk.docx`
- `knowledge_base/АстроКурс Виктор Слободнюк.docx`
- `knowledge_base/Знаки Зодиака.docx`

## Ядро изолировано

`core/` **не зависит** от Telegram. Клиенты (бот, будущий FastAPI, Android) обращаются к `AstroRetriever` и `create_llm()`. Вся логика поиска — в `core/rag/engine.py`.

## Таро-модуль (отдельный скрипт)

`tarot_chart.py` — автономный генератор PNG (matplotlib). Не связан с основным RAG-пайплайном. Результат — в `output/`.
