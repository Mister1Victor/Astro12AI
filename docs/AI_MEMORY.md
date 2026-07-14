Паспорт Проекта Astro12AI.

# AI MEMORY

Проект:
Astro12AI

Автор:
Виктор Слободнюк

Назначение

ИИ-консультант Высшей Школы Астрологии "12 Планет".

Главная задача —

не вычисление карты,

а максимально точная интерпретация
авторской базы знаний.

Архитектура

Telegram

↓

Aiogram

↓

AstroRetriever

↓

BM25

↓

Groq

↓

Ответ пользователю

Основные принципы

1.
Минимум новых файлов.

2.
Не ломать main.py без необходимости.

3.
Логика переносится внутрь
core/rag/engine.py

4.
Все улучшения поиска —
в AstroRetriever.

5.
Приоритет —
качество поиска,
а не количество функций.

Текущее состояние

Версия

v0.4.0

Production Stable

Следующая цель

AstroRetriever v2

Интеллектуальное ранжирование
по астрологическим сущностям.

PS D:\Астрология\ ASTRO-KURS_Victor_Slobodniuk\Апликейшн\Astro12AI> tree core /F  
Структура папок тома Новый том
Серийный номер тома: 0C3A-73B9
D:\АСТРОЛОГИЯ\ ASTRO-KURS_VICTOR_SLOBODNIUK\АПЛИКЕЙШН\ASTRO12AI\CORE
├───knowledge
│   │   cache.py
│   │   loader.py
│   │   weights.py
│   │   
│   └───__pycache__
│           cache.cpython-313.pyc
│           loader.cpython-313.pyc
│           weights.cpython-313.pyc
│           
├───llm
│   │   model.py
│   │   
│   └───__pycache__
│           model.cpython-313.pyc
│           
├───prompts
│   │   system_prompt.py
│   │   
│   └───__pycache__
│           system_prompt.cpython-313.pyc
│           
└───rag
    │   classifier.py
    │   context.py
    │   engine.py
    │   search.py
    │   
    └───__pycache__
            context.cpython-313.pyc
            engine.cpython-313.pyc
