/**
 * Astro12AI Mini App - Таро «12 Планет»
 * Строго по ТЗ: расклад > тип трёх карт > колода > перевёрнутые > вопрос > перемешать > вытянуть > толкование ВНУТРИ
 */

// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Глобальное состояние
const AppState = {
    spread: null,           // 'one_card' или 'three_cards'
    threeType: null,        // тип расклада для трёх карт
    deckId: null,           // выбранная колода
    allowReversed: false,   // учитывать перевёрнутые карты
    question: '',           // вопрос пользователя
    drawnCards: [],         // вытянутые карты
    interpretation: '',     // толкование внутри приложения
    isShuffling: false
};

// DOM элементы
const $ = (id) => document.getElementById(id);

// ==================== НАВИГАЦИЯ ====================

function showSection(sectionId) {
    // Скрыть все секции
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.add('hidden');
        sec.classList.remove('active');
    });
    
    // Показать нужную
    const target = $(sectionId);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }
    
    // Скрыть главную кнопку Telegram
    tg.MainButton.hide();
}

function goToMain() {
    // Закрыть Mini App и вернуться в чат
    tg.close();
}

// ==================== ЗАГРУЗКА ДАННЫХ ====================

document.addEventListener('DOMContentLoaded', () => {
    loadDecks();
    setupEventListeners();
    applyTelegramTheme();
});

async function loadDecks() {
    try {
        const response = await fetch('/api/tarot/decks');
        if (!response.ok) throw new Error('Failed to load decks');
        const decks = await response.json();
        renderDecksList(decks);
    } catch (error) {
        console.error('Ошибка загрузки колод:', error);
        // Демо-данные для разработки
        const demoDecks = [
            { deck_id: 'author_deck_146', name: 'Авторская колода 12 Планет', cards_count: 146 },
            { deck_id: 'rider_waite', name: 'Райдер-Уэйт', cards_count: 78 }
        ];
        renderDecksList(demoDecks);
    }
}

function renderDecksList(decks) {
    const container = $('decks-list');
    container.innerHTML = decks
        .filter(deck => deck.cards_count > 0)
        .map(deck => `
            <div class="deck-item" data-deck-id="${deck.deck_id}">
                <strong>${deck.name}</strong>
                <span style="float: right; opacity: 0.7;">${deck.cards_count} карт</span>
            </div>
        `).join('');

    // Обработчики кликов
    container.querySelectorAll('.deck-item').forEach(item => {
        item.addEventListener('click', () => {
            AppState.deckId = item.dataset.deckId;
            showSection('step-reversed');
            tg.HapticFeedback.selectionChanged();
        });
    });
}

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
            const spread = e.target.dataset.spread;
            AppState.spread = spread;
            
            if (spread === 'three_cards') {
                showSection('step-three-type');
            } else {
                showSection('step-deck');
            }
            tg.HapticFeedback.selectionChanged();
        });
    });

    // Выбор типа трёх карт
    document.querySelectorAll('[data-three-type]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            AppState.threeType = e.target.dataset.threeType;
            showSection('step-deck');
            tg.HapticFeedback.selectionChanged();
        });
    });

    // Выбор перевёрнутых карт
    document.querySelectorAll('[data-reversed]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            AppState.allowReversed = e.target.dataset.reversed === 'yes';
            showSection('step-question');
            tg.HapticFeedback.selectionChanged();
        });
    });

    // Подтверждение вопроса
    $('confirm-question').addEventListener('click', () => {
        AppState.question = $('user-question').value.trim();
        showSection('step-shuffle');
        resetShuffleScreen();
    });

    // Перемешивание
    $('shuffle-btn').addEventListener('click', shuffleDeck);

    // Вытягивание карт
    $('draw-cards-btn').addEventListener('click', drawCards);

    // Отправка в бот
    $('send-to-bot-btn').addEventListener('click', sendToBot);

    // Новый расклад
    $('retry-btn').addEventListener('click', () => {
        resetAppState();
        showSection('step-spread');
    });
}

// ==================== ЛОГИКА ТАРО ====================

function resetShuffleScreen() {
    $('deck-visual').classList.remove('shuffling');
    $('shuffle-btn').classList.remove('hidden');
    $('draw-cards-btn').classList.add('hidden');
}

async function shuffleDeck() {
    if (AppState.isShuffling) return;
    
    AppState.isShuffling = true;
    $('deck-visual').classList.add('shuffling');
    tg.HapticFeedback.impactOccurred('light');
    
    await sleep(1500);
    
    AppState.isShuffling = false;
    $('deck-visual').classList.remove('shuffling');
    $('shuffle-btn').classList.add('hidden');
    $('draw-cards-btn').classList.remove('hidden');
    tg.HapticFeedback.notificationOccurred('success');
}

