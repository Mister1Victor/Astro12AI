/**
 * Astro12AI Mini App - Логика работы
 * Интеграция с Telegram WebApp API
 */

// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Глобальное состояние приложения
const AppState = {
    currentSpread: null,
    threeCardType: null,
    selectedDeck: null,
    useReversed: true,
    question: '',
    drawnCards: [],
    decks: [],
    isShuffling: false,
    interpretation: null
};

// Конфигурация раскладов
const SPREAD_CONFIGS = {
    one: { name: 'Одна карта', count: 1, positions: ['Карта дня'] },
    three: { 
        name: 'Три карты', 
        count: 3, 
        positions: {
            'past-present-future': ['Прошлое', 'Настоящее', 'Будущее'],
            'thoughts-feelings-actions': ['Мысли', 'Чувства', 'Действия'],
            'plus-minus-result': ['Плюс', 'Минус', 'Итог']
        }
    },
    choice: { 
        name: 'Выбор пути', 
        count: 7, 
        positions: ['Вариант 1: Достоинство', 'Вариант 1: Недостаток', 'Вариант 1: Исход',
                    'Вариант 2: Достоинство', 'Вариант 2: Недостаток', 'Вариант 2: Исход',
                    'Совет']
    },
    celtic: { 
        name: 'Кельтский крест', 
        count: 10, 
        positions: ['Суть ситуации', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
                    'Ближайшее будущее', 'Я', 'Окружение', 'Надежды и страхи', 'Итог']
    }
};

// DOM элементы
const elements = {
    spreadSelection: document.getElementById('spread-selection'),
    threeCardTypeSelection: document.getElementById('three-card-type-selection'),
    deckSelection: document.getElementById('deck-selection'),
    reversedSetting: document.getElementById('reversed-setting'),
    questionInput: document.getElementById('question-input'),
    shuffleScreen: document.getElementById('shuffle-screen'),
    resultScreen: document.getElementById('result-screen'),
    interpretationScreen: document.getElementById('interpretation-screen'),
    astrologyInput: document.getElementById('astrology-input'),
    decksList: document.getElementById('decks-list'),
    cardsResult: document.getElementById('cards-result'),
    interpretationContent: document.getElementById('interpretation-content'),
    deckVisual: document.getElementById('deck-visual'),
    shuffleTitle: document.getElementById('shuffle-title'),
    questionText: document.getElementById('question-text')
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
        const response = await fetch('/api/tarot/decks');
        if (!response.ok) throw new Error('Failed to load decks');
        AppState.decks = await response.json();
        renderDecksList();
    } catch (error) {
        console.error('Ошибка загрузки колод:', error);
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
            <button class="deck-item" data-deck-id="${deck.deck_id}">
                <strong>${deck.name}</strong>
                <span class="deck-count">${deck.cards_count} карт</span>
            </button>
        `).join('');

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

    // Выбор типа трёхкарточного расклада
    document.querySelectorAll('[data-three-type]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const threeType = e.target.dataset.threeType;
            selectThreeCardType(threeType);
        });
    });

    // Настройка перевёрнутых карт
    document.querySelectorAll('[data-reversed]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const useReversed = e.target.dataset.reversed === 'yes';
            setReversedSetting(useReversed);
        });
    });

    // Кнопка "Продолжить" после ввода вопроса
    document.getElementById('continue-to-shuffle').addEventListener('click', () => {
        const question = elements.questionText.value.trim();
        if (question.length < 5) {
            tg.showAlert('Пожалуйста, опишите вопрос подробнее (минимум 5 символов)');
            return;
        }
        AppState.question = question;
        showSection('shuffle-screen');
        resetDeckVisual();
    });

    // Кнопка "Назад" из различных секций
    document.getElementById('back-to-spread-from-three').addEventListener('click', () => showSection('spread-selection'));
    document.getElementById('back-to-spread').addEventListener('click', () => {
        if (AppState.currentSpread === 'three') {
            showSection('three-card-type-selection');
        } else {
            showSection('spread-selection');
        }
    });
    document.getElementById('back-to-deck-from-reversed').addEventListener('click', () => showSection('deck-selection'));
    document.getElementById('back-to-reversed-from-question').addEventListener('click', () => showSection('reversed-setting'));
    document.getElementById('back-to-question-from-shuffle').addEventListener('click', () => showSection('question-input'));
    document.getElementById('back-to-shuffle-from-result').addEventListener('click', () => showSection('shuffle-screen'));
    document.getElementById('back-to-result-from-interp').addEventListener('click', () => showSection('result-screen'));

    // Кнопки "Основное меню"
    document.getElementById('main-menu-from-spread').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-three').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-deck').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-reversed').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-question').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-shuffle').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-result').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-interp').addEventListener('click', sendToMainMenu);
    document.getElementById('main-menu-from-astro').addEventListener('click', sendToMainMenu);

    // Перемешивание колоды
    document.getElementById('shuffle-btn').addEventListener('click', shuffleDeck);

    // Вытягивание карт
    document.getElementById('draw-cards-btn').addEventListener('click', drawCards);

    // Получение толкования
    document.getElementById('get-interpretation').addEventListener('click', getInterpretation);

    // Повторный расклад
    document.getElementById('retry-spread').addEventListener('click', () => {
        AppState.drawnCards = [];
        showSection('shuffle-screen');
        resetDeckVisual();
    });

    // Новый расклад
    document.getElementById('new-spread-from-interp').addEventListener('click', () => {
        AppState.drawnCards = [];
        AppState.interpretation = null;
        AppState.question = '';
        showSection('spread-selection');
    });

    // Форма астрологии
    document.getElementById('astrology-form').addEventListener('submit', handleAstrologySubmit);
}

// ==================== ЛОГИКА ТАРО ====================
function selectSpread(spreadType) {
    AppState.currentSpread = spreadType;
    
    if (spreadType === 'three') {
        showSection('three-card-type-selection');
    } else {
        const config = SPREAD_CONFIGS[spreadType];
        elements.shuffleTitle.textContent = `Расклад: ${config.name}`;
        showSection('deck-selection');
    }
}

function selectThreeCardType(threeType) {
    AppState.threeCardType = threeType;
    const config = SPREAD_CONFIGS.three;
    elements.shuffleTitle.textContent = `Расклад: ${config.name}`;
    showSection('deck-selection');
}

function selectDeck(deckId) {
    AppState.selectedDeck = deckId;
    showSection('reversed-setting');
}

function setReversedSetting(useReversed) {
    AppState.useReversed = useReversed;
    showSection('question-input');
    elements.questionText.value = AppState.question || '';
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
    
    await sleep(1500);
    
    AppState.isShuffling = false;
    elements.deckVisual.classList.remove('shuffling');
    document.getElementById('shuffle-btn').classList.add('hidden');
    document.getElementById('draw-cards-btn').classList.remove('hidden');
    
    tg.HapticFeedback.notificationOccurred('success');
}

async function drawCards() {
    const config = SPREAD_CONFIGS[AppState.currentSpread];
    if (!config) return;

    tg.showLoading();

    try {
        const positions = AppState.currentSpread === 'three' 
            ? config.positions[AppState.threeCardType]
            : config.positions;

        const response = await fetch('/api/tarot/draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: AppState.selectedDeck,
                count: config.count,
                use_reversed: AppState.useReversed,
                spread_type: AppState.currentSpread
            })
        });

        if (!response.ok) throw new Error('Failed to draw cards');
        
        const result = await response.json();
        AppState.drawnCards = result.cards;
        
        renderCardsResult(AppState.drawnCards, positions);
        showSection('result-screen');
        
        tg.hideLoading();
        tg.HapticFeedback.notificationOccurred('success');
        
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
            ${card.image_url ? `<img src="${card.image_url}" alt="${card.name}">` : '<div class="card-placeholder">🎴</div>'}
            <div class="card-name">
                ${card.name}<br>
                ${card.reversed ? '🔻' : '✅'}
            </div>
            <div class="card-pos">${positions[index] || ''}</div>
        </div>
    `).join('');
}

