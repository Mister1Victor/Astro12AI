/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║  Astro12AI Mini App — Telegram WebApp Client                ║
 * ║  Школа Астрологии «12 Планет»                               ║
 * ╚══════════════════════════════════════════════════════════════╝
 *
 * Модули:
 *   • Telegram SDK интеграция
 *   • State management
 *   • API client
 *   • UI контроллеры (Таро / Астрология)
 *   • Анимации и Haptic feedback
 */

// ═══════════════════════════════════════════════════════════════
// TELEGRAM SDK
// ═══════════════════════════════════════════════════════════════
const tg = window.Telegram?.WebApp;

// Инициализация Telegram WebApp
if (tg) {
    tg.ready();
    tg.expand();
    tg.enableClosingConfirmation();
}

// ═══════════════════════════════════════════════════════════════
// КОНСТАНТЫ
// ═══════════════════════════════════════════════════════════════

/** Конфигурация раскладов: имя, число карт, позиции */
const SPREAD_CONFIGS = {
    one: {
        name: "Одна карта",
        count: 1,
        positions: ["Карта Дня"],
        emoji: "🃏",
    },
    three: {
        name: "Три карты",
        count: 3,
        positions: ["Прошлое", "Настоящее", "Будущее"],
        emoji: "🔮",
    },
    choice: {
        name: "Выбор пути",
        count: 7,
        positions: [
            "Вариант 1 — Достоинство",
            "Вариант 1 — Недостаток",
            "Вариант 1 — Исход",
            "Вариант 2 — Достоинство",
            "Вариант 2 — Недостаток",
            "Вариант 2 — Исход",
            "Совет",
        ],
        emoji: "⚖️",
    },
    celtic: {
        name: "Кельтский крест",
        count: 10,
        positions: [
            "Суть ситуации (сигнификатор)",
            "Препятствие / что пересекает",
            "Цель / сознательное стремление",
            "Корни / подсознательное",
            "Прошлое (уходящее)",
            "Ближайшее будущее",
            "Я (самовосприятие)",
            "Окружение (внешние влияния)",
            "Надежды и страхи",
            "Итог",
        ],
        emoji: "✝️",
    },
    plusminus: {
        name: "Плюс — Минус — Итог",
        count: 3,
        positions: ["Плюс", "Минус", "Итог"],
        emoji: "➕",
    },
    yesno: {
        name: "Да или Нет",
        count: 1,
        positions: ["Ответ"],
        emoji: "🎯",
    },
};

/** Астрологические данные для формы */
const ASTRO_DATA = {
    planets: [
        { value: "Sun",     label: "Солнце ☉" },
        { value: "Moon",    label: "Луна ☽" },
        { value: "Mercury", label: "Меркурий ☿" },
        { value: "Venus",   label: "Венера ♀" },
        { value: "Mars",    label: "Марс ♂" },
        { value: "Jupiter", label: "Юпитер ♃" },
        { value: "Saturn",  label: "Сатурн ♄" },
    ],
    signs: [
        { value: "Ari", label: "Овен ♈" },
        { value: "Tau", label: "Телец ♉" },
        { value: "Gem", label: "Близнецы ♊" },
        { value: "Can", label: "Рак ♋" },
        { value: "Leo", label: "Лев ♌" },
        { value: "Vir", label: "Дева ♍" },
        { value: "Lib", label: "Весы ♎" },
        { value: "Sco", label: "Скорпион ♏" },
        { value: "Sgr", label: "Стрелец ♐" },
        { value: "Cap", label: "Козерог ♑" },
        { value: "Aqr", label: "Водолей ♒" },
        { value: "Psc", label: "Рыбы ♓" },
    ],
    aspects: [
        { value: "conjunction", label: "Соединение (0°)" },
        { value: "sextile",     label: "Секстиль (60°)" },
        { value: "square",      label: "Квадрат (90°)" },
        { value: "trine",       label: "Трин (120°)" },
        { value: "opposition",  label: "Оппозиция (180°)" },
        { value: "quincunx",    label: "Квиконс (150°)" },
    ],
};

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════
const AppState = {
    currentScreen:  "spread-selection",
    currentSpread:  null,
    selectedDeck:   null,
    drawnCards:     [],
    decks:          [],
    isShuffling:    false,
    isDrawing:      false,
    userId:         tg?.initDataUnsafe?.user?.id || 0,
    userName:       tg?.initDataUnsafe?.user?.first_name || "Гость",
};

// ═══════════════════════════════════════════════════════════════
// УТИЛИТЫ
// ═══════════════════════════════════════════════════════════════
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

