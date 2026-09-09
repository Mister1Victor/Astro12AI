/**
 * Astro12AI Mini App - Логика работы
 * Интеграция с Telegram WebApp API
 */

// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand(); // Развернуть на весь экран

// Глобальное состояние приложения
const AppState = {
    currentSpread: null,
    selectedDeck: null,
    drawnCards: [],
    decks: [],
    isShuffling: false
};

// Конфигурация раскладов
// Позиции Кельтского креста (локальная константа)
const CELTIC_CROSS_POSITIONS = [
  'Суть', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
  'Ближайшее будущее', 'Я', 'Окружение', 'Надежды/Страхи', 'Итог'
];

const SPREAD_CONFIGS = {
  one:    { name: 'Одна карта',      count: 1,  positions: ['Карта дня'] },
  three:  { name: 'Три карты',       count: 3,  positions: ['Прошлое', 'Настоящее', 'Будущее'] },
  choice: { name: 'Выбор пути',      count: 7,  positions: ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход', 'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'] },
  celtic: { name: 'Кельтский крест', count: 10, positions: CELTIC_CROSS_POSITIONS }
};

// DOM элементы
const elements = {
    spreadSelection: document.getElementById('spread-selection'),
    deckSelection: document.getElementById('deck-selection'),
    shuffleScreen: document.getElementById('shuffle-screen'),
    resultScreen: document.getElementById('result-screen'),
    astrologyInput: document.getElementById('astrology-input'),
    decksList: document.getElementById('decks-list'),
    cardsResult: document.getElementById('cards-result'),
    deckVisual: document.getElementById('deck-visual'),
    shuffleTitle: document.getElementById('shuffle-title')
};

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

document.addEventListener('DOMContentLoaded', () => {
    loadDecks();
    setupEventListeners();
    applyTelegramTheme();
});

// Загрузка колод с бэкенда
async function loadDecks() {
    try {
        // В продакшене заменить на реальный API endpoint
        const response = await fetch('/api/tarot/decks');
        if (!response.ok) throw new Error('Failed to load decks');
        
        AppState.decks = await response.json();
        renderDecksList();
    } catch (error) {
        console.error('Ошибка загрузки колод:', error);
        // Fallback: демо-данные для разработки
        AppState.decks = [
            { deck_id: 'rider_waite', name: 'Райдер-Уэйт', cards_count: 78 },
            { deck_id: 'thoth', name: 'Таро Тота', cards_count: 78 },
            { deck_id: 'author_deck_146', name: 'Авторская колода 12 Планет', cards_count: 146 }
        ];
        renderDecksList();
    }
}

// Отрисовка списка колод
function renderDecksList() {
    elements.decksList.innerHTML = AppState.decks
        .filter(deck => deck.cards_count > 0)
        .map(deck => `
            <div class="deck-item" data-deck-id="${deck.deck_id}">
                <strong>${deck.name}</strong>
                <span style="float: right; opacity: 0.7;">${deck.cards_count} карт</span>
            </div>
        `).join('');

    // Обработчики кликов по колодам
    document.querySelectorAll('.deck-item').forEach(item => {
        item.addEventListener('click', () => {
            const deckId = item.dataset.deckId;
            selectDeck(deckId);
        });
    });
}

// Применение темы Telegram
function applyTelegramTheme() {
    const root = document.documentElement;
    
    if (tg.themeParams) {
        root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#1a1a2e');
        root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#eaeaea');
        root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#6c5ce7');
        root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
        root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#16213e');
    }
}

// ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

function setupEventListeners() {
    // Выбор расклада
    document.querySelectorAll('[data-spread]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const spreadType = e.target.dataset.spread;
            selectSpread(spreadType);
        });
    });

    // Кнопка "Назад к раскладам"
    document.getElementById('back-to-spread').addEventListener('click', () => {
        showSection('spread-selection');
    });

    // Перемешивание колоды
    document.getElementById('shuffle-btn').addEventListener('click', shuffleDeck);

    // Вытягивание карт
    document.getElementById('draw-cards-btn').addEventListener('click', drawCards);

    // Отправка результата в бот
    document.getElementById('send-to-bot').addEventListener('click', sendToBot);

    // Повторный расклад
    document.getElementById('retry-spread').addEventListener('click', () => {
        showSection('shuffle-screen');
        AppState.drawnCards = [];
    });

    // Форма астрологии
    document.getElementById('astrology-form').addEventListener('submit', handleAstrologySubmit);

    // Настройка главной кнопки Telegram
    tg.MainButton.setText('✅ Отправить в бот');
    tg.MainButton.onClick(sendToBot);
}

// ==================== ЛОГИКА ТАРО ====================

function selectSpread(spreadType) {
    AppState.currentSpread = spreadType;
    const config = SPREAD_CONFIGS[spreadType];
    
    elements.shuffleTitle.textContent = `Расклад: ${config.name}`;
    showSection('deck-selection');
}

function selectDeck(deckId) {
    AppState.selectedDeck = deckId;
    showSection('shuffle-screen');
    resetDeckVisual();
}

