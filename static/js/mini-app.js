const tg = window.Telegram.WebApp;
tg.expand();

// Состояние приложения
const state = {
    spreadCount: 1, // 1 или 3
    spreadType: null,
    deck: null,
    reversed: false,
    question: '',
    cards: []
};

const app = {
    // Переключение экранов
    showScreen: (screenId) => {
        // Скрываем все экраны
        document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
        // Показываем нужный
        const target = document.getElementById(screenId);
        if (target) {
            target.classList.add('active');
            tg.BackButton.visible = (screenId !== 'screen-main' && screenId !== 'screen-spread');
        } else {
            console.error(`Экран ${screenId} не найден!`);
        }
    },

    toMainMenu: () => {
        // Возвращаем данные боту, но не закрываем приложение сразу, а показываем главное меню
        // Или просто переключаем вид
        app.showScreen('screen-main');
    },

    closeApp: () => {
        tg.close();
    },

    // Шаг 1: Выбор расклада
    selectSpread: (count) => {
        state.spreadCount = count;
        if (count === 3) {
            app.showScreen('screen-type');
        } else {
            app.showScreen('screen-deck');
        }
    },

    // Шаг 2: Тип расклада (только для 3 карт)
    selectType: (type) => {
        state.spreadType = type;
        app.showScreen('screen-deck');
    },

    // Шаг 3: Выбор колоды
    selectDeck: (deckName) => {
        state.deck = deckName;
        app.showScreen('screen-reversed');
    },

    // Шаг 4: Перевёрнутые карты
    setReversed: (isReversed) => {
        state.reversed = isReversed;
        app.showScreen('screen-question');
    },

    // Шаг 5: Вопрос -> Перемешивание
    goToShuffle: () => {
        const input = document.getElementById('question-input');
        state.question = input.value.trim();
        
        app.showScreen('screen-shuffle');
        
        // Имитация перемешивания
        const btnDraw = document.getElementById('btn-draw');
        const shuffleText = document.getElementById('shuffle-text');
        btnDraw.classList.add('hidden');
        shuffleText.innerText = "Перемешиваем колоду...";
        
        setTimeout(() => {
            shuffleText.innerText = "Сосредоточьтесь на вопросе...";
            setTimeout(() => {
                btnDraw.classList.remove('hidden');
                tg.HapticFeedback.notificationOccurred('success');
            }, 1500);
        }, 1000);
    },

    // Шаг 6: Вытягивание карт и Генерация результата
    drawCards: () => {
        // Здесь должна быть логика вызова API к бэкенду
        // Для примера генерируем фейковые данные, чтобы показать интерфейс
        const mockCards = [];
        const cardNames = ["Маг", "Жрица", "Императрица", "Император", "Влюбленные", "Колесница"];
        
        for (let i = 0; i < state.spreadCount; i++) {
            const isRev = state.reversed && Math.random() > 0.7;
            const name = cardNames[Math.floor(Math.random() * cardNames.length)];
            mockCards.push({ name, reversed: isRev, position: i });
        }
        
        state.cards = mockCards;
        app.renderResult(mockCards);
        app.showScreen('screen-result');
    },

    // Отрисовка результата ВНУТРИ приложения
    renderResult: (cards) => {
        const container = document.getElementById('result-cards');
        const textContainer = document.getElementById('result-interpretation');
        
        container.innerHTML = '';
        
        // Рисуем карты
        cards.forEach(card => {
            const cardEl = document.createElement('div');
            cardEl.className = `result-card ${card.reversed ? 'reversed' : ''}`;
            cardEl.innerText = card.name;
            container.appendChild(cardEl);
        });

        // Формируем текст толкования (Здесь будет ответ от LLM)
        let interpretation = `Расклад: ${state.spreadCount === 3 ? state.spreadType : 'Одна карта'}\n`;
        interpretation += `Колода: ${state.deck}\n`;
        interpretation += `Вопрос: ${state.question || 'Общий'}\n\n`;
        
        cards.forEach((card, index) => {
            const posText = state.spreadCount === 3 
                ? (index === 0 ? '1. ' : index === 1 ? '2. ' : '3. ') 
                : '';
            const revText = card.reversed ? ' (Перевёрнутая)' : '';
            interpretation += `${posText}${card.name}${revText}\n`;
        });

        interpretation += "\n[Здесь будет полный текст толкования от ИИ-агента...]";
        
        textContainer.innerText = interpretation;
        
        // Отправляем данные боту (опционально, чтобы он тоже знал результат)
        // Но НЕ закрываем приложение
        tg.sendData(JSON.stringify({
            action: 'tarot_result',
            cards: cards,
            question: state.question,
            deck: state.deck
        }));
    },

    restart: () => {
        state.spreadCount = 1;
        state.spreadType = null;
        state.deck = null;
        state.reversed = false;
        state.question = '';
        document.getElementById('question-input').value = '';
        app.showScreen('screen-spread');
    }
};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    app.showScreen('screen-spread');
    
    // Обработка кнопки "Назад" от Telegram
    tg.BackButton.onClick(() => {
        // Простая логика возврата на шаг назад по истории экранов могла бы быть здесь
        // Но по ТЗ у нас есть кнопки внизу экрана
        app.showScreen('screen-spread'); 
    });
});