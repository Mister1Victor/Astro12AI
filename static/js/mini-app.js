/**
 * Astro12AI Mini App — v4.0
 * Реальные картинки карт через /api/tarot/image/{deck}/{file}
 * Реальное толкование LLM через /api/tarot/interpret (демо-генерации НЕТ).
 */
(function () {
  'use strict';

  var tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;
  if (tg) { try { tg.ready(); tg.expand(); } catch (e) {} }

  // ---------- Конфигурация раскладов ----------
  var SPREADS = {
    one:   { count: 1, positions: ['Карта дня'] },
    three: { count: 3, positionsByType: {
        'past-present-future':       ['Прошлое', 'Настоящее', 'Будущее'],
        'thoughts-feelings-actions': ['Мысли', 'Чувства', 'Действия'],
        'plus-minus-result':         ['Плюс', 'Минус', 'Итог']
    } },
    choice: { count: 7, positions: ['Вариант 1 — Достоинство', 'Вариант 1 — Недостаток', 'Вариант 1 — Исход',
                                   'Вариант 2 — Достоинство', 'Вариант 2 — Недостаток', 'Вариант 2 — Исход', 'Совет'] },
    celtic: { count: 10, positions: ['Суть (сигнификатор)', 'Препятствие', 'Цель', 'Корни', 'Прошлое',
                                    'Ближайшее будущее', 'Я', 'Окружение', 'Надежды/страхи', 'Итог'] }
  };
  var FALLBACK_DECKS = [
    { deck_id: 'author_deck_146', name: 'Оракул «12 Планет»', cards_count: 146 },
    { deck_id: 'author_deck',     name: 'Авторская колода Школы «12 Планет»', cards_count: 78 },
    { deck_id: 'rider_waite',     name: 'Таро Райдера-Уэйта', cards_count: 78 },
    { deck_id: 'thoth',           name: 'Таро Тота (Алистер Кроули)', cards_count: 78 }
  ];
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

  var state = { spreadType: null, threeType: null, deckId: null,
                useReversed: true, question: '', cards: [], interpretation: '' };
  var screens = {};
  var current = 'spread-type';
  var FLOW = ['spread-type', 'three-type', 'deck', 'reverse', 'question', 'shuffle', 'result', 'interpretation'];

  // ---------- Утилиты ----------
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function haptic(t) {
    try { if (tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred) tg.HapticFeedback.impactOccurred(t || 'light'); } catch (e) {}
  }
  function showAlert(msg) {
    try {
      if (tg && tg.isVersionAtLeast && tg.isVersionAtLeast('6.2') && tg.showAlert) { tg.showAlert(msg); return; }
    } catch (e) {}
    try { alert(msg); } catch (e) {}
  }
  function positionsFor() {
    var cfg = SPREADS[state.spreadType] || SPREADS.one;
    if (state.spreadType === 'three') {
      return (cfg.positionsByType && cfg.positionsByType[state.threeType]) ||
             cfg.positionsByType['past-present-future'];
    }
    return cfg.positions;
  }

  // ---------- Навигация ----------
  function showScreen(id) {
    current = id;
    haptic('light');
    Object.keys(screens).forEach(function (k) {
      if (screens[k]) screens[k].classList.remove('active');
    });
    var target = screens[id];
    if (target) target.classList.add('active');
    window.scrollTo(0, 0);
  }
  function goBack() {
    var idx = FLOW.indexOf(current);
    if (idx > 0) {
      var prev = FLOW[idx - 1];
      if (state.spreadType !== 'three' && prev === 'three-type') prev = FLOW[idx - 2] || 'spread-type';
      showScreen(prev);
    } else if (current === 'astro') {
      showScreen('spread-type');
    } else if (tg && tg.close) {
      tg.close();
    }
  }
  function goHome() {
  // УДАЛЕНО: tg.close() больше не вызывается, приложение не закроется!
  state.spreadType = null; 
  state.threeType = null; 
  state.deckId = null;
  state.question = ''; 
  state.cards = []; 
  state.interpretation = '';
  
  // Сбрасываем видимость кнопок перемешивания, если они были изменены
  var shuffleBtn = $('shuffle-btn'); if (shuffleBtn) shuffleBtn.classList.remove('hidden');
  var drawBtn = $('draw-btn');       if (drawBtn) drawBtn.classList.add('hidden');
  
  // Возвращаем пользователя на самый первый экран выбора расклада
  showScreen('spread-type');
}

  // ---------- Колоды ----------
  function renderDecks(decks) {
    var box = $('deck-list');
    if (!box) return;
    box.innerHTML = '';
    decks.forEach(function (d) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'option-row deck-option';
      b.innerHTML = '<span class="icon">🎴</span><span class="text">' + esc(d.name) +
                    '</span><span class="subtext">' + esc(d.cards_count) + ' карт</span>';
      b.addEventListener('click', function () {
        state.deckId = d.deck_id;
        haptic('success');
        showScreen('reverse');
      });
      box.appendChild(b);
    });
  }
  function loadDecks() {
    fetch('/api/tarot/decks')
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('http ' + r.status)); })
      .then(function (list) { renderDecks((list && list.length) ? list : FALLBACK_DECKS); })
      .catch(function () { renderDecks(FALLBACK_DECKS); });
  }

  // ---------- Перемешивание / вытягивание ----------
  function onShuffle() {
    haptic('medium');
    var stack = document.querySelector('.card-stack');
    var shuffleBtn = $('shuffle-btn'), drawBtn = $('draw-btn');
    if (shuffleBtn) shuffleBtn.disabled = true;
    if (stack) stack.classList.add('shuffling');
    setTimeout(function () {
      if (stack) stack.classList.remove('shuffling');
      if (shuffleBtn) shuffleBtn.classList.add('hidden');
      if (drawBtn) drawBtn.classList.remove('hidden');
      if (shuffleBtn) shuffleBtn.disabled = false;
      haptic('success');
    }, 900);
  }

  function performDraw() {
    var cfg = SPREADS[state.spreadType];
    if (!cfg || !state.deckId) { showAlert('Выберите расклад и колоду.'); return; }
    showScreen('result');
    var container = $('result-cards-container');
    if (container) container.innerHTML = '<div class="loading-text">Вытягиваем карты…</div>';
    fetch('/api/tarot/draw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deck_id: state.deckId,
        count: cfg.count,
        spread_type: state.spreadType,
        use_reversed: state.useReversed
      })
    })
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (data) {
      if (!data || !data.cards || !data.cards.length) throw new Error('empty');
      state.cards = data.cards;
      renderResults();
    })
    .catch(function (e) {
      console.error('Draw error:', e);
      if (container) container.innerHTML = '';
      showAlert('Не удалось вытянуть карты. Попробуйте ещё раз.');
      showScreen('shuffle');
    });
  }

  /**
 * Отрисовка вытянутых карт Таро с поддержкой полноэкранного режима и тактильного отклика.
 */