/** Показывает нужную секцию, скрывая остальные */
function showSection(sectionId) {
    $$(".section").forEach((sec) => sec.classList.add("hidden"));
    const target = $(`#${sectionId}`);
    if (target) {
        target.classList.remove("hidden");
        target.style.animation = "none";
        target.offsetHeight; // reflow
        target.style.animation = "";
    }
    AppState.currentScreen = sectionId;

    // Скрываем MainButton при переходах
    if (tg?.MainButton) tg.MainButton.hide();
}

/** Haptic feedback */
function haptic(type = "success") {
    if (!tg?.HapticFeedback) return;
    try {
        if (type === "success") {
            tg.HapticFeedback.notificationOccurred("success");
        } else if (type === "error") {
            tg.HapticFeedback.notificationOccurred("error");
        } else if (type === "warning") {
            tg.HapticFeedback.notificationOccurred("warning");
        } else if (type === "impact") {
            tg.HapticFeedback.impactOccurred("medium");
        } else if (type === "light") {
            tg.HapticFeedback.impactOccurred("light");
        }
    } catch (_) { /* ignore */ }
}

/** Применение темы Telegram */
function applyTelegramTheme() {
    if (!tg?.themeParams) return;
    const root = document.documentElement;
    const t = tg.themeParams;

    const vars = {
        "--tg-theme-bg-color":           t.bg_color           || "#1a1a2e",
        "--tg-theme-text-color":         t.text_color         || "#eaeaea",
        "--tg-theme-button-color":       t.button_color       || "#6c5ce7",
        "--tg-theme-button-text-color":  t.button_text_color  || "#ffffff",
        "--tg-theme-secondary-bg-color": t.secondary_bg_color || "#16213e",
        "--tg-theme-hint-color":         t.hint_color         || "#a0a0a0",
        "--tg-theme-link-color":         t.link_color         || "#6c5ce7",
        "--tg-theme-destructive-color":  t.destructive_text_color || "#d63031",
    };
    Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
}

// ═══════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════
const API = {
    baseUrl: "",

    async getDecks() {
        try {
            const resp = await fetch(`${this.baseUrl}/api/tarot/decks`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.error("Ошибка загрузки колод:", err);
            // Fallback: демо-данные
            return [
                { deck_id: "rider_waite",    name: "Таро Райдера-Уэйта",          cards_count: 78 },
                { deck_id: "thoth",           name: "Таро Тота (Кроули)",           cards_count: 78 },
                { deck_id: "author_deck",     name: "Авторская «12 Планет»",         cards_count: 78 },
                { deck_id: "author_deck_146", name: "Оракул «12 Планет»",            cards_count: 146 },
            ];
        }
    },

    async drawCards(deckId, count, spreadType) {
        const resp = await fetch(`${this.baseUrl}/api/tarot/draw`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                deck_id:     deckId,
                count:       count,
                spread_type: spreadType,
                user_id:     AppState.userId,
            }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    },

    async sendWebAppData(data) {
        try {
            const resp = await fetch(`${this.baseUrl}/api/webapp/data`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...data, user_id: AppState.userId }),
            });
            return resp.ok;
        } catch (err) {
            console.error("Ошибка отправки данных:", err);
            return false;
        }
    },
};

// ═══════════════════════════════════════════════════════════════
// ЗАГРУЗКА КОЛОД
// ═══════════════════════════════════════════════════════════════
async function loadDecks() {
    AppState.decks = await API.getDecks();
    renderDecksList();
}

function renderDecksList() {
    const container = $("#decks-list");
    if (!container) return;

    container.innerHTML = AppState.decks
        .filter((d) => d.cards_count > 0)
        .map((deck) => `
            <div class="deck-item" data-deck-id="${deck.deck_id}">
                <div class="deck-item-info">
                    <strong>${deck.name}</strong>
                    <span class="deck-meta">${deck.cards_count} карт</span>
                </div>
                <span class="deck-arrow">→</span>
            </div>
        `)
        .join("");

    // Обработчики кликов
    container.querySelectorAll(".deck-item").forEach((item) => {
        item.addEventListener("click", () => {
            const deckId = item.dataset.deckId;
            selectDeck(deckId);
            haptic("light");
        });
    });
}

// ═══════════════════════════════════════════════════════════════
// ТАРО: ЛОГИКА
// ═══════════════════════════════════════════════════════════════

function selectSpread(spreadType) {
    const config = SPREAD_CONFIGS[spreadType];
    if (!config) return;

    AppState.currentSpread = spreadType;
    AppState.drawnCards = [];

    const title = $("#shuffle-title");
    if (title) title.textContent = `${config.emoji} ${config.name}`;

    showSection("deck-selection");
}

function selectDeck(deckId) {
    AppState.selectedDeck = deckId;
    showSection("shuffle-screen");
    resetShuffleScreen();
}

