/**
 * Astro12AI Tarot Mini App - Production Ready Script v3.0
 * Исправлены: навигация, popup, обработка изображений, API толкования.
 */

(function() {
    'use strict';

    // --- 1. Инициализация ---
    const tg = window.Telegram.WebApp;
    
    // Состояние приложения
    const state = {
        step: 'spread-type',
        spreadType: null,
        threeType: null,
        deckId: null,
        useReversed: true,
        question: '',
        cards: [],
        interpretation: ''
    };

    // Кэш элементов DOM
    const screens = {};
    
    // Конфигурация путей (исправляем ошибку /undefined)
    const DEFAULT_CARD_BACK = '/static/cards/back.jpg'; // Убедитесь, что эта картинка есть, или используйте плейсхолдер

    // --- 2. Утилиты ---

    function triggerHaptic(type = 'light') {
        try {
            if (tg.HapticFeedback && typeof tg.HapticFeedback.impactOccurred === 'function') {
                tg.HapticFeedback.impactOccurred(type);
            }
        } catch (e) { /* Игнорируем ошибки тактильности */ }
    }

    function showAlert(message) {
        // Замена tg.showPopup на alert для совместимости
        if (tg.showAlert) {
            try {
                tg.showAlert(message);
                return;
            } catch (e) { /* Fallback если метод недоступен */ }
        }
        alert(message);
    }

    function showScreen(screenId) {
        triggerHaptic('light');
        
        Object.values(screens).forEach(el => {
            if (el) {
                el.style.display = 'none';
                el.classList.remove('active');
            }
        });

        const target = screens[screenId];
        if (target) {
            target.style.display = 'block';
            // Небольшой таймаут для запуска CSS анимации
            requestAnimationFrame(() => {
                target.classList.add('active');
            });
            window.scrollTo(0, 0);
        }
        
        state.step = screenId;
        console.log(`[Nav] Switched to: ${screenId}`);
    }

    // --- 3. Логика Навигации (Универсальная) ---

    function setupNavigation() {
        // Кнопки "Назад"
        document.querySelectorAll('.btn-back').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                handleBackAction();
            });
        });

        // Кнопки "Основное меню"
        document.querySelectorAll('.btn-home').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                triggerHaptic('heavy');
                resetApp();
            });
        });

        // Кнопка "Новый расклад" (на экране интерпретации)
        const newReadingBtn = document.getElementById('new-reading-btn');
        if (newReadingBtn) {
            newReadingBtn.addEventListener('click', (e) => {
                e.preventDefault();
                triggerHaptic('success');
                resetToShuffle();
            });
        }
        
        // Кнопка "К картам" (на экране интерпретации)
        const backToCardsBtns = document.querySelectorAll('[data-action="back-to-cards"]');
        backToCardsBtns.forEach(btn => {
             btn.addEventListener('click', (e) => {
                e.preventDefault();
                showScreen('result');
             });
        });
    }

    function handleBackAction() {
        const flow = ['spread-type', 'three-type', 'deck', 'reverse', 'question', 'shuffle', 'result', 'interpretation'];
        const currentIndex = flow.indexOf(state.step);
        
        if (currentIndex > 0) {
            let prevStep = flow[currentIndex - 1];
            // Логика пропуска шагов
            if (state.spreadType !== 'three' && prevStep === 'three-type') {
                prevStep = 'spread-type';
            }
            showScreen(prevStep);
        } else {
            resetApp();
        }
    }

    function resetApp() {
        state.spreadType = null;
        state.threeType = null;
        state.deckId = null;
        state.question = '';
        state.cards = [];
        state.interpretation = '';
        
        // Очищаем поля
        const input = document.getElementById('question-input');
        if(input) input.value = '';
        const resContainer = document.getElementById('result-cards-container');
        if(resContainer) resContainer.innerHTML = '';
        const interpText = document.getElementById('interpretation-text');
        if(interpText) interpText.textContent = '';

        tg.close(); // Закрываем мини-апп, возвращая в чат
    }

    function resetToShuffle() {
        state.cards = [];
        state.interpretation = '';
        const resContainer = document.getElementById('result-cards-container');
        if(resContainer) resContainer.innerHTML = '';
        const interpText = document.getElementById('interpretation-text');
        if(interpText) interpText.textContent = 'Загрузка мудрости...';
        
        showScreen('shuffle');
    }

    // --- 4. Логика Шагов ---

    function initSpreadType() {
        document.querySelectorAll('.spread-option:not([disabled])').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.getAttribute('data-type');
                state.spreadType = type;
                triggerHaptic('success');
                
                if (type === 'three') {
                    showScreen('three-type');
                } else {
                    showScreen('deck');
                }
            });
        });
    }

    function initThreeType() {
        document.querySelectorAll('.three-type-option').forEach(btn => {
            btn.addEventListener('click', () => {
                state.threeType = btn.getAttribute('data-type');
                triggerHaptic('success');
                showScreen('deck');
            });
        });
    }

    function initDeckSelection() {
        document.querySelectorAll('.deck-option').forEach(btn => {
            btn.addEventListener('click', () => {
                const deckId = btn.getAttribute('data-deck-id');
                if (!deckId) return;
                
                state.deckId = deckId;
                triggerHaptic('success');
                
                // Визуальное выделение
                document.querySelectorAll('.deck-option').forEach(b => b.style.borderColor = 'rgba(255,255,255,0.1)');
                btn.style.borderColor = '#d4af37';

                showScreen('reverse');
            });
        });
    }

    function initReverseSetting() {
        const yesBtn = document.getElementById('reverse-yes');
        const noBtn = document.getElementById('reverse-no');

        if(yesBtn) yesBtn.addEventListener('click', () => {
            state.useReversed = true;
            triggerHaptic('success');
            showScreen('question');
        });

        if(noBtn) noBtn.addEventListener('click', () => {
            state.useReversed = false;
            triggerHaptic('success');
            showScreen('question');
        });
    }

    function initQuestionStep() {
        const input = document.getElementById('question-input');
        const submitBtn = document.getElementById('submit-question-btn');

        if (!input || !submitBtn) return;

        const submit = () => {
            const val = input.value.trim();
            if (!val) {
                triggerHaptic('error');
                showAlert('Пожалуйста, введите вопрос перед продолжением.');
                return;
            }
            state.question = val;
            triggerHaptic('success');
            showScreen('shuffle');
        };

        submitBtn.addEventListener('click', (e) => {
            e.preventDefault();
            submit();
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submit();
            }
        });
    }

    function initShuffleStep() {
        const shuffleBtn = document.getElementById('shuffle-btn');
        const drawBtn = document.getElementById('draw-btn');

        if(shuffleBtn) {
            shuffleBtn.addEventListener('click', () => {
                triggerHaptic('heavy');
                const container = document.querySelector('.card-stack');
                if(container) {
                    container.classList.add('shuffling');
                    setTimeout(() => container.classList.remove('shuffling'), 800);
                }
                // Используем alert вместо showPopup
                showAlert('Колода перемешана. Сосредоточьтесь на вопросе.');
            });
        }

        if(drawBtn) {
            drawBtn.addEventListener('click', async () => {
                triggerHaptic('success');
                await performDraw();
            });
        }
    }

    async function performDraw() {
        // Показываем лоадер внутри экрана result перед рендером
        const container = document.getElementById('result-cards-container');
        if(container) container.innerHTML = '<div style="color:#aaa; padding:20px;">Вытягиваем карты...</div>';
        showScreen('result');

        try {
            const payload = {
                deck_id: state.deckId,
                spread_type: state.spreadType,
                three_type: state.threeType,
                reversed: state.useReversed,
                question: state.question
            };

            const response = await fetch('/api/tarot/draw', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            let data;
            if (response.ok) {
                data = await response.json();
            } else {
                console.warn('API fallback used');
                data = generateDemoCards(state.spreadType);
            }

            state.cards = data.cards || [];
            renderResults(state.cards);

        } catch (error) {
            console.error('Draw error:', error);
            showAlert('Ошибка соединения. Показываем демо-расклад.');
            state.cards = generateDemoCards(state.spreadType);
            renderResults(state.cards);
        }
    }

    function generateDemoCards(type) {
        const count = (type === 'three') ? 3 : 1;
        const cards = [];
        const demoNames = ["Шут", "Маг", "Жрица", "Императрица", "Солнце", "Луна"];
        
        for(let i=0; i<count; i++) {
            cards.push({
                id: i,
                name: demoNames[Math.floor(Math.random() * demoNames.length)],
                // Важно: проверяем наличие пути, иначе ставим заглушку
                image: DEFAULT_CARD_BACK, 
                is_reversed: state.useReversed && Math.random() > 0.5
            });
        }
        return { cards };
    }

    function renderResults(cards) {
        const container = document.getElementById('result-cards-container');
        if (!container) return;

        container.innerHTML = '';
        
        cards.forEach((card, index) => {
            const cardEl = document.createElement('div');
            cardEl.className = 'tarot-card-item';
            if (card.is_reversed) cardEl.classList.add('reversed');
            
            // Защита от undefined URL
            const imgUrl = card.image || DEFAULT_CARD_BACK;
            
            cardEl.innerHTML = `
                <div class="card-image" style="background-image: url('${imgUrl}')" onerror="this.style.backgroundImage='url(${DEFAULT_CARD_BACK})'"></div>
                <div class="card-name">${card.name}</div>
            `;
            container.appendChild(cardEl);
        });
    }

    function initResultStep() {
        const interpretBtn = document.getElementById('get-interpretation-btn');
        const retryBtn = document.getElementById('retry-spread-btn');

        if(interpretBtn) {
            interpretBtn.addEventListener('click', async () => {
                triggerHaptic('success');
                showScreen('interpretation');
                await fetchInterpretation();
            });
        }

        if(retryBtn) {
            retryBtn.addEventListener('click', () => {
                triggerHaptic('warning');
                resetToShuffle();
            });
        }
    }

    async function fetchInterpretation() {
        const textContainer = document.getElementById('interpretation-text');
        if(!textContainer) return;
        
        textContainer.textContent = "Звезды шепчут ответ...";
        textContainer.style.color = "#a0a0b0";

        try {
            const payload = {
                cards: state.cards,
                question: state.question,
                spread_type: state.spreadType,
                three_type: state.threeType
            };

            const response = await fetch('/api/tarot/interpret', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            let data;
            if (response.ok) {
                data = await response.json();
                // Поддержка разных форматов ответа
                const text = data.text || data.result || data.interpretation || "Толкование готово.";
                state.interpretation = text;
                textContainer.textContent = text;
                textContainer.style.color = "var(--text-main)";
            } else {
                throw new Error("API Error");
            }

        } catch (e) {
            console.error(e);
            textContainer.textContent = "Не удалось получить толкование от ИИ. Проверьте соединение или попробуйте позже.";
            textContainer.style.color = "var(--error-color)";
        }
    }

    // --- 5. Точка входа ---

    function init() {
        tg.expand();
        
        // Применение темы Telegram
        if (tg.themeParams.bg_color) {
            document.documentElement.style.setProperty('--bg-color', tg.themeParams.bg_color);
        }
        if (tg.themeParams.text_color) {
            document.documentElement.style.setProperty('--text-main', tg.themeParams.text_color);
        }

        // Кэширование экранов
        const screenIds = ['spread-type', 'three-type', 'deck', 'reverse', 'question', 'shuffle', 'result', 'interpretation'];
        screenIds.forEach(id => {
            screens[id] = document.getElementById(`screen-${id}`);
        });

        // Инициализация модулей
        setupNavigation();
        initSpreadType();
        initThreeType();
        initDeckSelection();
        initReverseSetting();
        initQuestionStep();
        initShuffleStep();
        initResultStep();

        // Старт
        showScreen('spread-type');
        console.log('Mini App v3.0 Initialized');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
 
})();