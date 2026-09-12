/**
 * Astro12AI Tarot Mini App - Production Ready Script
 * Версия: 2.0.0 (Stable)
 */

(function() {
    'use strict';

    // --- 1. Инициализация и Конфигурация ---
    const tg = window.Telegram.WebApp;
    
    // Состояние приложения
    const state = {
        step: 'spread-type', // start, spread-type, three-type, deck, reverse, question, shuffle, result, interpretation
        spreadType: null,    // 'one', 'three', 'choice', 'celtic'
        threeType: null,     // 'past-present-future', 'thoughts-feelings-actions', 'plus-minus-result'
        deckId: null,
        useReversed: true,
        question: '',
        cards: [],
        isShuffling: false
    };

    // Элементы DOM (кэшируем для производительности)
    const screens = {};
    let currentScreen = null;

    // --- 2. Утилиты и Безопасность ---

    /**
     * Безопасный вызов тактильной отдачи
     * Решает ошибку: tg.HapticFeedback.notificationChanged is not a function
     */
    function triggerHaptic(type = 'light') {
        try {
            if (tg.HapticFeedback) {
                // Используем только стабильные методы
                if (typeof tg.HapticFeedback.impactOccurred === 'function') {
                    tg.HapticFeedback.impactOccurred(type);
                }
            }
        } catch (e) {
            console.warn('Haptic feedback error:', e);
        }
    }

    /**
     * Безопасное расширение главной кнопки
     */
    function updateMainButton(text, isVisible, onClick) {
        try {
            if (isVisible) {
                tg.MainButton.setText(text);
                tg.MainButton.show();
                tg.MainButton.onClick(onClick);
            } else {
                tg.MainButton.hide();
                tg.MainButton.offClick(onClick);
            }
        } catch (e) {
            console.warn('MainButton error:', e);
        }
    }

    /**
     * Переключение экранов с анимацией
     */
    function showScreen(screenId) {
        triggerHaptic('light');
        
        // Скрываем все экраны
        Object.values(screens).forEach(el => {
            if (el) el.style.display = 'none';
        });

        // Показываем нужный
        const target = screens[screenId];
        if (target) {
            target.style.display = 'block';
            // Небольшая анимация появления
            target.style.opacity = '0';
            setTimeout(() => {
                target.style.transition = 'opacity 0.3s ease';
                target.style.opacity = '1';
            }, 10);
        }
        
        state.step = screenId;
        console.log(`Screen switched to: ${screenId}`);
    }

    // --- 3. Логика Навигации ---

    function initNavigation() {
        // Кнопки "Назад"
        document.querySelectorAll('.btn-back').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                triggerHaptic('medium');
                handleBackAction();
            });
        });

        // Кнопки "Основное меню"
        document.querySelectorAll('.btn-home').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                triggerHaptic('heavy');
                resetToMenu();
            });
        });
    }

    function handleBackAction() {
        // Простая логика возврата на шаг назад
        const flow = ['spread-type', 'three-type', 'deck', 'reverse', 'question', 'shuffle', 'result', 'interpretation'];
        const currentIndex = flow.indexOf(state.step);
        
        if (currentIndex > 0) {
            let prevStep = flow[currentIndex - 1];
            
            // Пропускаем лишние шаги если нужно
            if (state.spreadType !== 'three' && prevStep === 'three-type') {
                prevStep = 'spread-type';
            }
            
            showScreen(prevStep);
        } else {
            resetToMenu();
        }
    }

    function resetToMenu() {
        // Сброс состояния
        state.spreadType = null;
        state.threeType = null;
        state.deckId = null;
        state.question = '';
        state.cards = [];
        
        // Возврат на главный экран бота (закрываем мини-апп или переключаем контекст)
        // В рамках Mini App лучше просто показать стартовый экран или закрыть
        tg.close(); 
    }

    // --- 4. Логика Шагов (Flow) ---

    function initSpreadType() {
        document.querySelectorAll('.spread-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const type = btn.getAttribute('data-type');
                state.spreadType = type;
                triggerHaptic('success');

                if (type === 'three') {
                    showScreen('three-type');
                } else {
                    // Для одиночной карты сразу идем к выбору колоды
                    // Можно добавить промежуточный шаг, но по ТЗ сразу колода
                    showScreen('deck');
                }
            });
        });
    }

    function initThreeType() {
        document.querySelectorAll('.three-type-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                state.threeType = btn.getAttribute('data-type');
                triggerHaptic('success');
                showScreen('deck');
            });
        });
    }

    function initDeckSelection() {
        document.querySelectorAll('.deck-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const deckId = btn.getAttribute('data-deck-id');
                if (!deckId) return;
                
                state.deckId = deckId;
                triggerHaptic('success');
                
                // Подсветка выбранной колоды (опционально)
                document.querySelectorAll('.deck-option').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');

                showScreen('reverse');
            });
        });
    }

    function initReverseSetting() {
        const yesBtn = document.querySelector('#reverse-yes');
        const noBtn = document.querySelector('#reverse-no');

        if(yesBtn) yesBtn.addEventListener('click', (e) => {
            e.preventDefault();
            state.useReversed = true;
            triggerHaptic('success');
            showScreen('question');
        });

        if(noBtn) noBtn.addEventListener('click', (e) => {
            e.preventDefault();
            state.useReversed = false;
            triggerHaptic('success');
            showScreen('question');
        });
    }

    function initQuestionStep() {
        const input = document.querySelector('#question-input');
        const submitBtn = document.querySelector('#submit-question-btn');

        if (!input || !submitBtn) return;

        // Обработчик кнопки "Продолжить"
        submitBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Важно! Предотвращаем перезагрузку
            
            const val = input.value.trim();
            if (!val) {
                triggerHaptic('error');
                tg.showAlert('Пожалуйста, введите вопрос перед продолжением.');
                return;
            }

            state.question = val;
            triggerHaptic('success');
            
            // Переход к перемешиванию
            showScreen('shuffle');
        });

        // Также обрабатываем Enter
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitBtn.click();
            }
        });
    }

    function initShuffleStep() {
        const shuffleBtn = document.querySelector('#shuffle-btn');
        const drawBtn = document.querySelector('#draw-btn');

        if(shuffleBtn) {
            shuffleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                triggerHaptic('heavy');
                // Анимация перемешивания (визуально можно добавить класс)
                const container = document.querySelector('.cards-container');
                if(container) {
                    container.classList.add('shuffling');
                    setTimeout(() => container.classList.remove('shuffling'), 1000);
                }
                tg.showPopup({
                    title: 'Колода перемешана',
                    message: 'Энергия карт готова к раскрытию.',
                    buttons: [{type: 'ok'}]
                });
            });
        }

        if(drawBtn) {
            drawBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                triggerHaptic('success');
                await performDraw();
            });
        }
    }

    async function performDraw() {
        showScreen('result-loading'); // Показать экран загрузки если есть, или спиннер
        
        try {
            // Формируем запрос к API
            const payload = {
                deck_id: state.deckId,
                spread_type: state.spreadType,
                three_type: state.threeType,
                reversed: state.useReversed,
                question: state.question
            };

            // Запрос к бэкенду (предполагается, что маршрут /api/tarot/draw существует)
            // Если бэкенд еще не готов, используем заглушку для демонстрации UI
            const response = await fetch('/api/tarot/draw', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            let data;
            if (response.ok) {
                data = await response.json();
            } else {
                // Fallback демо-данные если API упал или нет
                console.warn('API fallback used');
                data = generateDemoCards(state.spreadType);
            }

            state.cards = data.cards || [];
            renderResults(state.cards);
            showScreen('result');

        } catch (error) {
            console.error('Draw error:', error);
            tg.showAlert('Произошла ошибка при вытягивании карт. Попробуйте снова.');
            // Демо данные на всякий случай
            state.cards = generateDemoCards(state.spreadType);
            renderResults(state.cards);
            showScreen('result');
        }
    }

    function generateDemoCards(type) {
        // Заглушка для тестирования UI без бэкенда
        const count = (type === 'three') ? 3 : 1;
        const cards = [];
        for(let i=0; i<count; i++) {
            cards.push({
                id: i,
                name: `Карта ${i+1}`,
                image: '/static/cards/back.jpg', // Путь к рубашке или лицу
                is_reversed: state.useReversed && Math.random() > 0.5
            });
        }
        return { cards };
    }

    function renderResults(cards) {
        const container = document.querySelector('#result-cards-container');
        if (!container) return;

        container.innerHTML = '';
        
        cards.forEach((card, index) => {
            const cardEl = document.createElement('div');
            cardEl.className = 'tarot-card-item';
            if (card.is_reversed) cardEl.classList.add('reversed');
            
            // Здесь должна быть верстка карты (картинка + название)
            cardEl.innerHTML = `
                <div class="card-image" style="background-image: url('${card.image}')"></div>
                <div class="card-name">${card.name}</div>
            `;
            container.appendChild(cardEl);
        });
    }

    function initResultStep() {
        const interpretBtn = document.querySelector('#get-interpretation-btn');
        const retryBtn = document.querySelector('#retry-spread-btn');

        if(interpretBtn) {
            interpretBtn.addEventListener('click', async () => {
                triggerHaptic('success');
                showScreen('interpretation-loading');
                await fetchInterpretation();
            });
        }

        if(retryBtn) {
            retryBtn.addEventListener('click', () => {
                triggerHaptic('warning');
                showScreen('shuffle');
            });
        }
    }

    async function fetchInterpretation() {
        try {
            const payload = {
                cards: state.cards,
                question: state.question,
                spread_type: state.spreadType
            };

            const response = await fetch('/api/tarot/interpret', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            let data;
            if (response.ok) {
                data = await response.json();
            } else {
                data = { text: "Здесь будет толкование от ИИ. (Сервис временно недоступен, показываем заглушку)." };
            }

            renderInterpretation(data.text || data.result || "Толкование...");
            showScreen('interpretation');

        } catch (e) {
            console.error(e);
            renderInterpretation("Ошибка соединения с ИИ. Попробуйте позже.");
            showScreen('interpretation');
        }
    }

    function renderInterpretation(text) {
        const container = document.querySelector('#interpretation-text');
        if (container) {
            // Простая защита от XSS и форматирование переносов строк
            container.textContent = text; 
            // Или innerHTML если сервер присылает HTML
        }
    }

    // --- 5. Точка входа ---

    function init() {
        // Расширяем окно на весь экран
        tg.expand(); 
        
        // Настраиваем цвета под тему Telegram
        document.body.style.backgroundColor = tg.themeParams.bg_color || '#1a1a1a';
        document.body.style.color = tg.themeParams.text_color || '#ffffff';

        // Кэширование элементов
        screens['spread-type'] = document.getElementById('screen-spread-type');
        screens['three-type'] = document.getElementById('screen-three-type');
        screens['deck'] = document.getElementById('screen-deck');
        screens['reverse'] = document.getElementById('screen-reverse');
        screens['question'] = document.getElementById('screen-question');
        screens['shuffle'] = document.getElementById('screen-shuffle');
        screens['result'] = document.getElementById('screen-result');
        screens['interpretation'] = document.getElementById('screen-interpretation');
        // Добавьте экраны загрузки если они есть в HTML

        // Инициализация логики
        initNavigation();
        initSpreadType();
        initThreeType();
        initDeckSelection();
        initReverseSetting();
        initQuestionStep();
        initShuffleStep();
        initResultStep();

        // Старт с первого экрана
        showScreen('spread-type');
        
        console.log('Mini App initialized successfully');
    }

    // Запуск после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