async function getInterpretation() {
    if (AppState.drawnCards.length === 0) {
        tg.showAlert('Сначала вытяните карты!');
        return;
    }

    tg.showLoading();
    tg.HapticFeedback.notificationOccurred('success');

    try {
        const positions = AppState.currentSpread === 'three'
            ? SPREAD_CONFIGS.three.positions[AppState.threeCardType]
            : SPREAD_CONFIGS[AppState.currentSpread].positions;

        const response = await fetch('/api/tarot/interpret', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: AppState.selectedDeck,
                spread_type: AppState.currentSpread,
                three_card_type: AppState.threeCardType,
                question: AppState.question,
                cards: AppState.drawnCards,
                positions: positions,
                use_reversed: AppState.useReversed
            })
        });

        if (!response.ok) throw new Error('Failed to get interpretation');
        
        const result = await response.json();
        AppState.interpretation = result.interpretation;
        
        renderInterpretation(result.interpretation);
        showSection('interpretation-screen');
        
        tg.hideLoading();
        
    } catch (error) {
        console.error('Ошибка получения толкования:', error);
        tg.hideLoading();
        tg.showAlert('Не удалось получить толкование. Попробуйте ещё раз.');
        tg.HapticFeedback.notificationOccurred('error');
    }
}

function renderInterpretation(interpretation) {
    // Форматируем текст с переносами строк
    const formatted = interpretation
        .split('\n')
        .map(line => line.trim())
        .filter(line => line)
        .map(line => `<p>${line}</p>`)
        .join('');
    
    elements.interpretationContent.innerHTML = formatted;
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

    if (!formData.planet1 || !formData.sign1 || !formData.aspectType ||
        !formData.planet2 || !formData.sign2) {
        tg.showAlert('Заполните все поля!');
        return;
    }

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
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.add('hidden');
    });

    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    tg.MainButton.hide();
}

function sendToMainMenu() {
    const data = {
        action: 'main_menu',
        timestamp: Date.now()
    };
    tg.sendData(JSON.stringify(data));
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Экспорт для использования в других модулях
window.Astro12AI = {
    AppState,
    SPREAD_CONFIGS,
    showSection
};