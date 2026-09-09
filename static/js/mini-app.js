/**
 * Astro12AI Mini App — логика.
 * Исправлено: CELTIC_CROSS_POSITIONS объявлен ДО использования (ранее был ReferenceError).
 */
(function () {
  'use strict';

  const tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;

  // ВАЖНО: константа объявлена до SPREAD_CONFIGS
  const CELTIC_CROSS_POSITIONS = [
    'Суть (сигнификатор)', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
    'Ближайшее будущее', 'Я (самовосприятие)', 'Окружение',
    'Надежды и страхи', 'Итог'
  ];

  const SPREAD_CONFIGS = {
    one:    { name: 'Одна карта',      count: 1,  positions: ['Карта дня'] },
    three:  { name: 'Три карты',       count: 3,  positions: ['Прошлое', 'Настоящее', 'Будущее'] },
    choice: { name: 'Выбор пути',      count: 7,  positions: ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход', 'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'] },
    celtic: { name: 'Кельтский крест', count: 10, positions: CELTIC_CROSS_POSITIONS }
  };

  const AppState = {
    currentSpread: null,
    selectedDeck: null,
    decks: [],
    drawnCards: [],
    isShuffling: false,
    isDrawing: false
  };

  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function haptic(type) {
    if (!tg || !tg.HapticFeedback) return;
    try {
      if (type === 'success' || type === 'error' || type === 'warning') {
        tg.HapticFeedback.notificationOccurred(type);
      } else {
        tg.HapticFeedback.impactOccurred('light');
      }
    } catch (e) { /* ignore */ }
  }

  function applyTheme() {
    if (!tg || !tg.themeParams) return;
    const root = document.documentElement;
    const t = tg.themeParams;
    const map = {
      '--tg-theme-bg-color': t.bg_color,
      '--tg-theme-text-color': t.text_color,
      '--tg-theme-button-color': t.button_color,
      '--tg-theme-button-text-color': t.button_text_color,
      '--tg-theme-secondary-bg-color': t.secondary_bg_color,
      '--tg-theme-hint-color': t.hint_color
    };
    Object.keys(map).forEach((k) => {
      if (map[k]) root.style.setProperty(k, map[k]);
    });
  }

  function showSection(id) {
    document.querySelectorAll('.section').forEach((s) => s.classList.add('hidden'));
    const el = $(id);
    if (el) el.classList.remove('hidden');
    if (tg && tg.MainButton) {
      if (id === 'result-screen' && AppState.drawnCards.length) tg.MainButton.show();
      else tg.MainButton.hide();
    }
  }

  function deckName() {
    const d = AppState.decks.find((x) => x.deck_id === AppState.selectedDeck);
    return d ? d.name : '';
  }

  // ---------- колоды ----------
  async function loadDecks() {
    try {
      const resp = await fetch('/api/tarot/decks');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      AppState.decks = await resp.json();
    } catch (e) {
      AppState.decks = [
        { deck_id: 'rider_waite', name: 'Таро Райдера-Уэйта', cards_count: 78 },
        { deck_id: 'thoth', name: 'Таро Тота', cards_count: 78 },
        { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 }
      ];
    }
    renderDecks();
  }

  function renderDecks() {
    const list = $('decks-list');
    list.innerHTML = '';
    AppState.decks.filter((d) => d.cards_count > 0).forEach((d) => {
      const item = document.createElement('div');
      item.className = 'deck-item';
      item.innerHTML = '<strong>' + escapeHtml(d.name) + '</strong>' +
                       '<span class="deck-count">' + d.cards_count + ' карт</span>';
      item.addEventListener('click', () => {
        AppState.selectedDeck = d.deck_id;
        goShuffle();
        haptic('light');
      });
      list.appendChild(item);
    });
  }

  // ---------- перемешивание / вытягивание ----------
  function goShuffle() {
    showSection('shuffle-screen');
    resetShuffle();
  }

  function resetShuffle() {
    AppState.drawnCards = [];
    $('draw-cards-btn').classList.add('hidden');
    $('shuffle-btn').classList.remove('hidden');
    $('deck-visual').classList.remove('shuffling');
    const cfg = SPREAD_CONFIGS[AppState.currentSpread] || SPREAD_CONFIGS.one;
    $('shuffle-title').textContent = cfg.name + ' · ' + deckName();
  }

  async function shuffle() {
    if (AppState.isShuffling) return;
    AppState.isShuffling = true;
    haptic('impact');
    $('deck-visual').classList.add('shuffling');
    await sleep(1200);
    $('deck-visual').classList.remove('shuffling');
    $('shuffle-btn').classList.add('hidden');
    $('draw-cards-btn').classList.remove('hidden');
    AppState.isShuffling = false;
    haptic('success');
  }

  async function drawCards() {
    if (AppState.isDrawing) return;
    const cfg = SPREAD_CONFIGS[AppState.currentSpread] || SPREAD_CONFIGS.one;
    AppState.isDrawing = true;
    if (tg) tg.showProgress();
    try {
      const resp = await fetch('/api/tarot/draw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deck_id: AppState.selectedDeck,
          count: cfg.count,
          spread_type: AppState.currentSpread
        })
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      AppState.drawnCards = data.cards || [];
      if (!AppState.drawnCards.length) throw new Error('Нет карт');
      renderResults();
      showSection('result-screen');
      haptic('success');
    } catch (e) {
      if (tg) tg.showAlert('Не удалось вытянуть карты: ' + e.message);
    } finally {
      if (tg) tg.hideProgress();
      AppState.isDrawing = false;
    }
  }

  function renderResults() {
    const cfg = SPREAD_CONFIGS[AppState.currentSpread] || SPREAD_CONFIGS.one;
    const wrap = $('cards-result');
    wrap.innerHTML = '';
    AppState.drawnCards.forEach((card, i) => {
      const el = document.createElement('div');
      el.className = 'card-result' + (card.reversed ? ' reversed' : '');
      el.style.animationDelay = (i * 0.08) + 's';
      const img = card.image_url
        ? '<img src="' + card.image_url + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">'
        : '<div class="card-placeholder">🎴</div>';
      el.innerHTML = img +
        '<div class="card-name">' + escapeHtml(card.name) + '</div>' +
        '<div class="card-orient">' + (card.reversed ? '🔻 перевёрнуто' : '✅ прямо') + '</div>' +
        '<div class="card-pos">' + escapeHtml(cfg.positions[i] || ('Позиция ' + (i + 1))) + '</div>';
      wrap.appendChild(el);
    });
  }

  // ---------- отправка в бот ----------
  function sendToBot() {
    if (!AppState.drawnCards.length) {
      if (tg) tg.showAlert('Сначала вытяните карты!');
      return;
    }
    const payload = {
      action: 'tarot_spread',
      spread_type: AppState.currentSpread,
      deck_id: AppState.selectedDeck,
      cards: AppState.drawnCards.map((c) => ({
        card_id: c.card_id,
        reversed: !!c.reversed
      })),
      timestamp: Date.now()
    };
    if (tg && tg.sendData) {
      tg.sendData(JSON.stringify(payload));
      tg.showPopup({
        title: '✅ Отправлено!',
        message: 'Расклад отправлен в чат бота.',
        buttons: [{ type: 'ok' }]
      });
      tg.close();
    } else {
      fetch('/api/webapp/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(() => alert('Данные отправлены (вне Telegram).'))
        .catch((e) => alert('Ошибка: ' + e.message));
    }
  }

  // ---------- астрология ----------
  function submitAstro(e) {
    e.preventDefault();
    const p1 = $('planet1').value, s1 = $('sign1').value;
    const a = $('aspect-type').value;
    const p2 = $('planet2').value, s2 = $('sign2').value;
    if (!p1 || !s1 || !a || !p2 || !s2) {
      if (tg) tg.showAlert('Заполните все поля!');
      return;
    }
    const aspectNames = {
      conjunction: 'Соединение', sextile: 'Секстиль', square: 'Квадрат',
      trine: 'Трин', opposition: 'Оппозиция', quincunx: 'Квиконс'
    };
    const query = aspectNames[a] + ': ' + p1 + ' в ' + s1 + ' и ' + p2 + ' в ' + s2;
    const payload = {
      action: 'astrology_aspect',
      query: query,
      details: { planet1: p1, sign1: s1, aspect: a, planet2: p2, sign2: s2 },
      timestamp: Date.now()
    };
    if (tg && tg.sendData) {
      tg.sendData(JSON.stringify(payload));
      tg.showPopup({
        title: '🪐 Отправлено!',
        message: 'Запрос отправлен в чат бота.',
        buttons: [{ type: 'ok' }]
      });
      tg.close();
    } else {
      fetch('/api/webapp/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(() => alert('Данные отправлены (вне Telegram).'))
        .catch((e) => alert('Ошибка: ' + e.message));
    }
  }

  // ---------- инициализация ----------
  document.addEventListener('DOMContentLoaded', () => {
    if (tg) {
      tg.ready();
      tg.expand();
      applyTheme();
      tg.MainButton.setText('✅ Отправить в бот');
      tg.MainButton.onClick(sendToBot);
    }
    document.querySelectorAll('[data-spread]').forEach((btn) => {
      btn.addEventListener('click', () => {
        AppState.currentSpread = btn.dataset.spread;
        showSection('deck-selection');
        haptic('light');
      });
    });
    $('back-to-spread').addEventListener('click', () => showSection('spread-selection'));
    $('open-astro').addEventListener('click', () => showSection('astrology-input'));
    $('back-from-astro').addEventListener('click', () => showSection('spread-selection'));
    $('shuffle-btn').addEventListener('click', shuffle);
    $('draw-cards-btn').addEventListener('click', drawCards);
    $('retry-spread').addEventListener('click', () => { showSection('shuffle-screen'); resetShuffle(); });
    $('send-to-bot').addEventListener('click', sendToBot);
    $('astrology-form').addEventListener('submit', submitAstro);
    loadDecks();
  });
})();