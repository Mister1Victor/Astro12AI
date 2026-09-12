// static/js/mini-app.js
// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Глобальное состояние приложения
const state = {
    spreadType: null, // 'one', 'three', 'choice', 'celtic'
    threeCardType: null, // 'past_present_future', 'thoughts_feelings_actions', 'plus_minus_result'
    deckId: null,
    useReversed: false,
    question: '',
    cards: [],
    interpretation: ''
};

// Конфигурация колод
const decks = [
    { id: 'school_12planets', name: 'Авторская колода Школы «12 Планет»', count: 78 },
    { id: 'oracle_12planets', name: 'Оракул «12 Планет»', count: 146 },
    { id: 'rider_waite', name: 'Таро Райдера-Уэйта', count: 78 },
    { id: 'thoth', name: 'Таро Тота (Алистер Кроули)', count: 78 }
];

// Ссылки на секции (экраны)
const sections = {
    spread: document.getElementById('spread-selection'),
    threeType: document.getElementById('three-card-type-selection'),
    deck: document.getElementById('deck-selection'),
    reversed: document.getElementById('reversed-setting'),
    question: document.getElementById('question-input'),
    shuffle: document.getElementById('shuffle-screen'),
    result: document.getElementById('result-screen'),
    interpretation: document.getElementById('interpretation-screen'),
    astrology: document.getElementById('astrology-input')
};

// Функция переключения экранов
function showSection(sectionName) {
    // Скрываем все секции
    Object.values(sections).forEach(section => {
        if (section) section.classList.add('hidden');
    });
    
    // Показываем нужную
    const targetSection = sections[sectionName];
    if (targetSection) {
        targetSection.classList.remove('hidden');
        // Прокрутка вверх
        window.scrollTo(0, 0);
    } else {
        console.error(`Секция ${sectionName} не найдена!`);
    }
}

// Навигация
function goBack() {
    if (!sections.interpretation.classList.contains('hidden')) {
        showSection('result');
    } else if (!sections.result.classList.contains('hidden')) {
        showSection('shuffle');
    } else if (!sections.question.classList.contains('hidden')) {
        showSection('reversed');
    } else if (!sections.reversed.classList.contains('hidden')) {
        showSection('deck');
    } else if (!sections.deck.classList.contains('hidden')) {
        if (state.spreadType === 'three') {
            showSection('threeType');
        } else {
            showSection('spread');
        }
    } else if (!sections.threeType.classList.contains('hidden')) {
        showSection('spread');
    }
    // На экране spread назад не работает (это начало)
}

function goToMain() {
    // Сброс состояния
    state.spreadType = null;
    state.threeCardType = null;
    state.deckId = null;
    state.useReversed = false;
    state.question = '';
    state.cards = [];
    state.interpretation = '';
    
    // Очистка полей ввода
    const questionInput = document.getElementById('question-text');
    if (questionInput) questionInput.value = '';
    
    showSection('spread');
}

// Логика выбора расклада
function selectSpread(type) {
    state.spreadType = type;
    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    
    if (type === 'three') {
        showSection('threeType');
    } else {
        // Для одиночной карты сразу переходим к колоде
        showSection('deck');
    }
}

// Логика выбора типа тройного расклада
function selectThreeType(type) {
    state.threeCardType = type;
    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    showSection('deck');
}

// Логика выбора колоды
function selectDeck(deckId) {
    state.deckId = deckId;
    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    showSection('reversed');
}

// Логика переворотов
function setReversed(use) {
    state.useReversed = use;
    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    showSection('question');
}

// Логика вопроса
function submitQuestion() {
    const input = document.getElementById('question-text');
    if (input && input.value.trim()) {
        state.question = input.value.trim();
        if (tg.HapticFeedback) tg.HapticFeedback.notificationChanged('success');
        showSection('shuffle');
    } else {
        if (tg.HapticFeedback) tg.HapticFeedback.notificationChanged('error');
        if (tg.showAlert) tg.showAlert('Пожалуйста, введите вопрос.');
    }
}

// Перемешивание и вытягивание
let isShuffling = false;
function shuffleDeck() {
    if (isShuffling) return;
    isShuffling = true;
    
    const btn = document.getElementById('shuffle-btn');
    if (btn) {
        btn.textContent = 'Перемешивание...';
        btn.disabled = true;
    }
    
    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    
    // Имитация перемешивания
    setTimeout(() => {
        isShuffling = false;
        if (btn) {
            btn.textContent = '🔀 Перемешать';
            btn.disabled = false;
        }
        drawCards();
    }, 1500);
}

function drawCards() {
    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    
    // Генерация случайных карт (заглушка, потом будет API)
    const count = state.spreadType === 'one' ? 1 : 3;
    const deckInfo = decks.find(d => d.id === state.deckId);
    const maxCard = deckInfo ? deckInfo.count : 78;
    
    state.cards = [];
    for (let i = 0; i < count; i++) {
        const cardNum = Math.floor(Math.random() * maxCard) + 1;
        const isReversed = state.useReversed && Math.random() > 0.5;
        state.cards.push({
            id: cardNum,
            reversed: isReversed,
            name: `Карта ${cardNum}`, // Временное имя
            image: `/static/images/cards/${state.deckId}/${cardNum}.jpg` // Путь к изображению
        });
    }
    
    showSection('result');
    renderCards();
}

function renderCards() {
    const container = document.getElementById('cards-result');
    if (!container) return;
    
    container.innerHTML = '';
    
    state.cards.forEach((card, index) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'tarot-card';
        if (card.reversed) cardEl.classList.add('reversed');
        
        // Заглушка изображения, если нет реального файла
        const imgSrc = card.image; 
        // Для демонстрации используем плейсхолдер, если картинка не загрузится
        cardEl.innerHTML = `
            <div class="card-image">
                <img src="${imgSrc}" alt="Card ${card.id}" onerror="this.src='https://placehold.co/200x350/2a1b3d/FFF?text=Card+${card.id}'">
            </div>
            <div class="card-name">${card.name} ${card.reversed ? '(перевёрнутая)' : ''}</div>
        `;
        container.appendChild(cardEl);
    });
}

