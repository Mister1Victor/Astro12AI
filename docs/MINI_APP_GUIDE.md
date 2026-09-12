# Astro12AI — Модульная архитектура и Mini App

## 📁 Структура проекта (обновлённая)

```
/workspace/
├── main.py                    # Точка входа (теперь лёгкий, делегирует модулям)
├── handlers/
│   ├── __init__.py
│   ├── astrology.py           # Обработка астрологических запросов
│   └── tarot.py               # Обработка Tarot-запросов
├── services/
│   ├── __init__.py
│   └── web_server.py          # Веб-сервер для Mini App + API
├── keyboards/
│   ├── __init__.py
│   └── mini_app.py            # Клавиатуры с кнопками Mini App
├── static/                    # Файлы Mini App
│   ├── index.html             # Главная страница Mini App
│   ├── css/
│   │   └── mini-app.css       # Стили Mini App
│   └── js/
│       └── mini-app.js        # Логика Mini App
├── core/                      # Ядро (RAG, LLM, Tarot)
├── backend/                   # Конфигурация, логирование, валидация
└── docs/                      # Документация
```

---

## 🎯 Гибридная схема: Чат-бот + Mini App

### 1. **Чат-бот — это «Сердце» (80% проекта)**
- ИИ-агент отвечает внутри обычного чата Telegram
- Все интерпретации приходят текстом в диалог
- Пользователь получает ответы в привычном формате

### 2. **Mini App — это удобный пульт ввода (20% проекта)**
- Интерактивная клавиатура для отправки данных в бота
- **Для Таро**: визуальная колода, свайп карт, анимация
- **Для Астрологии**: форма выбора планет, знаков, аспектов

---

## 🚀 Как это работает

### Сценарий Таро через Mini App:

1. Пользователь нажимает кнопку `✨ Интерактивный расклад` в боте
2. Открывается Mini App с красивой визуальной колодой
3. Пользователь выбирает расклад (1 карта, 3 карты, Кельтский крест...)
4. Выбирает колоду из списка
5. Нажимает `🔀 Перемешать` → видит анимацию
6. Нажимает `✨ Вытянуть карты` → карты «переворачиваются»
7. Нажимает `✅ Отправить в бот` → данные улетают в чат
8. **Бот получает массив карт** и генерирует ИИ-интерпретацию в приложении

### Сценарий Астрологии через Mini App:

1. Пользователь открывает Mini App для астрологии
2. Заполняет форму:
   - Планета 1 + Знак
   - Тип аспекта (соединение, трин, квадрат...)
   - Планета 2 + Знак
3. Нажимает `✅ Отправить в бот`
4. **Бот получает структурированный запрос** и возвращает интерпретацию в приложение
5. Отображает красиво в Mini App.
6. На каждом этапе присутствуют кнопки "назад" и "основное меню" для возврата или выхода в начало. 

---

## 🔧 Технические детали

### Интеграция Mini App с ботом:

```python
# В main.py или отдельном модуле handlers/mini_app.py
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    """Обработка данных от Mini App."""
    data = json.loads(message.web_app_data.data)
    
    if data.get('action') == 'tarot_spread':
        # Получаем данные расклада
        spread_type = data['spread_type']
        deck_id = data['deck_id']
        cards = data['cards']
        
        # Запускаем интерпретацию как обычно
        await process_tarot_spread(message, spread_type, deck_id, cards)
    
    elif data.get('action') == 'astrology_aspect':
        query = data['query']
        await process_astro_request(message, query, rag_chain, astro_retriever, bot)
```

### Кнопка запуска Mini App в главном меню:

```python
from aiogram.types import WebAppInfo

def main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎴 Таро", callback_data="menu_tarot")
    kb.button(text="🪐 Астрология 12", callback_data="menu_astro")
    kb.button(
        text="✨ Интерактивный расклад",
        web_app=WebAppInfo(url="https://your-domain.com/webapp")
    )
    kb.adjust(2, 1)
    return kb.as_markup()
```

---

## 📋 Следующие шаги

### 1. Немедленно (критические ошибки исправлены ✅):
- [x] Удалено дублирование функции `_is_school_deck`
- [x] Исправлено использование `send_chat_action` для aiogram 3.x
- [x] Созданы модули `handlers/astrology.py` и `handlers/tarot.py`

### 2. Архитектурные улучшения (выполнено ✅):
- [x] Разделение `main.py` на модули
- [x] Создан веб-сервер для Mini App (`services/web_server.py`)
- [x] Создан интерфейс Mini App (`static/index.html`, `mini-app.css`, `mini-app.js`)
- [x] Добавлены клавиатуры для Mini App (`keyboards/mini_app.py`)

### 3. Дальнейшая оптимизация (рекомендации):
- [ ] Подключить реальный `TarotService` к API `/api/tarot/draw`
- [ ] Настроить HTTPS домен для Mini App (требуется для Telegram)
- [ ] Добавить обработку `WebAppData` в `main.py`
- [ ] Внедрить кэширование RAG-контекста
- [ ] Добавить метрики (Prometheus/Grafana)
- [ ] Настроить CI/CD pipeline

---

## 🌐 Развёртывание Mini App

### Требования:
1. **HTTPS домен** (обязательно для Telegram WebApp)
   - Можно использовать: Vercel, Netlify, Render, Heroku
   - Или свой сервер с SSL-сертификатом (Let's Encrypt)

2. **Настройка в @BotFather**:
   ```
   /newapp → выбрать бота → указать URL → получить short_name
   ```

3. **Кнопка в боте**:
   ```python
   from aiogram.types import WebAppInfo
   
   kb.button(
       text="🔮 Открыть Таро",
       web_app=WebAppInfo(url="https://your-domain.com/webapp")
   )
   ```

---

## 📊 Преимущества гибридной схемы

| Критерий | Чат-бот | Mini App | Гибрид |
|----------|---------|----------|--------|
| UX ввод данных | ❌ Текст/кнопки | ✅ Визуально | ✅ Лучшее |
| Интерпретация ИИ | ✅ В чате | ❌ Нет | ✅ В чате |
| Анимации | ❌ Ограничено | ✅ Полные | ✅ Есть |
| Разработка | ✅ Быстро | ⏳ Дольше | ✅ Баланс |
| Удержание | ✅ Высокое | ✅ Высокое | ✅ Максимум |

---

## 🎨 Дизайн Mini App

- **Тёмная тема** по умолчанию (астрологическая атмосфера)
- **Градиенты** и тени для глубины
- **Анимации** перемешивания и переворота карт
- **Haptic feedback** через Telegram API
- **Адаптивность** под все экраны мобильных

---

## 📞 Контакты и поддержка

Проект: **Astro12AI**  
Школа Астрологии **«12 Планет»**  
Автор: Виктор Слободнюк