function resetShuffleScreen() {
    const deckVisual = $("#deck-visual");
    if (deckVisual) deckVisual.classList.remove("shuffling");

    const shuffleBtn = $("#shuffle-btn");
    const drawBtn    = $("#draw-cards-btn");

    if (shuffleBtn) shuffleBtn.classList.remove("hidden");
    if (drawBtn)    drawBtn.classList.add("hidden");

    AppState.isShuffling = false;
    AppState.isDrawing   = false;
}

async function shuffleDeck() {
    if (AppState.isShuffling) return;
    AppState.isShuffling = true;

    haptic("impact");

    const deckVisual = $("#deck-visual");
    if (deckVisual) deckVisual.classList.add("shuffling");

    // Анимация перемешивания
    await sleep(1800);

    AppState.isShuffling = false;
    if (deckVisual) deckVisual.classList.remove("shuffling");

    const shuffleBtn = $("#shuffle-btn");
    const drawBtn    = $("#draw-cards-btn");

    if (shuffleBtn) shuffleBtn.classList.add("hidden");
    if (drawBtn)    drawBtn.classList.remove("hidden");

    haptic("success");
}

async function drawCards() {
    if (AppState.isDrawing) return;
    AppState.isDrawing = true;

    const config = SPREAD_CONFIGS[AppState.currentSpread];
    if (!config) return;

    haptic("impact");
    if (tg) tg.showLoading();

    try {
        const result = await API.drawCards(
            AppState.selectedDeck,
            config.count,
            AppState.currentSpread,
        );

        AppState.drawnCards = result.cards || [];

        renderCardsResult(AppState.drawnCards, config.positions);
        showSection("result-screen");

        haptic("success");

        // Показываем MainButton для отправки
        if (tg?.MainButton) {
            tg.MainButton.setText("✅ Отправить в бот");
            tg.MainButton.show();
        }
    } catch (err) {
        console.error("Ошибка вытягивания карт:", err);
        haptic("error");

        if (tg) {
            tg.showPopup({
                title:   "⚠️ Ошибка",
                message: "Не удалось вытянуть карты. Попробуйте ещё раз.",
                buttons: [{ type: "ok" }],
            });
        }
    } finally {
        AppState.isDrawing = false;
        if (tg) tg.hideLoading();
    }
}

function renderCardsResult(cards, positions) {
    const container = $("#cards-result");
    if (!container) return;

    container.innerHTML = cards.map((card, index) => {
        const posLabel   = positions[index] || `Позиция ${index + 1}`;
        const reversed   = card.reversed;
        const animDelay  = index * 0.12;

        let imageHtml = "";
        if (card.image_url) {
            imageHtml = `<img src="${card.image_url}" alt="${card.name}" loading="lazy">`;
        } else {
            imageHtml = `<div class="card-placeholder">🎴</div>`;
        }

        return `
            <div class="card-result ${reversed ? "reversed" : ""}"
                 style="animation-delay: ${animDelay}s">
                ${imageHtml}
                <div class="card-info">
                    <div class="card-name">${card.name}</div>
                    <div class="card-reversed">${reversed ? "🔻 перевёрнута" : "✅ прямо"}</div>
                    <div class="card-position">${posLabel}</div>
                    ${card.astrology ? `<div class="card-astro">🪐 ${card.astrology}</div>` : ""}
                </div>
            </div>
        `;
    }).join("");
}

// ═══════════════════════════════════════════════════════════════
// ОТПРАВКА ДАННЫХ В БОТ
// ═══════════════════════════════════════════════════════════════
async function sendToBot() {
    if (AppState.drawnCards.length === 0) {
        if (tg) tg.showAlert("Сначала вытяните карты!");
        return;
    }

    haptic("success");

    const payload = {
        action:      "tarot_spread",
        spread_type: AppState.currentSpread,
        deck_id:     AppState.selectedDeck,
        cards:       AppState.drawnCards,
        timestamp:   Date.now(),
    };

    // 1. Отправляем через Telegram WebApp API (основной канал)
    if (tg?.sendData) {
        tg.sendData(JSON.stringify(payload));
    }

    // 2. Дублируем на наш API (резервный канал)
    await API.sendWebAppData(payload);

    // Подтверждение
    if (tg?.showPopup) {
        tg.showPopup({
            title:   "✅ Отправлено!",
            message: "Расклад отправлен боту. Ожидайте интерпретацию в чате.",
            buttons: [{ type: "ok" }],
        });
    }

    // Скрываем MainButton
    if (tg?.MainButton) tg.MainButton.hide();
}

// ═══════════════════════════════════════════════════════════════
// АСТРОЛОГИЯ: ЛОГИКА
// ═══════════════════════════════════════════════════════════════

function showAstrologyInput() {
    showSection("astrology-input");
    populateAstroForm();
}