function renderResults() {
  var container = $('result-cards-container');
  if (!container) return;

  // Динамически задаем класс типа расклада (например, spread-celtic для компактных карт)
  container.className = 'cards-display spread-' + (state.spreadType || 'one');
  container.innerHTML = '';

  var positions = positionsFor();

  state.cards.forEach(function (card, i) {
    // 1. Создаем главный контейнер карты
    var cardItem = document.createElement('div');
    cardItem.className = 'tarot-card-item' + (card.reversed ? ' reversed' : '');
    cardItem.style.animationDelay = (0.15 * i) + 's';
    cardItem.style.cursor = 'zoom-in';

    // 2. Создаем и настраиваем изображение карты
    if (card.image_url) {
      var img = document.createElement('img');
      img.className = 'card-image';
      img.alt = card.name || 'Карта Таро';
      img.src = card.image_url;
      
      // Фолбэк, если изображение не загрузилось с сервера
      img.onerror = function () {
        var placeholder = document.createElement('div');
        placeholder.className = 'card-image card-image-empty';
        placeholder.textContent = '🎴';
        img.replaceWith(placeholder);
      };
      cardItem.appendChild(img);
    } else {
      var fallback = document.createElement('div');
      fallback.className = 'card-image card-image-empty';
      fallback.textContent = '🎴';
      cardItem.appendChild(fallback);
    }

    // 3. Добавляем название карты
    var nameLabel = document.createElement('div');
    nameLabel.className = 'card-name';
    nameLabel.textContent = (card.name || '') + (card.reversed ? ' 🔻' : '');
    cardItem.appendChild(nameLabel);

    // 4. Добавляем позицию карты в раскладе (Прошлое, Настоящее, Итог...)
    var posLabel = document.createElement('div');
    posLabel.className = 'card-pos';
    posLabel.textContent = positions[i] || ('Позиция ' + (i + 1));
    cardItem.appendChild(posLabel);

    // 5. Логика интерактивного увеличения карты во весь экран (UX/Haptic)
    cardItem.addEventListener('click', function (e) {
      e.stopPropagation(); // Предотвращаем ложные срабатывания оверлея

      if (cardItem.classList.contains('fullscreen')) {
        cardItem.classList.remove('fullscreen');
        haptic('light'); // Мягкая вибрация при закрытии
      } else {
        // Закрываем любую другую карту, если она была открыта ранее
        document.querySelectorAll('.tarot-card-item.fullscreen').forEach(function (el) {
          el.classList.remove('fullscreen');
        });
        
        cardItem.classList.add('fullscreen');
        haptic('medium'); // Сочная вибрация при раскрытии
      }
    });

    // Добавляем готовую карту в контейнер экрана результатов
    container.appendChild(cardItem);
  });
}


  // ---------- РЕАЛЬНОЕ толкование LLM ----------
  function fetchInterpretation() {
    var box = $('interpretation-text');
    if (!box) return;
    box.textContent = 'Звезды шепчут ответ…';
    box.className = 'interpretation-box loading-text';
    var payload = {
      deck_id: state.deckId,
      spread_type: state.spreadType,
      three_card_type: state.threeType,
      question: state.question,
      positions: positionsFor(),
      use_reversed: state.useReversed,
      cards: state.cards.map(function (c) {
        return { card_id: c.card_id, name: c.name, reversed: !!c.reversed,
                 astrology: c.astrology || '', keywords: c.keywords || [] };
      })
    };
    fetch('/api/tarot/interpret', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
    .then(function (res) {
      if (res.ok && res.j && res.j.interpretation) {
        state.interpretation = res.j.interpretation;
        box.className = 'interpretation-box';
        box.textContent = res.j.interpretation;   // white-space: pre-wrap сохранит абзацы
      } else {
        box.className = 'interpretation-box error-text';
        box.textContent = (res.j && res.j.error) ? res.j.error
          : 'Не удалось получить толкование. Попробуйте позже.';
      }
    })
    .catch(function () {
      box.className = 'interpretation-box error-text';
      box.textContent = 'Нет связи с сервером. Попробуйте позже.';
    });
  }

  function resetToShuffle() {
    state.cards = [];
    state.interpretation = '';
    var rc = $('result-cards-container'); if (rc) rc.innerHTML = '';
    var it = $('interpretation-text');
    if (it) { it.textContent = 'Звезды шепчут ответ…'; it.className = 'interpretation-box loading-text'; }
    var shuffleBtn = $('shuffle-btn'), drawBtn = $('draw-btn');
    if (shuffleBtn) shuffleBtn.classList.remove('hidden');
    if (drawBtn) drawBtn.classList.add('hidden');
    showScreen('shuffle');
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

  async function submitAstro(e) {
    e.preventDefault();
    const p1 = $('planet1').value, s1 = $('sign1').value, a = $('aspect-type').value,
          p2 = $('planet2').value, s2 = $('sign2').value;
    if (!p1 || !s1 || !a || !p2 || !s2) { 
        showAlert(t('select_aspect') ? 'Заполните все поля' : 'Fill all fields'); 
        return; 
    }
    
    const aName = (ASPECTS.find(x => x.id === a) || {}).name || a;
    const query = `${aName}: ${p1} в ${s1} и ${p2} в ${s2}`;
    
    // Показываем загрузку
    showLoading('Получаем толкование…');
    
    try {
        const r = await fetch('/api/astro/interpret', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        if (!r.ok) throw new Error('http ' + r.status);
        const data = await r.json();
        
        if (data.error) throw new Error(data.error);
        if (!data.interpretation) throw new Error('empty');
        
        // Отображаем ответ в приложении (переиспользуем экран интерпретации)
        state.interpretation = data.interpretation;
        hideLoading();
        
        const box = $('interpretation-box');
        const text = $('interpretation-text');
        if (box && text) {
            text.textContent = data.interpretation;
            text.classList.remove('loading-text');
            box.classList.remove('hidden');
            showScreen('interpretation');
            
            // Скрываем кнопку "К картам" (для астрологии она не нужна)
            const backToCardsBtn = $('back-to-cards-btn');
            if (backToCardsBtn) backToCardsBtn.style.display = 'none';
        }
        
    } catch (e) {
        hideLoading();
        console.error('Astro interpretation error:', e);
        showAlert('Не удалось получить толкование: ' + e.message);
    }
}

  // ---------- Инициализация ----------
  function init() {
    ['spread-type', 'three-type', 'deck', 'reverse', 'question', 'shuffle', 'result', 'interpretation', 'astro']
      .forEach(function (id) { screens[id] = $('screen-' + id); });

    document.querySelectorAll('.btn-back').forEach(function (b) {
      b.addEventListener('click', function (e) { e.preventDefault(); goBack(); });
    });
    document.querySelectorAll('.btn-home').forEach(function (b) {
      b.addEventListener('click', function (e) { e.preventDefault(); goHome(); });
    });
    document.querySelectorAll('.spread-option').forEach(function (b) {
      b.addEventListener('click', function () {
        state.spreadType = b.getAttribute('data-type');
        haptic('success');
        showScreen(state.spreadType === 'three' ? 'three-type' : 'deck');
      });
    });
    document.querySelectorAll('.three-type-option').forEach(function (b) {
      b.addEventListener('click', function () {
        state.threeType = b.getAttribute('data-type');
        haptic('success');
        showScreen('deck');
      });
    });
    var ry = $('reverse-yes'), rn = $('reverse-no');
    if (ry) ry.addEventListener('click', function () { state.useReversed = true;  haptic('success'); showScreen('question'); });
    if (rn) rn.addEventListener('click', function () { state.useReversed = false; haptic('success'); showScreen('question'); });

    var sq = $('submit-question-btn');
    if (sq) sq.addEventListener('click', function () {
      var v = ($('question-input').value || '').trim();
      if (!v) { haptic('error'); showAlert('Пожалуйста, введите вопрос перед продолжением.'); return; }
      state.question = v;
      haptic('success');
      showScreen('shuffle');
    });

    var sh = $('shuffle-btn'); if (sh) sh.addEventListener('click', onShuffle);
    var dr = $('draw-btn');    if (dr) dr.addEventListener('click', performDraw);
    var gi = $('get-interpretation-btn');
    if (gi) gi.addEventListener('click', function () { haptic('success'); showScreen('interpretation'); fetchInterpretation(); });
    var rs = $('retry-spread-btn');
    if (rs) rs.addEventListener('click', function () { haptic('light'); resetToShuffle(); });
    document.querySelectorAll('[data-action="back-to-cards"]').forEach(function (b) {
      b.addEventListener('click', function () { showScreen('result'); });
    });
    var nr = $('new-reading-btn');
    if (nr) nr.addEventListener('click', function () { resetToShuffle(); });
    var oa = $('open-astro');
    if (oa) oa.addEventListener('click', function () { showScreen('astro'); });
    var form = $('astrology-form');
    if (form) form.addEventListener('submit', sendAstro);

    fillSelect('planet1', PLANETS); fillSelect('planet2', PLANETS);
    fillSelect('sign1', SIGNS);     fillSelect('sign2', SIGNS);
    fillSelect('aspect-type', ASPECTS);

    loadDecks();
    showScreen('spread-type');
    console.log('Mini App v4.0 initialized');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();