async function drawCards() {
    tg.showLoading();
    
    try {
        const count = AppState.spread === 'one_card' ? 1 : 3;
        
        // Запрос к API для вытягивания карт
        const response = await fetch('/api/tarot/draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: AppState.deckId,
                count: count,
                allow_reversed: AppState.allowReversed,
                spread_type: AppState.spread,
                three_type: AppState.threeType
            })
        });
        
        if (!response.ok) throw new Error('Failed to draw cards');
        
        const result = await response.json();
        AppState.drawnCards = result.cards;
        AppState.interpretation = result.interpretation || '';
        
        renderResult();
        showSection('step-result');
        tg.hideLoading();
        tg.HapticFeedback.notificationOccurred('success');
        
    } catch (error) {
        console.error('Ошибка вытягивания карт:', error);
        tg.hideLoading();
        
        // Демо-режим для разработки
        AppState.drawnCards = generateDemoCards(count);
        AppState.interpretation = generateDemoInterpretation(AppState.drawnCards);
        renderResult();
        showSection('step-result');
    }
}

function renderResult() {
    const container = $('cards-container');
    const positions = getPositions();
    
    container.innerHTML = AppState.drawnCards.map((card, index) => `
        <div class="card-result ${card.reversed ? 'reversed' : ''}" 
             style="animation-delay: ${index * 0.1}s">
            ${card.image_url ? `<img src="${card.image_url}" alt="${card.name}">` : ''}
            <div class="card-name">
                ${card.name}<br>
                ${card.reversed ? '↔️ Перевернута' : ''}
                <small style="opacity: 0.7;">${positions[index] || ''}</small>
            </div>
        </div>
    `).join('');
    
    // Толкование ВНУТРИ приложения
    const interpContainer = $('interpretation');
    if (AppState.interpretation) {
        interpContainer.innerHTML = `
            <div class="interpretation-box">
                <h3>🔮 Толкование:</h3>
                <p>${AppState.interpretation}</p>
            </div>
        `;
    }
}

function getPositions() {
    if (AppState.spread === 'one_card') {
        return ['Карта дня'];
    }
    
    const types = {
        'past_present_future': ['Прошлое', 'Настоящее', 'Будущее'],
        'situation_obstacle_advice': ['Ситуация', 'Препятствие', 'Совет'],
        'thoughts_feelings_actions': ['Мысли', 'Чувства', 'Действия']
    };
    
    return types[AppState.threeType] || ['Карта 1', 'Карта 2', 'Карта 3'];
}

function sendToBot() {
    if (AppState.drawnCards.length === 0) {
        tg.showAlert('Сначала вытяните карты!');
        return;
    }

    const data = {
        action: 'tarot_spread',
        spread_type: AppState.spread,
        three_type: AppState.threeType,
        deck_id: AppState.deckId,
        allow_reversed: AppState.allowReversed,
        question: AppState.question,
        cards: AppState.drawnCards,
        interpretation: AppState.interpretation,
        timestamp: Date.now()
    };

    tg.sendData(JSON.stringify(data));
    
    tg.showPopup({
        title: '✅ Отправлено!',
        message: 'Данные расклада отправлены боту.',
        buttons: [{ type: 'ok' }]
    });
}

// ==================== УТИЛИТЫ ====================

function resetAppState() {
    AppState.spread = null;
    AppState.threeType = null;
    AppState.deckId = null;
    AppState.allowReversed = false;
    AppState.question = '';
    AppState.drawnCards = [];
    AppState.interpretation = '';
    $('user-question').value = '';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Демо-данные для разработки (если API недоступно)
function generateDemoCards(count) {
    const demoCards = [
        { name: 'Шут', reversed: false, image_url: '' },
        { name: 'Маг', reversed: false, image_url: '' },
        { name: 'Жрица', reversed: true, image_url: '' },
        { name: 'Императрица', reversed: false, image_url: '' },
        { name: 'Император', reversed: false, image_url: '' }
    ];
    
    const result = [];
    for (let i = 0; i < count; i++) {
        const card = demoCards[Math.floor(Math.random() * demoCards.length)];
        result.push({ ...card });
    }
    return result;
}

function generateDemoInterpretation(cards) {
    const interpretations = [
        'Карты указывают на важные перемены в вашей жизни. Обратите внимание на внутренние сигналы.',
        'Сейчас благоприятное время для новых начинаний. Доверяйте своей интуиции.',
        'Вам стоит проявить осторожность в принятии решений. Взвесьте все за и против.'
    ];
    return interpretations[Math.floor(Math.random() * interpretations.length)];
}

// Экспорт для отладки
window.Astro12AI = { AppState, showSection, goToMain };