function populateAstroForm() {
    const form = $("#astrology-form");
    if (!form || form.dataset.populated) return;

    // Заполняем select-ы данными
    const selects = {
        "planet1":     ASTRO_DATA.planets,
        "planet2":     ASTRO_DATA.planets,
        "sign1":       ASTRO_DATA.signs,
        "sign2":       ASTRO_DATA.signs,
        "aspect-type": ASTRO_DATA.aspects,
    };

    Object.entries(selects).forEach(([id, options]) => {
        const select = $(`#${id}`);
        if (!select) return;

        // Сохраняем первый option (placeholder)
        const placeholder = select.querySelector('option[value=""]');
        select.innerHTML = "";
        if (placeholder) select.appendChild(placeholder);

        options.forEach((opt) => {
            const el = document.createElement("option");
            el.value = opt.value;
            el.textContent = opt.label;
            select.appendChild(el);
        });
    });

    form.dataset.populated = "true";
}

async function handleAstrologySubmit(e) {
    e.preventDefault();

    const planet1    = $("#planet1")?.value;
    const sign1      = $("#sign1")?.value;
    const aspectType = $("#aspect-type")?.value;
    const planet2    = $("#planet2")?.value;
    const sign2      = $("#sign2")?.value;

    // Валидация
    if (!planet1 || !sign1 || !aspectType || !planet2 || !sign2) {
        haptic("error");
        if (tg) tg.showAlert("Заполните все поля!");
        return;
    }

    haptic("success");

    // Формируем текст запроса
    const aspectNames = {
        conjunction: "Соединение",
        sextile:     "Секстиль",
        square:      "Квадрат",
        trine:       "Трин",
        opposition:  "Оппозиция",
        quincunx:    "Квиконс",
    };

    const queryText =
        `${aspectNames[aspectType]} между ` +
        `${planet1} в ${sign1} и ${planet2} в ${sign2}`;

    const payload = {
        action:    "astrology_aspect",
        query:     queryText,
        details:   { planet1, sign1, aspectType, planet2, sign2 },
        timestamp: Date.now(),
    };

    // Отправка в бот
    if (tg?.sendData) {
        tg.sendData(JSON.stringify(payload));
    }
    await API.sendWebAppData(payload);

    if (tg?.showPopup) {
        tg.showPopup({
            title:   "🪐 Отправлено!",
            message: "Данные аспекта отправлены боту. Ожидайте интерпретацию.",
            buttons: [{ type: "ok" }],
        });
    }
}

// ═══════════════════════════════════════════════════════════════
// ОБРАБОТЧИКИ СОБЫТИЙ
// ═══════════════════════════════════════════════════════════════
function setupEventListeners() {
    // ── Кнопки выбора расклада ──
    $$("[data-spread]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            selectSpread(e.target.dataset.spread);
            haptic("light");
        });
    });

    // ── Навигация ──
    $("#back-to-spread")?.addEventListener("click", () => {
        showSection("spread-selection");
        haptic("light");
    });

    // ── Таро: перемешивание и вытягивание ──
    $("#shuffle-btn")?.addEventListener("click", shuffleDeck);
    $("#draw-cards-btn")?.addEventListener("click", drawCards);

    // ── Результат ──
    $("#send-to-bot")?.addEventListener("click", sendToBot);
    $("#retry-spread")?.addEventListener("click", () => {
        AppState.drawnCards = [];
        showSection("shuffle-screen");
        resetShuffleScreen();
        haptic("light");
    });

    // ── Астрология ──
    $("#astrology-form")?.addEventListener("submit", handleAstrologySubmit);
    $("#astro-back-btn")?.addEventListener("click", () => {
        showSection("spread-selection");
        haptic("light");
    });

    // ── Telegram MainButton ──
    if (tg?.MainButton) {
        tg.MainButton.onClick(sendToBot);
    }

    // ── Обработка данных от Telegram WebApp ──
    if (tg?.onEvent) {
        tg.onEvent("webAppData", () => {
            // Данные уже отправлены через sendData
        });
    }
}

// ═══════════════════════════════════════════════════════════════
// ИНИЦИАЛИЗАЦИЯ
// ═══════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", async () => {
    applyTelegramTheme();
    setupEventListeners();
    await loadDecks();

    console.log(
        "%c🔮 Astro12AI Mini App loaded",
        "color: #6c5ce7; font-size: 14px; font-weight: bold;",
    );
    console.log(`   User: ${AppState.userName} (${AppState.userId})`);
    console.log(`   Decks: ${AppState.decks.length}`);
});

// ═══════════════════════════════════════════════════════════════
// ЭКСПОРТ (для отладки в консоли)
// ═══════════════════════════════════════════════════════════════
window.Astro12AI = {
    state:       AppState,
    config:      SPREAD_CONFIGS,
    sendToBot,
    showSection,
    drawCards,
    shuffleDeck,
};