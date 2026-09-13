/**
 * Astro12AI Mini App — Таро «12 Планет»
 * Без tg.showLoading/showProgress (их нет в Telegram) — загрузка через DOM.
 */
(function () {
  'use strict';

  const tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;

  // ===== Состояние =====
  const state = {
    screen: 'spread-type',
    spreadType: null,
    threeType: null,
    deckId: null,
    deckName: null,
    useReversed: true,
    question: '',
    cards: [],
    interpretation: null
  };
  let navHistory = [];
  let decks = [];

  const SPREADS = {
    one:    { name: 'Одна карта',      count: 1,  positions: ['Карта дня'] },
    three:  { name: 'Три карты',       count: 3,  positions: ['Прошлое', 'Настоящее', 'Будущее'] },
    celtic: { name: 'Кельтский крест', count: 10, positions: ['Суть', 'Препятствие', 'Цель', 'Корни', 'Прошлое', 'Будущее', 'Я', 'Окружение', 'Надежды/страхи', 'Итог'] },
    choice: { name: 'Выбор пути',      count: 7,  positions: ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход', 'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'] },
    yesno:  { name: 'Да или Нет',      count: 1,  positions: ['Ответ'] }
  };
  const THREE_TYPES = {
    'past-present-future':       ['Прошлое', 'Настоящее', 'Будущее'],
    'thoughts-feelings-actions': ['Мысли', 'Чувства', 'Действия'],
    'plus-minus-result':         ['Плюс', 'Минус', 'Итог']
  };
  const FALLBACK_DECKS = [
    { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 },
    { deck_id: 'author_deck',     name: 'Авторская колода Школы', cards_count: 78 },
    { deck_id: 'rider_waite',     name: 'Таро Райдера-Уэйта', cards_count: 78 },
    { deck_id: 'thoth',           name: 'Таро Тота', cards_count: 78 }
  ];

  // ===== Утилиты =====
  const $ = (id) => document.getElementById(id);

  function haptic(type) {
    try {
      if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.impactOccurred === 'function') {
        tg.HapticFeedback.impactOccurred(type || 'light');
      }
    } catch (e) {}
  }
  function showAlert(message) {
    try {
      if (tg && typeof tg.showAlert === 'function') { tg.showAlert(message); return; }
    } catch (e) {}
    try { alert(message); } catch (e) {}
  }
  function showLoading(text) {
    const o = $('loading-overlay'), t = $('loading-text');
    if (o) { if (t) t.textContent = text || 'Загрузка…'; o.classList.remove('hidden'); }
  }
  function hideLoading() {
    const o = $('loading-overlay');
    if (o) o.classList.add('hidden');
  }
  function getPositions() {
    if (state.spreadType === 'three') {
      return THREE_TYPES[state.threeType] || THREE_TYPES['past-present-future'];
    }
    return (SPREADS[state.spreadType] || SPREADS.one).positions;
  }

  // ===== Навигация =====
  function showScreen(id) {
    state.screen = id;
    document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
    const t = $('screen-' + id);
    if (t) t.classList.add('active');
    window.scrollTo(0, 0);
  }
  function navigateTo(id) { navHistory.push(state.screen); showScreen(id); }
  function goBack() {
    haptic('light');
    if (navHistory.length) showScreen(navHistory.pop());
    else goMainMenu();
  }
  function goMainMenu() {
    haptic('light');
    navHistory = [];
    resetState();
    showScreen('spread-type');
  }
  function resetState() {
    state.spreadType = null; state.threeType = null;
    state.deckId = null; state.deckName = null;
    state.question = ''; state.cards = []; state.interpretation = null;
    const q = $('question-input'); if (q) q.value = '';
    const rc = $('result-cards'); if (rc) rc.innerHTML = '';
    const it = $('interpretation-text'); if (it) { it.textContent = ''; it.classList.remove('error'); }
    const ib = $('interpretation-box'); if (ib) ib.classList.add('hidden');
    const sb = $('shuffle-btn'), db = $('draw-btn');
    if (sb) sb.classList.remove('hidden');
    if (db) db.classList.add('hidden');
  }

  // ===== Колоды =====
  function renderDecks(list) {
    const box = $('deck-list');
    if (!box) return;
    box.innerHTML = '';
    list.filter(d => d.cards_count > 0).forEach(d => {
      const b = document.createElement('button');
      b.className = 'option-row deck-option';
      b.type = 'button';
      b.innerHTML = `<span class="text">${d.name}</span><span class="subtext">${d.cards_count} карт</span>`;
      b.addEventListener('click', () => {
        state.deckId = d.deck_id; state.deckName = d.name;
        haptic('success'); navigateTo('reverse');
      });
      box.appendChild(b);
    });
  }
  async function loadDecks() {
    try {
      const r = await fetch('/api/tarot/decks');
      if (!r.ok) throw new Error('http ' + r.status);
      const data = await r.json();
      decks = Array.isArray(data) && data.length ? data : FALLBACK_DECKS;
    } catch (e) { decks = FALLBACK_DECKS; }
    renderDecks(decks);
  }

  // ===== Вытягивание =====
  async function drawCards() {
    const cfg = SPREADS[state.spreadType] || SPREADS.one;
    if (!state.deckId) { showAlert('Сначала выберите колоду.'); return; }
    showLoading('Вытягиваем карты…');
    try {
      const r = await fetch('/api/tarot/draw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deck_id: state.deckId,
          count: cfg.count,
          spread_type: state.spreadType,
          use_reversed: state.useReversed
        })
      });
      if (!r.ok) throw new Error('http ' + r.status);
      const data = await r.json();
      state.cards = Array.isArray(data.cards) ? data.cards : [];
      if (!state.cards.length) throw new Error('empty');
      renderResult();
      navigateTo('result');
    } catch (e) {
      console.error('draw error', e);
      showAlert('Не удалось вытянуть карты. Попробуйте ещё раз.');
    } finally { hideLoading(); }
  }

  function renderResult() {
    const box = $('result-cards');
    if (!box) return;
    box.innerHTML = '';
    const positions = getPositions();
    state.cards.forEach((card, i) => {
      const el = document.createElement('div');
      el.className = 'tarot-card-item' + (card.reversed ? ' reversed' : '');
      const imgUrl = card.image_url || card.image || null;
      if (imgUrl) {
        const img = document.createElement('img');
        img.className = 'card-image';
        img.alt = card.name || '';
        img.src = imgUrl;
        img.onerror = function () {
          const ph = document.createElement('div');
          ph.className = 'card-image card-placeholder';
          ph.textContent = '🎴';
          img.replaceWith(ph);
        };
        el.appendChild(img);
      } else {
        const ph = document.createElement('div');
        ph.className = 'card-image card-placeholder';
        ph.textContent = '🎴';
        el.appendChild(ph);
      }
      const name = document.createElement('div');
      name.className = 'card-name';
      name.textContent = card.name || '';
      el.appendChild(name);
      const pos = document.createElement('div');
      pos.className = 'card-pos';
      pos.textContent = positions[i] || ('Позиция ' + (i + 1));
      el.appendChild(pos);
      box.appendChild(el);
    });
  }

  // ===== Толкование (в приложении) =====
  async function getInterpretation() {
    if (!state.cards.length) { showAlert('Сначала вытяните карты.'); return; }
    navigateTo('interpretation');
    const box = $('interpretation-box'), text = $('interpretation-text');
    if (box) box.classList.remove('hidden');
    if (text) { text.classList.remove('error'); text.textContent = 'Звезды шепчут ответ…'; }
    showLoading('Получаем толкование…');
    try {
      const r = await fetch('/api/tarot/interpret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deck_id: state.deckId,
          spread_type: state.spreadType,
          three_card_type: state.threeType,
          question: state.question,
          cards: state.cards.map(c => ({
            card_id: c.card_id, name: c.name, reversed: !!c.reversed,
            astrology: c.astrology || '', keywords: c.keywords || []
          })),
          positions: getPositions(),
          use_reversed: state.useReversed
        })
      });
      if (!r.ok) throw new Error('http ' + r.status);
      const data = await r.json();
      const textValue = data.interpretation || data.text || data.result || '';
      if (!textValue) throw new Error('empty');
      state.interpretation = textValue;
      if (text) { text.textContent = textValue; text.classList.remove('error'); }
    } catch (e) {
      console.error('interpret error', e);
      if (text) {
        text.textContent = 'Не удалось получить толкование. Нажмите «Отправить в бот», чтобы получить ответ в чате.';
        text.classList.add('error');
      }
    } finally { hideLoading(); }
  }

  // ===== Отправка в бот (резерв) =====
  function sendToBot() {
    if (!state.cards.length) { showAlert('Нет данных для отправки.'); return; }
    const payload = {
      action: 'tarot_spread',
      spread_type: state.spreadType,
      deck_id: state.deckId,
      question: state.question,
      cards: state.cards.map(c => ({ card_id: c.card_id, name: c.name, reversed: !!c.reversed })),
      timestamp: Date.now()
    };
    try {
      if (tg && typeof tg.sendData === 'function') {
        tg.sendData(JSON.stringify(payload));
        showAlert('Данные отправлены в бот.');
        setTimeout(() => { try { tg.close(); } catch (e) {} }, 800);
      } else { showAlert('Отправка доступна только внутри Telegram.'); }
    } catch (e) { showAlert('Не удалось отправить данные.'); }
  }

  // ===== Астрология =====
  const PLANETS = ['Солнце','Луна','Меркурий','Венера','Марс','Юпитер','Сатурн','Уран','Нептун','Плутон','Эрида','Церера'];
  const SIGNS = ['Овен','Телец','Близнецы','Рак','Лев','Дева','Весы','Скорпион','Стрелец','Козерог','Водолей','Рыбы'];
  const ASPECTS = [
    { id: 'conjunction', name: 'Соединение (0°)' },
    { id: 'sextile',     name: 'Секстиль (60°)' },
    { id: 'square',      name: 'Квадрат (90°)' },
    { id: 'trine',       name: 'Трин (120°)' },
    { id: 'opposition',  name: 'Оппозиция (180°)' },
    { id: 'quincunx',    name: 'Квиконс (150°)' }
  ];
  function fillSelect(id, items) {
    const sel = $(id); if (!sel) return;
    sel.innerHTML = '<option value="">Выберите…</option>';
    items.forEach(it => {
      const o = document.createElement('option');
      if (typeof it === 'string') { o.value = it; o.textContent = it; }
      else { o.value = it.id; o.textContent = it.name; }
      sel.appendChild(o);
    });
  }
  function submitAstro(e) {
    e.preventDefault();
    const p1 = $('planet1').value, s1 = $('sign1').value, a = $('aspect-type').value,
          p2 = $('planet2').value, s2 = $('sign2').value;
    if (!p1 || !s1 || !a || !p2 || !s2) { showAlert('Заполните все поля.'); return; }
    const aName = (ASPECTS.find(x => x.id === a) || {}).name || a;
    const payload = {
      action: 'astrology_aspect',
      query: `${aName}: ${p1} в ${s1} и ${p2} в ${s2}`,
      timestamp: Date.now()
    };
    try {
      if (tg && typeof tg.sendData === 'function') {
        tg.sendData(JSON.stringify(payload));
        showAlert('Данные отправлены в бот.');
        setTimeout(() => { try { tg.close(); } catch (e2) {} }, 800);
      } else { showAlert('Отправка доступна только внутри Telegram.'); }
    } catch (e2) { showAlert('Не удалось отправить данные.'); }
  }

  // ===== Инициализация =====
  function init() {
    try { if (tg && tg.ready) tg.ready(); if (tg && tg.expand) tg.expand(); } catch (e) {}

    // Загрузка сохранённой настройки перевёрнутых
    try {
      const saved = localStorage.getItem('astro12_use_reversed');
      if (saved !== null) state.useReversed = saved === '1';
    } catch (e) {}

    loadDecks();
    fillSelect('planet1', PLANETS); fillSelect('planet2', PLANETS);
    fillSelect('sign1', SIGNS);     fillSelect('sign2', SIGNS);
    fillSelect('aspect-type', ASPECTS);

    // Выбор расклада
    document.querySelectorAll('.spread-option').forEach(btn => {
      btn.addEventListener('click', () => {
        state.spreadType = btn.dataset.spread;
        haptic('success');
        if (state.spreadType === 'three') navigateTo('three-type');
        else navigateTo('deck');
      });
    });
    // Подтип трёх карт
    document.querySelectorAll('.three-type-option').forEach(btn => {
      btn.addEventListener('click', () => {
        state.threeType = btn.dataset.three;
        haptic('success'); navigateTo('deck');
      });
    });
    // Перевёрнутые
    document.querySelectorAll('.reverse-option').forEach(btn => {
      btn.addEventListener('click', () => {
        state.useReversed = btn.dataset.reversed === 'yes';
        try { localStorage.setItem('astro12_use_reversed', state.useReversed ? '1' : '0'); } catch (e) {}
        haptic('success'); navigateTo('question');
      });
    });
    // Вопрос
    const qSubmit = $('question-submit-btn');
    if (qSubmit) qSubmit.addEventListener('click', () => {
      const q = ($('question-input').value || '').trim();
      if (q.length < 3) { showAlert('Опишите вопрос подробнее.'); return; }
      state.question = q;
      haptic('success'); navigateTo('shuffle');
    });
    // Перемешать / вытянуть
    const shuffleBtn = $('shuffle-btn');
    if (shuffleBtn) shuffleBtn.addEventListener('click', () => {
      haptic('heavy');
      const stack = $('card-stack');
      if (stack) { stack.classList.add('shuffling'); setTimeout(() => stack.classList.remove('shuffling'), 800); }
      showAlert('Колода перемешана. Сосредоточьтесь на вопросе.');
      shuffleBtn.classList.add('hidden');
      const db = $('draw-btn'); if (db) db.classList.remove('hidden');
    });
    const drawBtn = $('draw-btn');
    if (drawBtn) drawBtn.addEventListener('click', drawCards);
    // Толкование / повтор / в бот
    const interpretBtn = $('interpret-btn');
    if (interpretBtn) interpretBtn.addEventListener('click', getInterpretation);
    const redrawBtn = $('redraw-btn');
    if (redrawBtn) redrawBtn.addEventListener('click', () => { haptic('warning'); state.cards = []; const rc = $('result-cards'); if (rc) rc.innerHTML = ''; navigateTo('shuffle'); });
    const backToCards = $('back-to-cards-btn');
    if (backToCards) backToCards.addEventListener('click', () => navigateTo('result'));
    const sendBotBtn = $('send-to-bot-btn');
    if (sendBotBtn) sendBotBtn.addEventListener('click', sendToBot);
    // Астрология
    const astroOpen = $('astro-open-btn');
    if (astroOpen) astroOpen.addEventListener('click', () => navigateTo('astro'));
    const astroForm = $('astro-form');
    if (astroForm) astroForm.addEventListener('submit', submitAstro);
    // Навигация: назад / главное меню
    document.querySelectorAll('.back-btn').forEach(b => b.addEventListener('click', goBack));
    document.querySelectorAll('.home-btn').forEach(b => b.addEventListener('click', goMainMenu));

    showScreen('spread-type');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();