function resetDeckVisual() {
    elements.deckVisual.classList.remove('shuffling');
    document.getElementById('draw-cards-btn').classList.add('hidden');
    document.getElementById('shuffle-btn').classList.remove('hidden');
}

async function shuffleDeck() {
    if (AppState.isShuffling) return;
    
    AppState.isShuffling = true;
    elements.deckVisual.classList.add('shuffling');
    
    // Анимация перемешивания (1.5 секунды)
    await sleep(1500);
    
    AppState.isShuffling = false;
    elements.deckVisual.classList.remove('shuffling');
    
    document.getElementById('shuffle-btn').classList.add('hidden');
    document.getElementById('draw-cards-btn').classList.remove('hidden');
    
    // Haptic feedback
    tg.HapticFeedback.notificationOccurred('success');
}

async function drawCards() {
    const config = SPREAD_CONFIGS[AppState.currentSpread];
    if (!config) return;

    // Показываем индикатор загрузки
    tg.showLoading();
    
    try {
        // Запрос к API для вытягивания карт
        const response = await fetch('/api/tarot/draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: AppState.selectedDeck,
                count: config.count,
                spread_type: AppState.currentSpread
            })
        });
        
        if (!response.ok) throw new Error('Failed to draw cards');
        
        const result = await response.json();
        AppState.drawnCards = result.cards;
        
        renderCardsResult(AppState.drawnCards, config.positions);
        
        // Показываем результат
        showSection('result-screen');
        tg.hideLoading();
        tg.HapticFeedback.notificationOccurred('success');
        
        // Показываем главную кнопку Telegram
        tg.MainButton.show();
        
    } catch (error) {
        console.error('Ошибка вытягивания карт:', error);
        tg.hideLoading();
        tg.showAlert('Произошла ошибка при вытягивании карт. Попробуйте ещё раз.');
        tg.HapticFeedback.notificationOccurred('error');
    }
}

function renderCardsResult(cards, positions) {
    elements.cardsResult.innerHTML = cards.map((card, index) => `
        <div class="card-result ${card.reversed ? 'reversed' : ''}" 
             style="animation-delay: ${index * 0.1}s">
            ${card.image_url ? `<img src="${card.image_url}" alt="${card.name}">` : ''}
            <div class="card-name">
                ${card.name}<br>
                ${card.reversed ? '↔️' : ''}
                <small style="opacity: 0.7;">${positions[index] || ''}</small>
            </div>
        </div>
    `).join('');
}

function sendToBot() {
    if (AppState.drawnCards.length === 0) {
        tg.showAlert('Сначала вытяните карты!');
        return;
    }

    const data = {
        action: 'tarot_spread',
        spread_type: AppState.currentSpread,
        deck_id: AppState.selectedDeck,
        cards: AppState.drawnCards,
        timestamp: Date.now()
    };

    // Отправка данных боту через Telegram WebApp
    tg.sendData(JSON.stringify(data));
    
    // Или закрытие окна с данными
    // tg.close();
    
    tg.showPopup({
        title: '✅ Отправлено!',
        message: 'Данные расклада отправлены боту. Ожидайте интерпретацию.',
        buttons: [{ type: 'ok' }]
    });
}

// ==================== ЛОГИКА АСТРОЛОГИИ ====================

function handleAstrologySubmit(e) {
    e.preventDefault();
    
    const formData = {
        planet1: document.getElementById('planet1').value,
        sign1: document.getElementById('sign1').value,
        aspectType: document.getElementById('aspect-type').value,
        planet2: document.getElementById('planet2').value,
        sign2: document.getElementById('sign2').value
    };

    // Валидация
    if (!formData.planet1 || !formData.sign1 || !formData.aspectType || 
        !formData.planet2 || !formData.sign2) {
        tg.showAlert('Заполните все поля!');
        return;
    }

    // Формирование строки запроса для бота
    const aspectNames = {
        conjunction: 'Соединение',
        sextile: 'Секстиль',
        square: 'Квадрат',
        trine: 'Трин',
        opposition: 'Оппозиция',
        quincunx: 'Квиконс'
    };

    const queryText = `${aspectNames[formData.aspectType]} между ${formData.planet1} в ${formData.sign1} и ${formData.planet2} в ${formData.sign2}`;

    const data = {
        action: 'astrology_aspect',
        query: queryText,
        details: formData,
        timestamp: Date.now()
    };

    tg.sendData(JSON.stringify(data));
    
    tg.showPopup({
        title: '🪐 Отправлено!',
        message: 'Данные аспекта отправлены боту. Ожидайте интерпретацию.',
        buttons: [{ type: 'ok' }]
    });
}

// ==================== УТИЛИТЫ ====================

function showSection(sectionId) {
    // Скрываем все секции
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.add('hidden');
    });
    
    // Показываем нужную
    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.remove('hidden');
    }
    
    // Скрываем главную кнопку при переходе между секциями
    tg.MainButton.hide();
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Экспорт для использования в других модулях
window.Astro12AI = {
    AppState,
    SPREAD_CONFIGS,
    sendToBot,
    showSection
};
