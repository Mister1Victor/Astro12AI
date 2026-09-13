/**
 * Astro12AI Tarot Mini App — Production Ready v3.1
 * 
 * ИСПРАВЛЕНО v3.1:
 * 1. Кнопка «Основное меню» — отправляет tg.sendData({action:'main_menu'}) + tg.close()
 * 2. Кнопка «Повторить вопрос» при ошибке ИИ — повторно отправляет тот же запрос
 * 3. Совместимость с HTML-структурой screen-* ID
 */
(function () {
    'use strict';

    const tg = window.Telegram ? window.Telegram.WebApp : null;
    if (tg) { tg.ready(); tg.expand(); }

    // ==================== СОСТОЯНИЕ ====================
    const state = {
        step: 'spread-type',
        spreadType: null,
        threeType: null,
        deckId: null,
        deckName: '',
        useReversed: true,
        question: '',
        cards: [],
        interpretation: '',
        interpretationError: false,
        decks: []
    };

    // ==================== КОНСТАНТЫ ====================
    const FLOW = [
        'spread-type', 'three-type', 'deck', 'reverse',
        'question', 'shuffle', 'result', 'interpretation'
    ];

    const SPREAD_COUNTS = {
        'one': 1, 'three': 3, 'choice': 7, 'celtic': 10
    };

    const SPREAD_NAMES = {
        'one': 'Одна карта',
        'three': 'Три карты',
        'choice': 'Выбор пути',
        'celtic': 'Кельтский крест'
    };

    const DEFAULT_CARD_BACK = '/static/cards/back.jpg';

    // ==================== УТИЛИТЫ ====================
    function $(id) { return document.getElementById(id); }

    function triggerHaptic(type) {
        try {
            if (tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred) {
                tg.HapticFeedback.impactOccurred(type || 'light');
            }
        } catch (e) { /* ignore */ }
    }

    function showAlert(msg) {
        try {
            if (tg && tg.showAlert) { tg.showAlert(msg); return; }
        } catch (e) { /* fallback */ }
        alert(msg);
    }

    function showScreen(name) {
        triggerHaptic('light');
        FLOW.forEach(function (s) {
            var el = $('screen-' + s);
            if (el) {
                if (s === name) {
                    el.style.display = 'block';
                    el.classList.add('active');
                } else {
                    el.style.display = 'none';
                    el.classList.remove('active');
                }
            }
        });
        state.step = name;
        window.scrollTo(0, 0);
    }

    // ==================== НАВИГАЦИЯ ====================
    function handleBack() {
        var idx = FLOW.indexOf(state.step);
        if (idx <= 0) { resetApp(); return; }
        var prev = FLOW[idx - 1];
        // Пропускаем three-type если расклад не "three"
        if (prev === 'three-type' && state.spreadType !== 'three') {
            prev = FLOW[idx - 2] || 'spread-type';
        }
        showScreen(prev);
    }

    function resetApp() {
        triggerHaptic('heavy');
        // Отправляем боту сигнал вернуться в главное меню
        if (tg && tg.sendData) {
            try {
                tg.sendData(JSON.stringify({
                    action: 'main_menu',
                    timestamp: Date.now()
                }));
            } catch (e) { /* ignore */ }
        }
        // Сброс состояния
        state.spreadType = null;
        state.threeType = null;
        state.deckId = null;
        state.deckName = '';
        state.question = '';
        state.cards = [];
        state.interpretation = '';
        state.interpretationError = false;
        var qi = $('question-input');
        if (qi) qi.value = '';
        var rc = $('result-cards-container');
        if (rc) rc.innerHTML = '';
        var it = $('interpretation-text');
        if (it) { it.textContent = 'Загрузка мудрости...'; it.style.color = ''; }
        var rc2 = $('retry-interpretation-container');
        if (rc2) rc2.style.display = 'none';
        // Закрываем Mini App — возврат в чат бота
        if (tg && tg.close) {
            setTimeout(function () { tg.close(); }, 300);
        }
    }

    function resetToShuffle() {
        state.cards = [];
        state.interpretation = '';
        state.interpretationError = false;
        var rc = $('result-cards-container');
        if (rc) rc.innerHTML = '';
        var it = $('interpretation-text');
        if (it) { it.textContent = 'Загрузка мудрости...'; it.style.color = ''; }
        var rc2 = $('retry-interpretation-container');
        if (rc2) rc2.style.display = 'none';
        // Сброс кнопок shuffle/draw
        var sb = $('shuffle-btn');
        var db = $('draw-btn');
        if (sb) { sb.style.display = ''; sb.disabled = false; }
        if (db) { db.style.display = 'none'; db.disabled = false; }
        showScreen('shuffle');
    }

    // ==================== ЗАГРУЗКА КОЛОД ====================
    function loadDecks() {
        fetch('/api/tarot/decks')
            .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
            .then(function (data) {
                state.decks = Array.isArray(data) && data.length ? data : getFallbackDecks();
                renderDecks();
            })
            .catch(function () {
                state.decks = getFallbackDecks();
                renderDecks();
            });
    }

    function getFallbackDecks() {
        return [
            { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 },
            { deck_id: 'rider_waite', name: 'Таро Райдера-Уэйта', cards_count: 78 },
            { deck_id: 'thoth', name: 'Таро Тота', cards_count: 78 },
            { deck_id: 'author_deck', name: 'Авторская колода Школы', cards_count: 78 }
        ];
    }

    function renderDecks() {
        var box = $('deck-list');
        if (!box) return;
        box.innerHTML = '';
        state.decks.forEach(function (d) {
            if (d.cards_count <= 0) return;
            var btn = document.createElement('button');
            btn.className = 'option-row deck-option';
            btn.setAttribute('data-deck-id', d.deck_id);
            btn.innerHTML =
                '<span class="icon">🎴</span>' +
                '<span class="text">' + d.name + '</span>' +
                '<span class="subtext">' + d.cards_count + ' карт</span>';
            btn.addEventListener('click', function () {
                state.deckId = d.deck_id;
                state.deckName = d.name;
                triggerHaptic('success');
                showScreen('reverse');
            });
            box.appendChild(btn);
        });
    }

    // ==================== ВЫТЯГИВАНИЕ КАРТ ====================
    function shuffleDeck() {
        triggerHaptic('heavy');
        var stack = document.querySelector('.card-stack');
        if (stack) {
            stack.classList.add('shuffling');
            setTimeout(function () { stack.classList.remove('shuffling'); }, 800);
        }
        var sb = $('shuffle-btn');
        var db = $('draw-btn');
        if (sb) sb.style.display = 'none';
        if (db) db.style.display = '';
    }

    function drawCards() {
        triggerHaptic('success');
        var count = SPREAD_COUNTS[state.spreadType] || 1;
        var rc = $('result-cards-container');
        if (rc) rc.innerHTML = '<div style="color:#aaa;padding:20px;text-align:center;">Вытягиваем карты...</div>';
        showScreen('result');

        fetch('/api/tarot/draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: state.deckId,
                count: count,
                spread_type: state.spreadType,
                use_reversed: state.useReversed
            })
        })
        .then(function (r) { return r.ok ? r.json() : Promise.reject('http ' + r.status); })
        .then(function (data) {
            if (!data || !Array.isArray(data.cards) || !data.cards.length) {
                throw new Error('empty');
            }
            state.cards = data.cards;
            renderCards(data.cards);
        })
        .catch(function (err) {
            console.error('Draw error:', err);
            // Фолбэк: демо-карты
            state.cards = generateDemoCards(count);
            renderCards(state.cards);
        });
    }

    function generateDemoCards(count) {
        var names = ['Шут', 'Маг', 'Жрица', 'Императрица', 'Император',
                     'Иерофант', 'Влюблённые', 'Колесница', 'Сила', 'Солнце'];
        var cards = [];
        for (var i = 0; i < count; i++) {
            cards.push({
                card_id: 'demo_' + i,
                name: names[Math.floor(Math.random() * names.length)],
                reversed: state.useReversed && Math.random() > 0.5,
                image_url: null
            });
        }
        return cards;
    }

    function renderCards(cards) {
        var container = $('result-cards-container');
        if (!container) return;
        container.innerHTML = '';
        cards.forEach(function (card, i) {
            var el = document.createElement('div');
            el.className = 'tarot-card-item';
            if (card.reversed) el.classList.add('reversed');
            var imgUrl = card.image_url || DEFAULT_CARD_BACK;
            el.innerHTML =
                '<div class="card-image" style="background-image:url(\'' + imgUrl + '\')"' +
                ' onerror="this.style.backgroundImage=\'url(' + DEFAULT_CARD_BACK + ')\'"></div>' +
                '<div class="card-name">' + (card.name || 'Карта') + '</div>';
            el.style.animationDelay = (i * 0.15) + 's';
            container.appendChild(el);
        });
    }

    // ==================== ТОЛКОВАНИЕ ====================
    function fetchInterpretation() {
        var textEl = $('interpretation-text');
        var retryContainer = $('retry-interpretation-container');
        if (!textEl) return;

        // Показываем загрузку
        textEl.textContent = 'Звёзды шепчут ответ...';
        textEl.style.color = '#a0a0b0';
        if (retryContainer) retryContainer.style.display = 'none';
        state.interpretationError = false;

        var positions = [];
        if (state.spreadType === 'three') {
            if (state.threeType === 'past-present-future') {
                positions = ['Прошлое', 'Настоящее', 'Будущее'];
            } else if (state.threeType === 'thoughts-feelings-actions') {
                positions = ['Мысли', 'Чувства', 'Действия'];
            } else if (state.threeType === 'plus-minus-result') {
                positions = ['Плюс', 'Минус', 'Итог'];
            }
        } else if (state.spreadType === 'celtic') {
            positions = ['Суть', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
                         'Будущее', 'Я', 'Окружение', 'Надежды/страхи', 'Итог'];
        } else if (state.spreadType === 'choice') {
            positions = ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход',
                         'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'];
        } else {
            positions = ['Карта дня'];
        }

        fetch('/api/tarot/interpret', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                deck_id: state.deckId,
                spread_type: state.spreadType,
                three_card_type: state.threeType,
                question: state.question,
                cards: state.cards,
                positions: positions,
                use_reversed: state.useReversed
            })
        })
        .then(function (r) {
            if (!r.ok) throw new Error('http ' + r.status);
            return r.json();
        })
        .then(function (data) {
            var text = data.interpretation || data.text || data.result || '';
            if (!text || text.length < 10) throw new Error('empty');
            state.interpretation = text;
            state.interpretationError = false;
            textEl.textContent = text;
            textEl.style.color = '';
            if (retryContainer) retryContainer.style.display = 'none';
            triggerHaptic('success');
        })
        .catch(function (err) {
            console.error('Interpretation error:', err);
            state.interpretationError = true;
            textEl.textContent = '⚠️ ИИ временно недоступен. Попробуйте через 1–2 минуты.';
            textEl.style.color = '#ff4b4b';
            // 🔧 ПОКАЗЫВАЕМ КНОПКУ ПОВТОРА
            if (retryContainer) retryContainer.style.display = 'block';
            triggerHaptic('error');
        });
    }

    // 🔧 ПОВТОРНАЯ ОТПРАВКА ТОГО ЖЕ ВОПРОСА С ТЕМИ ЖЕ КАРТАМИ
    function retryInterpretation() {
        triggerHaptic('medium');
        fetchInterpretation();
    }

    // ==================== ОТПРАВКА В БОТ ====================
    function sendToBot() {
        if (!state.cards.length) { showAlert('Сначала вытяните карты.'); return; }
        var payload = {
            action: 'tarot_spread',
            spread_type: state.spreadType,
            deck_id: state.deckId,
            question: state.question,
            cards: state.cards.map(function (c) {
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
            try {
                if (tg.showPopup) {
                    tg.showPopup({
                        title: '✅ Отправлено',
                        message: 'Расклад передан в чат бота.',
                        buttons: [{ type: 'ok' }]
                    });
                }
            } catch (e) { /* ignore */ }
            setTimeout(function () { if (tg && tg.close) tg.close(); }, 1200);
        } else {
            showAlert('Вне Telegram отправка недоступна.');
        }
    }

    // ==================== ИНИЦИАЛИЗАЦИЯ ====================
    function init() {
        // Тема Telegram
        if (tg && tg.themeParams) {
            var root = document.documentElement;
            if (tg.themeParams.bg_color) root.style.setProperty('--bg-color', tg.themeParams.bg_color);
            if (tg.themeParams.text_color) root.style.setProperty('--text-main', tg.themeParams.text_color);
        }

        // --- Кнопки навигации ---
        document.querySelectorAll('.btn-back').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                handleBack();
            });
        });

        // 🔧 Кнопки «Основное меню» — закрывают Mini App и возвращают в чат
        document.querySelectorAll('.btn-home').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                resetApp();
            });
        });

        // --- Выбор расклада ---
        document.querySelectorAll('.spread-option').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var type = btn.getAttribute('data-type');
                state.spreadType = type;
                triggerHaptic('success');
                if (type === 'three') {
                    showScreen('three-type');
                } else {
                    loadDecks();
                    showScreen('deck');
                }
            });
        });

        // --- Выбор типа трёхкарточного ---
        document.querySelectorAll('.three-type-option').forEach(function (btn) {
            btn.addEventListener('click', function () {
                state.threeType = btn.getAttribute('data-type');
                triggerHaptic('success');
                loadDecks();
                showScreen('deck');
            });
        });

        // --- Настройка перевёрнутых ---
        var ry = $('reverse-yes');
        var rn = $('reverse-no');
        if (ry) ry.addEventListener('click', function () {
            state.useReversed = true;
            triggerHaptic('success');
            showScreen('question');
        });
        if (rn) rn.addEventListener('click', function () {
            state.useReversed = false;
            triggerHaptic('success');
            showScreen('question');
        });

        // --- Вопрос ---
        var submitQ = $('submit-question-btn');
        var qInput = $('question-input');
        if (submitQ) submitQ.addEventListener('click', function (e) {
            e.preventDefault();
            var val = qInput ? qInput.value.trim() : '';
            if (!val) { triggerHaptic('error'); showAlert('Введите вопрос.'); return; }
            state.question = val;
            triggerHaptic('success');
            showScreen('shuffle');
        });
        if (qInput) qInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQ.click(); }
        });

        // --- Перемешивание ---
        var shuffleBtn = $('shuffle-btn');
        if (shuffleBtn) shuffleBtn.addEventListener('click', shuffleDeck);

        // --- Вытягивание ---
        var drawBtn = $('draw-btn');
        if (drawBtn) drawBtn.addEventListener('click', drawCards);

        // --- Толкование ---
        var interpBtn = $('get-interpretation-btn');
        if (interpBtn) interpBtn.addEventListener('click', function () {
            showScreen('interpretation');
            fetchInterpretation();
        });

        // 🔧 КНОПКА ПОВТОРА ТОЛКОВАНИЯ
        var retryInterpBtn = $('retry-interpretation-btn');
        if (retryInterpBtn) retryInterpBtn.addEventListener('click', function (e) {
            e.preventDefault();
            retryInterpretation();
        });

        // --- Повторить расклад ---
        var retryBtn = $('retry-spread-btn');
        if (retryBtn) retryBtn.addEventListener('click', function (e) {
            e.preventDefault();
            triggerHaptic('warning');
            resetToShuffle();
        });

        // --- Новый расклад (с экрана толкования) ---
        var newBtn = $('new-reading-btn');
        if (newBtn) newBtn.addEventListener('click', function (e) {
            e.preventDefault();
            triggerHaptic('success');
            state.spreadType = null;
            state.threeType = null;
            state.deckId = null;
            state.question = '';
            state.cards = [];
            state.interpretation = '';
            state.interpretationError = false;
            var rc2 = $('retry-interpretation-container');
            if (rc2) rc2.style.display = 'none';
            showScreen('spread-type');
        });

        // --- К картам (с экрана толкования) ---
        document.querySelectorAll('[data-action="back-to-cards"]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                showScreen('result');
            });
        });

        // --- Telegram BackButton ---
        if (tg && tg.BackButton) {
            tg.BackButton.onClick(handleBack);
        }

        // Старт
        loadDecks();
        showScreen('spread-type');
        console.log('🔮 Mini App v3.1 initialized');
    }

    // Запуск
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();