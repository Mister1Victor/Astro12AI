/**
 * Astro12AI Mini App — логика. Самодостаточный: все константы локальные.
 * Поток экранов: spread -> deck -> shuffle -> result (+ astro).
 * ВСЕ вызовы Telegram WebApp обёрнуты в безопасные функции
 * (showLoading/hideProgress у WebApp НЕ существуют — используем MainButton).
 */
(function () {
  'use strict';

  var tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;
  if (tg) {
    try { tg.ready(); tg.expand(); } catch (e) {}
    if (tg.MainButton) { try { tg.MainButton.hide(); } catch (e) {} }
  }

  // ---------- БЕЗОПАСНЫЕ обёртки Telegram API ----------
  function showLoading() {
    if (tg && tg.MainButton && typeof tg.MainButton.showProgress === 'function') {
      try { tg.MainButton.showProgress(); } catch (e) {}
    }
  }
  function hideLoading() {
    if (tg && tg.MainButton && typeof tg.MainButton.hideProgress === 'function') {
      try { tg.MainButton.hideProgress(); } catch (e) {}
    }
  }
  function alertMsg(text) {
    if (tg && typeof tg.showAlert === 'function') {
      try { tg.showAlert(text); } catch (e) {}
    }
  }
  function haptic(t) {
    if (tg && tg.HapticFeedback) {
      try { tg.HapticFeedback.impactOccurred(t || 'light'); } catch (e) {}
    }
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

  var State = { screen: 'spread', spread: null, deck: null, drawn: [], decks: [] };

  function $(id) { return document.getElementById(id); }

  // ---------- Экраны и навигация ----------
  var SCREENS = ['spread', 'deck', 'shuffle', 'result', 'astro'];
  var BACK = { deck: 'spread', shuffle: 'deck', result: 'shuffle', astro: 'spread' };

  function showScreen(name) {
    State.screen = name;
    SCREENS.forEach(function (s) {
      var el = $('screen-' + s);
      if (el) el.classList.toggle('hidden', s !== name);
    });
    if (tg && tg.BackButton) {
      try {
        if (name === 'spread') tg.BackButton.hide();
        else tg.BackButton.show();
      } catch (e) {}
    }
    if (tg && tg.MainButton) { try { tg.MainButton.hide(); } catch (e) {} }
  }

  function goBack() {
    var target = BACK[State.screen];
    if (target) showScreen(target);
  }

  // ---------- 🏠 Основное меню: отправить действие боту и закрыть Mini App ----------
  function goMainMenu() {
    if (tg && typeof tg.sendData === 'function') {
      try {
        tg.sendData(JSON.stringify({ action: 'main_menu', timestamp: Date.now() }));
      } catch (e) {}
    }
    if (tg && typeof tg.close === 'function') {
      try { tg.close(); } catch (e) {}
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
        showScreen('shuffle');
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

  // ---------- Перемешать / вытянуть ----------
  function resetShuffle() {
    State.drawn = [];
    var cfg = SPREADS[State.spread] || SPREADS.one;
    $('shuffle-title').textContent = cfg.name + ' — ' + (State.deck ? State.deck.name : '');
    $('btn-shuffle').classList.remove('hidden');
    $('btn-draw').classList.add('hidden');
    $('btn-draw').disabled = false;
  }

  function shuffle() {
    $('btn-shuffle').disabled = true;
    haptic('light');
    var v = $('deck-visual');
    if (v) v.classList.add('shuffling');
    setTimeout(function () {
      if (v) v.classList.remove('shuffling');
      $('btn-shuffle').classList.add('hidden');
      $('btn-draw').classList.remove('hidden');
      $('btn-shuffle').disabled = false;
      haptic('medium');
    }, 1200);
  }

  function draw() {
    var cfg = SPREADS[State.spread] || SPREADS.one;
    if (!State.deck) return;
    $('btn-draw').disabled = true;
    showLoading();
    fetch('/api/tarot/draw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deck_id: State.deck.deck_id, count: cfg.count, spread_type: State.spread })
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
        alertMsg('Сервер недоступен. Повторите попытку через минуту.');
      })
      .then(function () {
        hideLoading();
        $('btn-draw').disabled = false;
      });
  }

  function renderResult() {
    var cfg = SPREADS[State.spread] || SPREADS.one;
    var box = $('cards-result');
    box.innerHTML = '';
    State.drawn.forEach(function (c, i) {
      var el = document.createElement('div');
      el.className = 'card-result' + (c.reversed ? ' reversed' : '');
      var img = c.image_url ? '<img src="' + c.image_url + '" alt="">' : '<div class="card-placeholder">🎴</div>';
      el.innerHTML = img +
        '<div class="card-name">' + (c.name || '') + '</div>' +
        '<div class="card-pos">' + (cfg.positions[i] || ('Позиция ' + (i + 1))) + '</div>' +
        '<div class="card-orient">' + (c.reversed ? '🔻 перевёрнуто' : '✅ прямо') + '</div>';
      box.appendChild(el);
    });
  }

  // ---------- Отправка расклада в бот ----------
  function sendToBot() {
    if (!State.drawn.length) { alertMsg('Сначала вытяните карты.'); return; }
    var payload = {
      action: 'tarot_spread',
      spread_type: State.spread,
      deck_id: State.deck ? State.deck.deck_id : null,
      cards: State.drawn.map(function (c) { return { card_id: c.card_id, name: c.name, reversed: !!c.reversed }; }),
      timestamp: Date.now()
    };
    if (tg && typeof tg.sendData === 'function') {
      try { tg.sendData(JSON.stringify(payload)); } catch (e) {}
      if (typeof tg.showPopup === 'function') {
        try {
          tg.showPopup({ title: '✅ Отправлено', message: 'Расклад передан в чат бота.', buttons: [{ type: 'ok' }] });
        } catch (e) {}
      }
      setTimeout(function () { try { tg.close(); } catch (e) {} }, 1200);
    } else {
      alertMsg('Вне Telegram отправка недоступна.');
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
    if (!p1 || !s1 || !a || !p2 || !s2) { alertMsg('Заполните все поля.'); return; }
    var aName = (ASPECTS.filter(function (x) { return x.id === a; })[0] || {}).name || a;
    var payload = { action: 'astrology_aspect', query: aName + ': ' + p1 + ' в ' + s1 + ' и ' + p2 + ' в ' + s2, timestamp: Date.now() };
    if (tg && typeof tg.sendData === 'function') {
      try { tg.sendData(JSON.stringify(payload)); } catch (e) {}
      if (typeof tg.showPopup === 'function') {
        try {
          tg.showPopup({ title: '✅ Отправлено', message: 'Запрос передан в чат бота.', buttons: [{ type: 'ok' }] });
        } catch (e) {}
      }
      setTimeout(function () { try { tg.close(); } catch (e) {} }, 1200);
    } else {
      alertMsg('Вне Telegram отправка недоступна.');
    }
  }

  // ---------- Инициализация ----------
  function init() {
    fillSelect('planet1', PLANETS); fillSelect('planet2', PLANETS);
    fillSelect('sign1', SIGNS);     fillSelect('sign2', SIGNS);
    fillSelect('aspect', ASPECTS);

    Array.prototype.forEach.call(document.querySelectorAll('[data-spread]'), function (btn) {
      btn.addEventListener('click', function () {
        State.spread = btn.getAttribute('data-spread');
        loadDecks();
        showScreen('deck');
        haptic('light');
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-back]'), function (btn) {
      btn.addEventListener('click', function () { showScreen(btn.getAttribute('data-back')); haptic('light'); });
    });
    // 🏠 Кнопки «Основное меню»
    Array.prototype.forEach.call(document.querySelectorAll('[data-main-menu]'), function (btn) {
      btn.addEventListener('click', goMainMenu);
    });
    var ba = $('btn-astro');
    if (ba) ba.addEventListener('click', function () { showScreen('astro'); haptic('light'); });
    $('btn-shuffle').addEventListener('click', shuffle);
    $('btn-draw').addEventListener('click', draw);
    $('btn-send').addEventListener('click', sendToBot);
    var form = $('astrology-form');
    if (form) form.addEventListener('submit', sendAstro);
    if (tg && tg.BackButton) {
      try { tg.BackButton.onClick(goBack); } catch (e) {}
    }
    loadDecks();
    showScreen('spread');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();