// Получение толкования
async function getInterpretation() {
    const btn = document.getElementById('get-interpretation');
    if (btn) {
        btn.textContent = 'Толкуем...';
        btn.disabled = true;
    }
    
    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('heavy');
    
    try {
        // Запрос к API бота
        const response = await fetch('/api/tarot/interpret', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: state.deckId,
                cards: state.cards,
                question: state.question,
                spread_type: state.spreadType,
                three_card_type: state.threeCardType
            })
        });
        
        if (!response.ok) throw new Error('Ошибка сети');
        
        const data = await response.json();
        state.interpretation = data.text || data.result || "Толкование не найдено.";
        
        showSection('interpretation');
        const contentEl = document.getElementById('interpretation-content');
        if (contentEl) contentEl.textContent = state.interpretation;
        
    } catch (error) {
        console.error('Error:', error);
        // Если API нет, показываем заглушку для демонстрации
        state.interpretation = "Демонстрационное толкование: Карты указывают на важные перемены в вашей жизни. Будьте внимательны к знакам судьбы.";
        showSection('interpretation');
        const contentEl = document.getElementById('interpretation-content');
        if (contentEl) contentEl.textContent = state.interpretation;
        
        if (btn) {
            btn.textContent = '🔮 Получить толкование';
            btn.disabled = false;
        }
    }
}

function repeatSpread() {
    state.cards = [];
    state.interpretation = '';
    showSection('shuffle');
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    // Настройка темы Telegram
    if (tg.colorScheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
    
    // Рендер кнопок колод
    const deckContainer = document.getElementById('decks-list');
    if (deckContainer) {
        deckContainer.innerHTML = '';
        decks.forEach(deck => {
            const btn = document.createElement('button');
            btn.className = 'deck-btn';
            btn.innerHTML = `<span class="deck-name">${deck.name}</span><span class="deck-count">${deck.count} карт</span>`;
            btn.onclick = () => selectDeck(deck.id);
            deckContainer.appendChild(btn);
        });
    }
    
    // Обработчики кнопок расклада
    document.querySelectorAll('[data-spread]').forEach(btn => {
        btn.addEventListener('click', () => selectSpread(btn.dataset.spread));
    });
    
    // Обработчики кнопок типа тройного расклада
    document.querySelectorAll('[data-three-type]').forEach(btn => {
        btn.addEventListener('click', () => selectThreeType(btn.dataset.threeType));
    });
    
    // Обработчики кнопок переворотов
    document.querySelectorAll('[data-reversed]').forEach(btn => {
        btn.addEventListener('click', () => setReversed(btn.dataset.reversed === 'yes'));
    });
    
    // Обработчик кнопки продолжения
    const continueBtn = document.getElementById('continue-to-shuffle');
    if (continueBtn) {
        continueBtn.addEventListener('click', submitQuestion);
    }
    
    // Обработчики кнопок перемешивания
    const shuffleBtn = document.getElementById('shuffle-btn');
    if (shuffleBtn) {
        shuffleBtn.addEventListener('click', shuffleDeck);
    }
    
    const drawBtn = document.getElementById('draw-cards-btn');
    if (drawBtn) {
        drawBtn.addEventListener('click', drawCards);
    }
    
    // Обработчик получения толкования
    const interpretBtn = document.getElementById('get-interpretation');
    if (interpretBtn) {
        interpretBtn.addEventListener('click', getInterpretation);
    }
    
    // Обработчик повтора расклада
    const retryBtn = document.getElementById('retry-spread');
    if (retryBtn) {
        retryBtn.addEventListener('click', repeatSpread);
    }
    
    // Обработчики навигации "Назад"
    const backButtons = {
        'back-to-spread-from-three': () => showSection('spread'),
        'back-to-spread': () => showSection('spread'),
        'back-to-deck-from-reversed': () => showSection('deck'),
        'back-to-reversed-from-question': () => showSection('reversed'),
        'back-to-question-from-shuffle': () => showSection('question'),
        'back-to-shuffle-from-result': () => showSection('shuffle'),
        'back-to-result-from-interp': () => showSection('result')
    };
    
    Object.entries(backButtons).forEach(([id, handler]) => {
        const btn = document.getElementById(id);
        if (btn) btn.addEventListener('click', handler);
    });
    
    // Обработчики кнопок "Основное меню"
    const menuButtons = [
        'main-menu-from-spread',
        'main-menu-from-three',
        'main-menu-from-deck',
        'main-menu-from-reversed',
        'main-menu-from-question',
        'main-menu-from-shuffle',
        'main-menu-from-result',
        'main-menu-from-interp',
        'main-menu-from-astro'
    ];
    
    menuButtons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.addEventListener('click', goToMain);
    });
    
    // Обработчик нового расклада
    const newSpreadBtn = document.getElementById('new-spread-from-interp');
    if (newSpreadBtn) {
        newSpreadBtn.addEventListener('click', () => {
            state.cards = [];
            state.interpretation = '';
            showSection('shuffle');
        });
    }
    
    // Показать первый экран
    showSection('spread');
});

// Экспорт функций для глобального доступа (если нужно)
window.appActions = {
    selectSpread,
    selectThreeType,
    selectDeck,
    setReversed,
    submitQuestion,
    shuffleDeck,
    drawCards,
    getInterpretation,
    repeatSpread,
    goBack,
    goToMain
};
