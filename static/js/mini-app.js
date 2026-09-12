/**
 * Astro12AI Mini App — логика (production).
 * Поток: spread -> (three-type) -> deck -> reversed -> question -> shuffle -> result -> interpretation.
 * Все binding'и защищены от null. Telegram API вызывается только через безопасные обёртки.
 */
(function () {
  'use strict';

  var tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;

  // ---------- Безопасные обёртки Telegram ----------
  function tgInit() {
    if (!tg) return;
    try { tg.ready(); tg.expand(); } catch (e) {}
    try { if (tg.MainButton) tg.MainButton.hide(); } catch (e) {}
  }
  function showProgress() {
    if (tg && tg.MainButton && tg.MainButton.showProgress) { try { tg.MainButton.showProgress(); } catch (e) {} }
  }
  function hideProgress() {
    if (tg && tg.MainButton && tg.MainButton.hideProgress) { try { tg.MainButton.hideProgress(); } catch (e) {} }
  }
  function alertMsg(m) {
    if (tg && tg.showAlert) { try { tg.showAlert(m); } catch (e) {} }
    else { try { console.warn(m); } catch (e) {} }
  }
  function popupMsg(title, message) {
    if (tg && tg.showPopup) { try { tg.showPopup({ title: title, message: message, buttons: [{ type: 'ok' }] }); } catch (e) {} }
  }
  function haptic(t) {
    if (tg && tg.HapticFeedback) { try { tg.HapticFeedback.impactOccurred(t || 'light'); } catch (e) {} }
  }
  function closeApp() {
    if (tg && tg.close) { try { tg.close(); } catch (e) {} }
  }

  // ---------- Константы ----------
  var SPREAD_CONFIGS = {
    one:    { name: 'Одна карта',      count: 1,  positions: ['Карта дня'] },
    three:  { name: 'Три карты',       count: 3,  positions: null }, // позиции из threeCardType
    choice: { name: 'Выбор пути',      count: 7,  positions: ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход', 'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'] },
    celtic: { name: 'Кельтский крест', count: 10, positions: ['Суть (сигнификатор)', 'Препятствие', 'Цель', 'Корни', 'Прошлое', 'Ближайшее будущее', 'Я', 'Окружение', 'Надежды и страхи', 'Итог'] }
  };
  var THREE_POSITIONS = {
    'past-present-future':       ['Прошлое', 'Настоящее', 'Будущее'],
    'thoughts-feelings-actions': ['Мысли', 'Чувства', 'Действия'],
    'plus-minus-result':         ['Плюс', 'Минус', 'Итог']
  };
  var FALLBACK_DECKS = [
    { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 },
    { deck_id: 'rider_waite',     name: 'Таро Райдера-Уэйта', cards_count: 78 },
    { deck_id: 'thoth',           name: 'Таро Тота', cards_count: 78 },
    { deck_id: 'author_deck',     name: 'Авторская колода Школы', cards_count: 78 }
  ];

  var AppState = {
    screen: 'spread-selection',
    spread: null,
    threeCardType: null,
    deck: null,
    useReversed: true,
    question: '',
    drawn: [],
    decks: [],
    interpretation: null,
    isShuffling: false,
    isDrawing: false
  };

  function $(id) { return document.getElementById(id); }
  function on(id, ev, fn) {           // защищённый binding: null не падает
    var el = (typeof id === 'string') ? $(id) : id;
    if (el) el.addEventListener(ev, fn);
  }
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ---------- Экраны и навигация ----------
  function positionsFor() {
    if (AppState.spread === 'three') {
      return THREE_POSITIONS[AppState.threeCardType] || THREE_POSITIONS['past-present-future'];
    }
    return (SPREAD_CONFIGS[AppState.spread] || SPREAD_CONFIGS.one).positions;
  }

  function backTarget(screen) {
    switch (screen) {
      case 'three-card-type-selection': return 'spread-selection';
      case 'deck-selection':  return (AppState.spread === 'three') ? 'three-card-type-selection' : 'spread-selection';
      case 'reversed-setting': return 'deck-selection';
      case 'question-input':   return 'reversed-setting';
      case 'shuffle-screen':   return 'question-input';
      case 'result-screen':    return 'shuffle-screen';
      case 'interpretation-screen': return 'result-screen';
      case 'astrology-input':  return 'spread-selection';
      default: return null;
    }
  }

  function showScreen(name) {
    AppState.screen = name;
    var sections = document.querySelectorAll('.section');
    for (var i = 0; i < sections.length; i++) sections[i].classList.add('hidden');
    var target = $(name);
    if (target) target.classList.remove('hidden');
    if (tg && tg.BackButton) {
      try {
        if (name === 'spread-selection') tg.BackButton.hide();
        else tg.BackButton.show();
      } catch (e) {}
    }
    if (tg && tg.MainButton) { try { tg.MainButton.hide(); } catch (e) {} }
    try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) {}
  }

  function goBack() {
    var t = backTarget(AppState.screen);
    if (t) { showScreen(t); haptic('light'); }
  }

  function goMainMenu() {
    var payload = { action: 'main_menu', timestamp: Date.now() };
    if (tg && tg.sendData) { try { tg.sendData(JSON.stringify(payload)); } catch (e) {} }
    setTimeout(closeApp, 400);
  }

  // ---------- Колоды ----------
  function renderDecks() {
    var box = $('decks-list');
    if (!box) return;
    box.innerHTML = '';
    AppState.decks.forEach(function (d) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'deck-item';
      b.innerHTML = '<strong>' + escapeHtml(d.name) + '</strong>' +
                    '<span class="deck-count">' + escapeHtml(d.cards_count) + ' карт</span>';
      b.addEventListener('click', function () { selectDeck(d.deck_id); });
      box.appendChild(b);
    });
  }

  function loadDecks() {
    fetch('/api/tarot/decks')
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('http ' + r.status)); })
      .then(function (data) {
        AppState.decks = (Array.isArray(data) && data.length) ? data : FALLBACK_DECKS;
        renderDecks();
      })
      .catch(function () { AppState.decks = FALLBACK_DECKS; renderDecks(); });
  }

  // ---------- Шаги потока ----------
  function selectSpread(spreadType) {
    AppState.spread = spreadType;
    if (spreadType === 'three') { showScreen('three-card-type-selection'); }
    else { showScreen('deck-selection'); }
    haptic('light');
  }

  function selectThreeCardType(t) {
    AppState.threeCardType = t;
    showScreen('deck-selection');
    haptic('light');
  }

  function selectDeck(deckId) {
    AppState.deck = deckId;
    showScreen('reversed-setting');
    haptic('light');
  }

  function setReversed(use) {
    AppState.useReversed = use;
    try { localStorage.setItem('astro12_use_reversed', use ? '1' : '0'); } catch (e) {}
    var q = $('question-text');
    if (q) q.value = AppState.question || '';
    showScreen('question-input');
    haptic('light');
  }

  function resetShuffle() {
    AppState.drawn = [];
    var v = $('deck-visual');
    if (v) v.classList.remove('shuffling');
    var sh = $('shuffle-btn'); if (sh) { sh.classList.remove('hidden'); sh.disabled = false; }
    var dr = $('draw-cards-btn'); if (dr) { dr.classList.add('hidden'); dr.disabled = false; }
  }

  function shuffle() {
    if (AppState.isShuffling) return;
    AppState.isShuffling = true;
    haptic('light');
    var v = $('deck-visual');
    if (v) v.classList.add('shuffling');
    var sh = $('shuffle-btn'); if (sh) sh.disabled = true;
    setTimeout(function () {
      if (v) v.classList.remove('shuffling');
      if (sh) sh.classList.add('hidden');
      var dr = $('draw-cards-btn'); if (dr) dr.classList.remove('hidden');
      AppState.isShuffling = false;
      haptic('medium');
    }, 1200);
  }

  function draw() {
    if (AppState.isDrawing) return;
    var cfg = SPREAD_CONFIGS[AppState.spread] || SPREAD_CONFIGS.one;
    if (!AppState.deck) { alertMsg('Сначала выберите колоду.'); return; }
    AppState.isDrawing = true;
    var dr = $('draw-cards-btn'); if (dr) dr.disabled = true;
    showProgress();
    fetch('/api/tarot/draw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deck_id: AppState.deck,
        count: cfg.count,
        spread_type: AppState.spread,
        use_reversed: AppState.useReversed
      })
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('http ' + r.status)); })
      .then(function (data) {
        if (!data || !Array.isArray(data.cards) || !data.cards.length) throw new Error('empty');
        AppState.drawn = data.cards;
        renderResult();
        showScreen('result-screen');
        haptic('medium');
      })
      .catch(function (e) { alertMsg('Сервер недоступен. Повторите попытку через минуту.'); })
      .then(function () {
        hideProgress();
        if (dr) dr.disabled = false;
        AppState.isDrawing = false;
      });
  }

  function renderResult() {
    var box = $('cards-result');
    if (!box) return;
    var positions = positionsFor();
    box.innerHTML = '';
    AppState.drawn.forEach(function (c, i) {
      var el = document.createElement('div');
      el.className = 'card-result' + (c.reversed ? ' reversed' : '');
      el.style.animationDelay = (i * 0.1) + 's';
      var img = c.image_url
        ? '<img src="' + c.image_url + '" alt="' + escapeHtml(c.name) + '" onerror="this.style.display=\'none\'">'
        : '<div class="card-placeholder">🎴</div>';
      el.innerHTML = img +
        '<div class="card-name">' + escapeHtml(c.name) + '<br>' + (c.reversed ? '🔻' : '✅') + '</div>' +
        '<div class="card-pos">' + escapeHtml(positions[i] || ('Позиция ' + (i + 1))) + '</div>';
      box.appendChild(el);
    });
  }

  // ---------- Толкование ВНУТРИ приложения ----------
  function getInterpretation() {
    if (!AppState.drawn.length) { alertMsg('Сначала вытяните карты!'); return; }
    showProgress();
    haptic('light');
    fetch('/api/tarot/interpret', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deck_id: AppState.deck,
        spread_type: AppState.spread,
        three_card_type: AppState.threeCardType,
        question: AppState.question,
        cards: AppState.drawn,
        positions: positionsFor(),
        use_reversed: AppState.useReversed
      })
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('http ' + r.status)); })
      .then(function (res) {
        if (!res || !res.interpretation) throw new Error('empty');
        AppState.interpretation = res.interpretation;
        renderInterpretation(res.interpretation);
        showScreen('interpretation-screen');
        haptic('medium');
      })
      .catch(function () {
        alertMsg('Не удалось получить толкование. Попробуйте ещё раз через 1–2 минуты.');
      })
      .then(function () { hideProgress(); });
  }

  function renderInterpretation(text) {
    var box = $('interpretation-content');
    if (!box) return;
    box.innerHTML = String(text).split('\n')
      .map(function (l) { return l.trim(); })
      .filter(function (l) { return l.length > 0; })
      .map(function (l) { return '<p>' + escapeHtml(l) + '</p>'; })
      .join('');
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
    var p1 = $('planet1'), s1 = $('sign1'), a = $('aspect-type'), p2 = $('planet2'), s2 = $('sign2');
    if (!p1 || !s1 || !a || !p2 || !s2) return;
    if (!p1.value || !s1.value || !a.value || !p2.value || !s2.value) { alertMsg('Заполните все поля.'); return; }
    var aspectNames = {
      conjunction: 'Соединение', sextile: 'Секстиль', square: 'Квадрат',
      trine: 'Трин', opposition: 'Оппозиция', quincunx: 'Квиконс'
    };
    var payload = {
      action: 'astrology_aspect',
      query: aspectNames[a.value] + ': ' + p1.value + ' в ' + s1.value + ' и ' + p2.value + ' в ' + s2.value,
      timestamp: Date.now()
    };
    if (tg && tg.sendData) { try { tg.sendData(JSON.stringify(payload)); } catch (e2) {} }
    popupMsg('🪐 Отправлено!', 'Запрос передан в чат бота.');
    setTimeout(closeApp, 800);
  }

  // ---------- Инициализация ----------
  function init() {
    tgInit();
    try {
      AppState.useReversed = (localStorage.getItem('astro12_use_reversed') !== '0');
    } catch (e) {}

    // Расклады и типы
    var spreadBtns = document.querySelectorAll('[data-spread]');
    for (var i = 0; i < spreadBtns.length; i++) {
      (function (btn) {
        btn.addEventListener('click', function () { selectSpread(btn.getAttribute('data-spread')); });
      })(spreadBtns[i]);
    }
    var threeBtns = document.querySelectorAll('[data-three-type]');
    for (var j = 0; j < threeBtns.length; j++) {
      (function (btn) {
        btn.addEventListener('click', function () { selectThreeCardType(btn.getAttribute('data-three-type')); });
      })(threeBtns[j]);
    }
    var revBtns = document.querySelectorAll('[data-reversed]');
    for (var k = 0; k < revBtns.length; k++) {
      (function (btn) {
        btn.addEventListener('click', function () { setReversed(btn.getAttribute('data-reversed') === 'yes'); });
      })(revBtns[k]);
    }

    // Навигация «Назад»
    on('back-to-spread-from-three', 'click', function () { showScreen('spread-selection'); });
    on('back-to-spread', 'click', function () {
      showScreen(AppState.spread === 'three' ? 'three-card-type-selection' : 'spread-selection');
    });
    on('back-to-deck-from-reversed', 'click', function () { showScreen('deck-selection'); });
    on('back-to-reversed-from-question', 'click', function () { showScreen('reversed-setting'); });
    on('back-to-question-from-shuffle', 'click', function () { showScreen('question-input'); });
    on('back-to-shuffle-from-result', 'click', function () { showScreen('shuffle-screen'); });
    on('back-to-result-from-interp', 'click', function () { showScreen('result-screen'); });

    // Кнопки «🏠 Основное меню» (есть на каждом экране)
    var mm = ['main-menu-from-spread', 'main-menu-from-three', 'main-menu-from-deck',
              'main-menu-from-reversed', 'main-menu-from-question', 'main-menu-from-shuffle',
              'main-menu-from-result', 'main-menu-from-interp', 'main-menu-from-astro'];
    mm.forEach(function (id) { on(id, 'click', goMainMenu); });

    // Шаги потока
    on('continue-to-shuffle', 'click', function () {
      var q = $('question-text');
      var text = q ? q.value.trim() : '';
      if (text.length < 5) { alertMsg('Пожалуйста, опишите вопрос подробнее (минимум 5 символов).'); return; }
      AppState.question = text;
      resetShuffle();
      showScreen('shuffle-screen');
    });
    on('shuffle-btn', 'click', shuffle);
    on('draw-cards-btn', 'click', draw);
    on('get-interpretation', 'click', getInterpretation);
    on('retry-spread', 'click', function () {
      AppState.drawn = [];
      resetShuffle();
      showScreen('shuffle-screen');
    });
    on('new-spread-from-interp', 'click', function () {
      AppState.drawn = [];
      AppState.interpretation = null;
      AppState.question = '';
      showScreen('spread-selection');
    });
    on('btn-astro', 'click', function () { showScreen('astrology-input'); });
    on('astro-form', 'submit', sendAstro);

    if (tg && tg.BackButton) { try { tg.BackButton.onClick(goBack); } catch (e) {} }

    loadDecks();
    showScreen('spread-selection');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.Astro12AI = { AppState: AppState, SPREAD_CONFIGS: SPREAD_CONFIGS, showScreen: showScreen };
})();