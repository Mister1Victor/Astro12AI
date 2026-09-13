/**
 * Astro12AI Mini App — Таро «12 Планет»
 * Полностью согласован с static/index.html по id.
 * Реализовано по ТЗ: расклад → тип трёх карт → колода → перевёрнутые (запоминание)
 * → вопрос → вытягивание → толкование в приложении → отправка в бот.
 */
(function () {
  'use strict';

  // ---------- Telegram ----------
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) { tg.ready(); tg.expand(); }

  // ---------- Переводы (ТЗ: русский, английский, немецкий) ----------
  const I18N = {
    ru: {
      subtitle: 'Мудрость в каждой карте', choose_spread: 'Выберите тип расклада',
      choose_spread_desc: 'Какой вопрос вас интересует?',
      spread_one: 'Одна карта', spread_three: 'Три карты', spread_choice: 'Выбор пути',
      spread_celtic: 'Кельтский крест', spread_yesno: 'Да или Нет',
      astrology: 'Астрология', main_menu: '🏠 Основное меню', back: '🔙 Назад',
      three_type_title: 'Тип расклада «Три карты»',
      three_ppf: 'Прошлое — Настоящее — Будущее', three_tfa: 'Мысли — Чувства — Действия',
      three_pmr: 'Плюс — Минус — Итог',
      choose_deck: 'Выберите колоду', reverse_title: 'Настройка карт',
      reverse_desc: 'Использовать ли перевёрнутые карты?',
      reverse_yes: 'Да, использовать перевёрнутые', reverse_no: 'Нет, только прямые',
      question_title: 'Ваш вопрос', question_desc: 'Напишите вопрос для расклада',
      question_placeholder: 'Например: что ждёт меня в работе?',
      continue_btn: 'Продолжить →', shuffle_title: 'Перемешайте колоду',
      shuffle_btn: '🔀 Перемешать', draw_btn: '✨ Вытянуть карты',
      result_title: 'Ваши карты', interpret_btn: '🔮 Получить толкование',
      redraw_btn: '🔄 Повторить расклад', interpret_title: 'Толкование расклада',
      loading: 'Загрузка…', back_to_cards: '🔙 К картам', send_to_bot: '📨 Отправить в бот',
      astro_title: 'Параметры аспекта', select_planet: 'Выберите планету',
      select_sign: 'Выберите знак', select_aspect: 'Тип аспекта',
      alert_question: 'Пожалуйста, напишите вопрос.',
      alert_deck: 'Сначала выберите колоду.',
      alert_no_cards: 'Сначала вытяните карты.',
      err_draw: 'Не удалось вытянуть карты. Попробуйте ещё раз.',
      err_interpret: 'Не удалось получить толкование. Нажмите «Получить толкование» ещё раз.',
      interpret_loading: 'Звёзды шепчут ответ…',
      sent: 'Отправлено в бот!'
    },
    en: {
      subtitle: 'Wisdom in every card', choose_spread: 'Choose a spread type',
      choose_spread_desc: 'What is your question about?',
      spread_one: 'One card', spread_three: 'Three cards', spread_choice: 'Choice of path',
      spread_celtic: 'Celtic Cross', spread_yesno: 'Yes or No',
      astrology: 'Astrology', main_menu: '🏠 Main menu', back: '🔙 Back',
      three_type_title: '"Three cards" spread type',
      three_ppf: 'Past — Present — Future', three_tfa: 'Thoughts — Feelings — Actions',
      three_pmr: 'Plus — Minus — Result',
      choose_deck: 'Choose a deck', reverse_title: 'Card settings',
      reverse_desc: 'Use reversed cards?',
      reverse_yes: 'Yes, use reversed', reverse_no: 'No, upright only',
      question_title: 'Your question', question_desc: 'Write a question for the spread',
      question_placeholder: 'For example: what awaits me at work?',
      continue_btn: 'Continue →', shuffle_title: 'Shuffle the deck',
      shuffle_btn: '🔀 Shuffle', draw_btn: '✨ Draw cards',
      result_title: 'Your cards', interpret_btn: '🔮 Get interpretation',
      redraw_btn: '🔄 Redraw', interpret_title: 'Spread interpretation',
      loading: 'Loading…', back_to_cards: '🔙 Back to cards', send_to_bot: '📨 Send to bot',
      astro_title: 'Aspect parameters', select_planet: 'Select a planet',
      select_sign: 'Select a sign', select_aspect: 'Aspect type',
      alert_question: 'Please write a question.',
      alert_deck: 'Choose a deck first.',
      alert_no_cards: 'Draw cards first.',
      err_draw: 'Failed to draw cards. Try again.',
      err_interpret: 'Failed to get interpretation. Try again.',
      interpret_loading: 'The stars are whispering…',
      sent: 'Sent to bot!'
    },
    de: {
      subtitle: 'Weisheit in jeder Karte', choose_spread: 'Wählen Sie die Legung',
      choose_spread_desc: 'Worum geht Ihre Frage?',
      spread_one: 'Eine Karte', spread_three: 'Drei Karten', spread_choice: 'Wegwahl',
      spread_celtic: 'Keltisches Kreuz', spread_yesno: 'Ja oder Nein',
      astrology: 'Astrologie', main_menu: '🏠 Hauptmenü', back: '🔙 Zurück',
      three_type_title: 'Typ der Legung „Drei Karten"',
      three_ppf: 'Vergangenheit — Gegenwart — Zukunft', three_tfa: 'Gedanken — Gefühle — Handlungen',
      three_pmr: 'Plus — Minus — Ergebnis',
      choose_deck: 'Wählen Sie ein Deck', reverse_title: 'Karteneinstellungen',
      reverse_desc: 'Umgedrehte Karten verwenden?',
      reverse_yes: 'Ja, umgedrehte verwenden', reverse_no: 'Nein, nur aufrechte',
      question_title: 'Ihre Frage', question_desc: 'Schreiben Sie eine Frage für die Legung',
      question_placeholder: 'Zum Beispiel: Was erwartet mich bei der Arbeit?',
      continue_btn: 'Weiter →', shuffle_title: 'Mischen Sie das Deck',
      shuffle_btn: '🔀 Mischen', draw_btn: '✨ Karten ziehen',
      result_title: 'Ihre Karten', interpret_btn: '🔮 Deutung erhalten',
      redraw_btn: '🔄 Neu ziehen', interpret_title: 'Deutung der Legung',
      loading: 'Lädt…', back_to_cards: '🔙 Zu den Karten', send_to_bot: '📨 An Bot senden',
      astro_title: 'Aspekt-Parameter', select_planet: 'Planet wählen',
      select_sign: 'Zeichen wählen', select_aspect: 'Aspekt-Typ',
      alert_question: 'Bitte schreiben Sie eine Frage.',
      alert_deck: 'Wählen Sie zuerst ein Deck.',
      alert_no_cards: 'Ziehen Sie zuerst Karten.',
      err_draw: 'Karten konnten nicht gezogen werden. Versuchen Sie es erneut.',
      err_interpret: 'Deutung fehlgeschlagen. Versuchen Sie es erneut.',
      interpret_loading: 'Die Sterne flüstern…',
      sent: 'An Bot gesendet!'
    }
  };

  // Автоопределение языка устройства (ТЗ), по умолчанию русский
  let lang = 'ru';
  try {
    const deviceLang = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code)
      ? tg.initDataUnsafe.user.language_code.slice(0, 2).toLowerCase()
      : navigator.language.slice(0, 2).toLowerCase();
    if (['en', 'de'].includes(deviceLang)) lang = deviceLang;
  } catch (e) { lang = 'ru'; }

  const t = (key) => (I18N[lang] && I18N[lang][key]) || I18N.ru[key] || key;

  function applyLang() {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    document.querySelectorAll('.lang-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.lang === lang));
    fillAstroSelects();
  }

  // ---------- Состояние ----------
  const state = {
    step: 'spread', spreadType: null, threeType: null,
    deckId: null, deckName: null, useReversed: true,
    question: '', cards: [], interpretation: null
  };

  // Запоминание настройки перевёрнутых (ТЗ: «запомнить»)
  try {
    const savedRev = localStorage.getItem('astro12_use_reversed');
    if (savedRev !== null) state.useReversed = savedRev === '1';
  } catch (e) {}

  const navHistory = [];
  let decks = [];

  // ---------- Конфигурация раскладов ----------
  const SPREADS = {
    one:    { name: t('spread_one'), count: 1, positions: [t('spread_one')] },
    three:  { name: t('spread_three'), count: 3, positions: [t('three_ppf')] },
    choice: { name: t('spread_choice'), count: 7, positions: [] },
    celtic: { name: t('spread_celtic'), count: 10, positions: [] },
    yesno:  { name: t('spread_yesno'), count: 1, positions: [t('spread_yesno')] }
  };

  const THREE_TYPES = {
    'past-present-future':       ['Прошлое', 'Настоящее', 'Будущее'],
    'thoughts-feelings-actions': ['Мысли', 'Чувства', 'Действия'],
    'plus-minus-result':         ['Плюс', 'Минус', 'Итог']
  };

  const CHOICE_POSITIONS = ['В1—Достоинство', 'В1—Недостаток', 'В1—Исход',
    'В2—Достоинство', 'В2—Недостаток', 'В2—Исход', 'Совет'];
  const CELTIC_POSITIONS = ['Суть', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
    'Будущее', 'Я', 'Окружение', 'Надежды/страхи', 'Итог'];

  const FALLBACK_DECKS = [
    { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 },
    { deck_id: 'author_deck',     name: 'Авторская колода Школы', cards_count: 78 },
    { deck_id: 'rider_waite',     name: 'Таро Райдера-Уэйта', cards_count: 78 },
    { deck_id: 'thoth',           name: 'Таро Тота', cards_count: 78 }
  ];

  const PLANETS = ['Солнце','Луна','Меркурий','Венера','Марс','Юпитер',
    'Сатурн','Уран','Нептун','Плутон','Эрида','Церера'];
  const SIGNS = ['Овен','Телец','Близнецы','Рак','Лев','Дева','Весы',
    'Скорпион','Стрелец','Козерог','Водолей','Рыбы'];
  const ASPECTS = [
    { id: 'conjunction', name: 'Соединение (0°)' },
    { id: 'sextile',     name: 'Секстиль (60°)' },
    { id: 'square',      name: 'Квадрат (90°)' },
    { id: 'trine',       name: 'Трин (120°)' },
    { id: 'opposition',  name: 'Оппозиция (180°)' },
    { id: 'quincunx',    name: 'Квиконс (150°)' }
  ];

  // ---------- Утилиты ----------
  const $ = (id) => document.getElementById(id);

  function haptic(type) {
    try {
      if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.impactOccurred === 'function')
        tg.HapticFeedback.impactOccurred(type || 'light');
    } catch (e) {}
  }

  function showAlert(message) {
    try { if (tg && typeof tg.showAlert === 'function') { tg.showAlert(message); return; } } catch (e) {}
    try { alert(message); } catch (e) {}
  }

  function showLoading(text) {
    const o = $('loading-overlay'), tx = $('loading-text');
    if (tx) tx.textContent = text || t('loading');
    if (o) o.classList.remove('hidden');
  }
  function hideLoading() {
    const o = $('loading-overlay');
    if (o) o.classList.add('hidden');
  }

  function getPositions() {
    if (state.spreadType === 'three')
      return THREE_TYPES[state.threeType] || THREE_TYPES['past-present-future'];
    if (state.spreadType === 'choice') return CHOICE_POSITIONS;
    if (state.spreadType === 'celtic') return CELTIC_POSITIONS;
    const s = SPREADS[state.spreadType] || SPREADS.one;
    return s.positions || [];
  }

  // ---------- Навигация ----------
  const SCREENS = ['spread', 'three-type', 'deck', 'reverse', 'question',
    'shuffle', 'result', 'interpretation', 'astro'];

  function showScreen(id) {
    state.step = id;
    SCREENS.forEach(s => {
      const el = $('screen-' + s);
      if (el) el.classList.remove('active');
    });
    const target = $('screen-' + id);
    if (target) target.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function navigateTo(id) { navHistory.push(state.step); showScreen(id); }

  function goBack() {
    haptic('light');
    if (navHistory.length) showScreen(navHistory.pop());
    else goMainMenu();
  }

  function goMainMenu() {
    haptic('light');
    try {
      if (tg && typeof tg.sendData === 'function')
        tg.sendData(JSON.stringify({ action: 'main_menu', timestamp: Date.now() }));
      if (tg && typeof tg.close === 'function') tg.close();
    } catch (e) { showScreen('spread'); }
  }

  function resetApp() {
    state.spreadType = null; state.threeType = null;
    state.deckId = null; state.deckName = null;
    state.question = ''; state.cards = []; state.interpretation = null;
    navHistory.length = 0;
    const q = $('question-input'); if (q) q.value = '';
    const rc = $('result-cards'); if (rc) rc.innerHTML = '';
    const it = $('interpretation-text');
    if (it) { it.textContent = t('loading'); it.classList.add('loading-text'); }
    const sb = $('shuffle-btn'), db = $('draw-btn');
    if (sb) sb.classList.remove('hidden');
    if (db) db.classList.add('hidden');
    showScreen('spread');
  }

  // ---------- Колоды ----------
  function renderDecks(list) {
    const box = $('deck-list');
    if (!box) return;
    box.innerHTML = '';
    list.filter(d => d.cards_count > 0).forEach(d => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'option-card deck-option';
      b.innerHTML = '<span class="icon">🎴</span><span class="label deck-name-highlight">' +
        d.name + '</span><span class="subtext">' + d.cards_count + '</span>';
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

  // ---------- Перемешивание и вытягивание ----------
  function shuffle() {
    haptic('heavy');
    const stack = $('card-stack');
    if (stack) {
      stack.classList.add('shuffling');
      setTimeout(() => stack.classList.remove('shuffling'), 800);
    }
    const sb = $('shuffle-btn'), db = $('draw-btn');
    if (sb) sb.classList.add('hidden');
    if (db) db.classList.remove('hidden');
  }

  async function drawCards() {
    const cfg = SPREADS[state.spreadType] || SPREADS.one;
    if (!state.deckId) { showAlert(t('alert_deck')); return; }
    showLoading(t('loading'));
    try {
      const r = await fetch('/api/tarot/draw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deck_id: state.deckId, count: cfg.count,
          spread_type: state.spreadType, use_reversed: state.useReversed
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
      showAlert(t('err_draw'));
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
      el.style.animationDelay = (i * 0.1) + 's';
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
      pos.className = 'card-name';
      pos.style.fontSize = '10px';
      pos.style.color = 'var(--text-secondary)';
      pos.textContent = positions[i] || '';
      el.appendChild(pos);
      box.appendChild(el);
    });
  }

  // ---------- Толкование в приложении ----------
  async function getInterpretation() {
    if (!state.cards.length) { showAlert(t('alert_no_cards')); return; }
    navigateTo('interpretation');
    const box = $('interpretation-box'), text = $('interpretation-text');
    if (text) { text.textContent = t('interpret_loading'); text.classList.add('loading-text'); }
    showLoading(t('interpret_loading'));
    try {
      const r = await fetch('/api/tarot/interpret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deck_id: state.deckId, spread_type: state.spreadType,
          three_card_type: state.threeType, question: state.question,
          cards: state.cards.map(c => ({
            card_id: c.card_id, name: c.name, reversed: !!c.reversed,
            astrology: c.astrology || '', keywords: c.keywords || []
          })),
          positions: getPositions(), use_reversed: state.useReversed
        })
      });
      if (!r.ok) throw new Error('http ' + r.status);
      const data = await r.json();
      const txt = data.interpretation || data.text || data.result || '';
      if (!txt) throw new Error('empty');
      state.interpretation = txt;
      if (text) { text.textContent = txt; text.classList.remove('loading-text'); }
    } catch (e) {
      console.error('interpret error', e);
      if (text) { text.textContent = t('err_interpret'); text.classList.remove('loading-text'); }
    } finally { hideLoading(); }
  }

  // ---------- Отправка в бот ----------
  function sendToBot() {
    if (!state.cards.length) { showAlert(t('alert_no_cards')); return; }
    try {
      if (tg && typeof tg.sendData === 'function') {
        tg.sendData(JSON.stringify({
          action: 'tarot_spread', spread_type: state.spreadType,
          deck_id: state.deckId, question: state.question,
          interpretation: state.interpretation,
          cards: state.cards.map(c => ({ card_id: c.card_id, name: c.name, reversed: !!c.reversed })),
          timestamp: Date.now()
        }));
        showAlert(t('sent'));
        setTimeout(() => { try { tg.close(); } catch (e) {} }, 900);
      } else showAlert(t('sent'));
    } catch (e) { showAlert(t('sent')); }
  }

  // ---------- Астрология ----------
  function fillAstroSelects() {
    const fill = (id, items, isObj) => {
      const sel = $(id); if (!sel) return;
      const placeholder = isObj ? t('select_aspect') :
        (id.startsWith('planet') ? t('select_planet') : t('select_sign'));
      sel.innerHTML = '<option value="">' + placeholder + '</option>';
      items.forEach(it => {
        const o = document.createElement('option');
        o.value = isObj ? it.id : it;
        o.textContent = isObj ? it.name : it;
        sel.appendChild(o);
      });
    };
    fill('planet1', PLANETS, false); fill('planet2', PLANETS, false);
    fill('sign1', SIGNS, false);     fill('sign2', SIGNS, false);
    fill('aspect-type', ASPECTS, true);
  }

  function submitAstro(e) {
    e.preventDefault();
    const p1 = $('planet1').value, s1 = $('sign1').value, a = $('aspect-type').value,
          p2 = $('planet2').value, s2 = $('sign2').value;
    if (!p1 || !s1 || !a || !p2 || !s2) { showAlert(t('loading') ? t('select_aspect') : 'Fill all fields'); return; }
    const aName = (ASPECTS.find(x => x.id === a) || {}).name || a;
    try {
      if (tg && typeof tg.sendData === 'function') {
        tg.sendData(JSON.stringify({
          action: 'astrology_aspect',
          query: aName + ': ' + p1 + ' в ' + s1 + ' и ' + p2 + ' в ' + s2,
          timestamp: Date.now()
        }));
        showAlert(t('sent'));
        setTimeout(() => { try { tg.close(); } catch (e) {} }, 900);
      } else showAlert(t('sent'));
    } catch (e) { showAlert(t('sent')); }
  }

  // ---------- Инициализация ----------
  function init() {
    applyLang();

    document.querySelectorAll('.lang-btn').forEach(b =>
      b.addEventListener('click', () => { lang = b.dataset.lang; applyLang(); }));

    document.querySelectorAll('.spread-option').forEach(btn =>
      btn.addEventListener('click', () => {
        state.spreadType = btn.dataset.spread;
        haptic('success');
        if (state.spreadType === 'three') navigateTo('three-type');
        else navigateTo('deck');
      }));

    document.querySelectorAll('.three-type-option').forEach(btn =>
      btn.addEventListener('click', () => {
        state.threeType = btn.dataset.threeType;
        haptic('success'); navigateTo('deck');
      }));

    const ry = $('reverse-yes'), rn = $('reverse-no');
    if (ry) ry.addEventListener('click', () => {
      state.useReversed = true;
      try { localStorage.setItem('astro12_use_reversed', '1'); } catch (e) {}
      haptic('success'); navigateTo('question');
    });
    if (rn) rn.addEventListener('click', () => {
      state.useReversed = false;
      try { localStorage.setItem('astro12_use_reversed', '0'); } catch (e) {}
      haptic('success'); navigateTo('question');
    });

    const qSubmit = $('question-submit-btn');
    if (qSubmit) qSubmit.addEventListener('click', () => {
      const q = ($('question-input').value || '').trim();
      if (q.length < 3) { showAlert(t('alert_question')); return; }
      state.question = q;
      haptic('success'); navigateTo('shuffle');
    });

    const shuffleBtn = $('shuffle-btn');
    if (shuffleBtn) shuffleBtn.addEventListener('click', shuffle);
    const drawBtn = $('draw-btn');
    if (drawBtn) drawBtn.addEventListener('click', drawCards);

    const interpretBtn = $('interpret-btn');
    if (interpretBtn) interpretBtn.addEventListener('click', getInterpretation);
    const redrawBtn = $('redraw-btn');
    if (redrawBtn) redrawBtn.addEventListener('click', () => {
      haptic('warning'); state.cards = [];
      const rc = $('result-cards'); if (rc) rc.innerHTML = '';
      navigateTo('shuffle');
    });
    const backToCards = $('back-to-cards-btn');
    if (backToCards) backToCards.addEventListener('click', () => showScreen('result'));
    const sendBotBtn = $('send-to-bot-btn');
    if (sendBotBtn) sendBotBtn.addEventListener('click', sendToBot);

    const astroOpen = $('astro-open-btn');
    if (astroOpen) astroOpen.addEventListener('click', () => navigateTo('astro'));
    const astroForm = $('astro-form');
    if (astroForm) astroForm.addEventListener('submit', submitAstro);

    document.querySelectorAll('.btn-back').forEach(b =>
      b.addEventListener('click', e => { e.preventDefault(); goBack(); }));
    document.querySelectorAll('.btn-home').forEach(b =>
      b.addEventListener('click', e => { e.preventDefault(); goMainMenu(); }));

    loadDecks();
    showScreen('spread');
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', init);
  else init();
})();