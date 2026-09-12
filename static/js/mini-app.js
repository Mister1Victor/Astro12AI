/**
 * Astro12AI Mini App — логика.
 * Архитектура: Mini App ТОЛЬКО отправляет данные в бот через tg.sendData().
 * Толкование генерируется ботом в чате (не в WebApp).
 */
(function () {
    'use strict';

    var tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;
    if (tg) { tg.ready(); tg.expand(); if (tg.MainButton) tg.MainButton.hide(); }

    // ---------- Безопасные обёртки для Telegram API ----------
    function safeAlert(msg) {
        if (tg && tg.showAlert) {
            try { tg.showAlert(msg); return; } catch (e) {}
        }
        alert(msg);
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
    const container = $('decks-list');
    
    // Демо-колоды (гарантированно работают)
    const demoDecks = [
        { deck_id: 'author_deck_146', name: 'Авторская колода 12 Планет', cards_count: 146 },
        { deck_id: 'rider_waite', name: 'Райдер-Уэйт', cards_count: 78 }
    ];
    
    try {
        const response = await fetch('/api/tarot/decks');
        if (!response.ok) throw new Error('Failed to load decks');
        const decks = await response.json();
        if (decks && decks.length > 0) {
            renderDecksList(decks);
            return;
        }
    } catch (error) {
        console.log('Используем демо-колоды:', error.message);
    }
    
    // Если API не доступен, используем демо-данные
    renderDecksList(demoDecks);
}

function renderDecksList(decks) {
    const container = $('decks-list');
    container.innerHTML = decks
        .filter(deck => deck.cards_count > 0)
        .map(deck => `
            <div class="deck-item" data-deck-id="${deck.deck_id}">
                <strong class="deck-name">${deck.name}</strong>
                <span class="deck-count">${deck.cards_count} карт</span>
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

    // ---------- Локальные константы ----------
    var CELTIC = ['Суть (сигнификатор)', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
        'Ближайшее будущее', 'Я', 'Окружение', 'Надежды и страхи', 'Итог'];
    var SPREADS = {
        one:    { name: 'Одна карта',      count: 1,  positions: ['Карта дня'] },
        three:  { name: 'Три карты',       count: 3,  positions: ['Прошлое', 'Настоящее', 'Будущее'] },
        choice: { name: 'Выбор пути',      count: 7,  positions: ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход', 'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'] },
        celtic: { name: 'Кельтский крест', count: 10, positions: CELTIC }
    };
    var PLANETS = ['Солнце', 'Луна', 'Меркурий', 'Венера', 'Марс', 'Юпитер',
        'Сатурн', 'Уран', 'Нептун', 'Плутон', 'Эрида', 'Церера'];
    var SIGNS = ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева',
        'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы'];
    var ASPECTS = [
        { id: 'conjunction', name: 'Соединение (0°)' },
        { id: 'sextile',     name: 'Секстиль (60°)' },
        { id: 'square',      name: 'Квадрат (90°)' },
        { id: 'trine',       name: 'Трин (120°)' },
        { id: 'opposition',  name: 'Оппозиция (180°)' },
        { id: 'quincunx',    name: 'Квиконс (150°)' }
    ];
    var FALLBACK_DECKS = [
        { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 },
        { deck_id: 'rider_waite',     name: 'Таро Райдера-Уэйта', cards_count: 78 },
        { deck_id: 'thoth',           name: 'Таро Тота', cards_count: 78 },
        { deck_id: 'author_deck',     name: 'Авторская колода Школы', cards_count: 78 }
    ];

    var State = { screen: 'spread', spread: null, deck: null, drawn: [], decks: [], question: '' };

    function $(id) { return document.getElementById(id); }

    // ---------- Экраны и «назад» ----------
    var SCREENS = ['spread', 'deck', 'question', 'shuffle', 'result', 'astro'];
    var BACK = { deck: 'spread', question: 'deck', shuffle: 'question', result: 'shuffle', astro: 'spread' };

    function showScreen(name) {
        State.screen = name;
        SCREENS.forEach(function (s) {
            var el = $('screen-' + s);
            if (el) el.classList.toggle('hidden', s !== name);
        });
        if (tg && tg.BackButton) {
            if (name === 'spread') tg.BackButton.hide();
            else tg.BackButton.show();
        }
        if (tg && tg.MainButton) tg.MainButton.hide();
    }

    function goBack() {
        var target = BACK[State.screen];
        if (target) showScreen(target);
    }

    // ---------- 🏠 Основное меню ----------
    function sendToMainMenu() {
        // Просто закрываем WebApp — пользователь возвращается в чат с ботом
        if (tg && tg.close) {
            tg.close();
        } else {
            window.history.back();
        }
    }

    // ---------- Колоды ----------
    function renderDecks() {
        var box = $('deck-list');
        if (!box) return;
        box.innerHTML = '';
        State.decks.forEach(function (d) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'deck-item';
            b.textContent = d.name + ' · ' + d.cards_count;
            b.addEventListener('click', function () {
                State.deck = d;
                resetShuffle();
                showScreen('question');
                haptic('light');
            });
            box.appendChild(b);
        });
    }

    function loadDecks() {
        fetch('/api/tarot/decks')
            .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('http ' + r.status)); })
            .then(function (data) {
                State.decks = (Array.isArray(data) && data.length) ? data : FALLBACK_DECKS;
                renderDecks();
            })
            .catch(function () { State.decks = FALLBACK_DECKS; renderDecks(); });
    }

    // ---------- Вопрос ----------
    function submitQuestion() {
        var input = $('question-input');
        var q = input ? input.value.trim() : '';
        if (q.length < 3) {
            safeAlert('Пожалуйста, опишите вопрос подробнее (минимум 3 символа)');
            return;
        }
        State.question = q;
        showScreen('shuffle');
        haptic('light');
    }

    // ---------- Перемешать / вытянуть ----------
    function resetShuffle() {
        State.drawn = [];
        var cfg = SPREADS[State.spread] || SPREADS.one;
        var titleEl = $('shuffle-title');
        if (titleEl) titleEl.textContent = cfg.name + ' — ' + (State.deck ? State.deck.name : '');
        var btnShuffle = $('btn-shuffle');
        var btnDraw = $('btn-draw');
        if (btnShuffle) { btnShuffle.classList.remove('hidden'); btnShuffle.disabled = false; }
        if (btnDraw) btnDraw.classList.add('hidden');
    }

    function shuffle() {
        var btn = $('btn-shuffle');
        if (btn) btn.disabled = true;
        haptic('light');
        var v = $('deck-visual');
        if (v) v.classList.add('shuffling');
        setTimeout(function () {
            if (v) v.classList.remove('shuffling');
            var btnShuffle = $('btn-shuffle');
            var btnDraw = $('btn-draw');
            if (btnShuffle) btnShuffle.classList.add('hidden');
            if (btnDraw) { btnDraw.classList.remove('hidden'); btnDraw.disabled = false; }
            haptic('medium');
        }, 1200);
    }

    function draw() {
        var cfg = SPREADS[State.spread] || SPREADS.one;
        if (!State.deck) return;
        var btn = $('btn-draw');
        if (btn) btn.disabled = true;
        if (tg && tg.showProgress) tg.showProgress();

        fetch('/api/tarot/draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: State.deck.deck_id,
                count: cfg.count,
                spread_type: State.spread
            })
        })
            .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('http ' + r.status)); })
            .then(function (data) {
                if (!data || !Array.isArray(data.cards) || !data.cards.length) throw new Error('empty');
                State.drawn = data.cards;
                renderResult();
                showScreen('result');
                haptic('medium');
            })
            .catch(function () {
                safeAlert('Сервер недоступен. Повторите попытку через минуту.');
            })
            .then(function () {
                if (tg && tg.hideProgress) tg.hideProgress();
                if (btn) btn.disabled = false;
            });
    }

    function renderResult() {
        var cfg = SPREADS[State.spread] || SPREADS.one;
        var box = $('cards-result');
        if (!box) return;
        box.innerHTML = '';
        State.drawn.forEach(function (c, i) {
            var el = document.createElement('div');
            el.className = 'card-result' + (c.reversed ? ' reversed' : '');
            var img = c.image_url ? '<img src="' + c.image_url + '" alt="">' : '';
            el.innerHTML = img +
                '<div class="card-name">' + (c.name || '') + '</div>' +
                '<div class="card-pos">' + (cfg.positions[i] || ('Позиция ' + (i + 1))) + '</div>' +
                '<div class="card-orient">' + (c.reversed ? '🔻 перевёрнуто' : '✅ прямо') + '</div>';
            box.appendChild(el);
        });
    }

    // ---------- 🚀 Отправка в бот (ГЛАВНАЯ ФУНКЦИЯ) ----------
    function sendToBot() {
        if (!State.drawn.length) {
            safeAlert('Сначала вытяните карты.');
            return;
        }

        // Формируем payload для бота (совместимо с handle_webapp_data в main.py)
        var payload = {
            action: 'tarot_spread',
            spread_type: State.spread,
            deck_id: State.deck ? State.deck.deck_id : null,
            question: State.question || '',
            cards: State.drawn.map(function (c) {
                return {
                    card_id: c.card_id,
                    name: c.name,
                    reversed: !!c.reversed
                };
            }),
            timestamp: Date.now()
        };

        if (tg && tg.sendData) {
            tg.sendData(JSON.stringify(payload));
            safePopup('✅ Отправлено', 'Расклад передан в чат бота. Ожидайте толкование.');
            setTimeout(function () { tg.close(); }, 1200);
        } else {
            alert('Вне Telegram отправка недоступна.');
        }
    }

    // ---------- Астрология ----------
    function fillSelect(id, items) {
        var sel = $(id);
        if (!sel) return;
        sel.innerHTML = '<option value="">Выберите…</option>';
        items.forEach(function (it) {
            var o = document.createElement('option');
            if (typeof it === 'string') { o.value = it; o.textContent = it; }
            else { o.value = it.id; o.textContent = it.name; }
            sel.appendChild(o);
        });
    }

    function sendAstro(e) {
        e.preventDefault();
        var p1 = $('planet1').value, s1 = $('sign1').value, a = $('aspect').value,
            p2 = $('planet2').value, s2 = $('sign2').value;
        if (!p1 || !s1 || !a || !p2 || !s2) {
            safeAlert('Заполните все поля.');
            return;
        }
        var aName = (ASPECTS.filter(function (x) { return x.id === a; })[0] || {}).name || a;
        var payload = {
            action: 'astrology_aspect',
            query: aName + ': ' + p1 + ' в ' + s1 + ' и ' + p2 + ' в ' + s2,
            timestamp: Date.now()
        };
        if (tg && tg.sendData) {
            tg.sendData(JSON.stringify(payload));
            safePopup('✅ Отправлено', 'Запрос передан в чат бота.');
            setTimeout(function () { tg.close(); }, 1200);
        } else {
            alert('Вне Telegram отправка недоступна.');
        }
    }

    // ---------- Инициализация ----------
    function init() {
        fillSelect('planet1', PLANETS); fillSelect('planet2', PLANETS);
        fillSelect('sign1', SIGNS);     fillSelect('sign2', SIGNS);
        fillSelect('aspect', ASPECTS);

        // Расклады
        Array.prototype.forEach.call(document.querySelectorAll('[data-spread]'), function (btn) {
            btn.addEventListener('click', function () {
                State.spread = btn.getAttribute('data-spread');
                loadDecks();
                showScreen('deck');
                haptic('light');
            });
        });

        // Кнопка «Астрология»
        var ba = $('btn-astro');
        if (ba) ba.addEventListener('click', function () { showScreen('astro'); haptic('light'); });

        // Вопрос
        var btnQ = $('btn-submit-question');
        if (btnQ) btnQ.addEventListener('click', submitQuestion);

        // Перемешать / вытянуть / отправить
        var btnShuffle = $('btn-shuffle');
        if (btnShuffle) btnShuffle.addEventListener('click', shuffle);
        var btnDraw = $('btn-draw');
        if (btnDraw) btnDraw.addEventListener('click', draw);
        var btnSend = $('btn-send');
        if (btnSend) btnSend.addEventListener('click', sendToBot);

        // 🏠 Все кнопки "Основное меню"
        Array.prototype.forEach.call(document.querySelectorAll('[data-action="main-menu"]'), function (btn) {
            btn.addEventListener('click', sendToMainMenu);
        });

        // Кнопки «назад» внутри экранов
        Array.prototype.forEach.call(document.querySelectorAll('[data-back]'), function (btn) {
            btn.addEventListener('click', function () {
                var target = btn.getAttribute('data-back');
                showScreen(target);
                haptic('light');
            });
        });

        // Форма астрологии
        var form = $('astro-form');
        if (form) form.addEventListener('submit', sendAstro);

        // Telegram BackButton
        if (tg && tg.BackButton) tg.BackButton.onClick(goBack);

        loadDecks();
        showScreen('spread');
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
