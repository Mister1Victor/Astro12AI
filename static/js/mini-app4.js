/**
 * Astro12AI Mini App — v4.0
 * Реальные картинки карт через /api/tarot/image/{deck}/{file}
 * Реальное толкование LLM через /api/tarot/interpret (демо-генерации НЕТ).
 */
(function () {
  "use strict";

  var tg =
    window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
    } catch (e) { }
  }

  // ---------- Конфигурация раскладов ----------
  // БЫЛО:
  var SPREADS = {
    one: { count: 1, positions: ["Карта дня"] },
    three: {
      count: 3,
      positionsByType: {
        "past-present-future": ["Прошлое", "Настоящее", "Будущее"],
        "thoughts-feelings-actions": ["Мысли", "Чувства", "Действия"],
        "plus-minus-result": ["Плюс", "Минус", "Итог"],
      },
    },
    choice: {
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
    },
    celtic: {
      count: 10,
      positions: [
        "Суть (сигнификатор)",
        "Препятствие",
        "Цель",
        "Корни",
        "Прошлое",
        "Ближайшее будущее",
        "Я",
        "Окружение",
        "Надежды/страхи",
        "Итог",
      ],
    },
  };

  // СТАЛО:
  var SPREADS = {
    one: { count: 1, positions: ["Карта дня"] },
    three: {
      count: 3,
      positionsByType: {
        "past-present-future": ["Прошлое", "Настоящее", "Будущее"],
        "thoughts-feelings-actions": ["Мысли", "Чувства", "Действия"],
        "plus-minus-result": ["Плюс", "Минус", "Итог"],
      },
    },
    choice: { count: 7, positions: [] }, // count будет пересчитан динамически
    celtic: {
      count: 10,
      positions: [
        "Суть (сигнификатор)",
        "Препятствие",
        "Цель",
        "Корни",
        "Прошлое",
        "Ближайшее будущее",
        "Я",
        "Окружение",
        "Надежды/страхи",
        "Итог",
      ],
    },
  };
  var FALLBACK_DECKS = [
    { deck_id: "thoth", name: "Таро Тота ", cards_count: 78, },
    { deck_id: "rider_waite", name: "Таро Райдера-Уэйта ", cards_count: 78, },
    { deck_id: "author_deck", name: "Таро Райдера-Уэйта «12 Планет» ", cards_count: 78, },
    { deck_id: "author_deck_146", name: "Оракул «12 Планет» Авторская колода", cards_count: 146, },
  ];
  var PLANETS = [
    "Солнце",
    "Луна",
    "Меркурий",
    "Венера",
    "Марс",
    "Юпитер",
    "Сатурн",
    "Уран",
    "Нептун",
    "Плутон",
    "Эрида",
    "Церера",
  ];
  var SIGNS = [
    "Овен",
    "Телец",
    "Близнецы",
    "Рак",
    "Лев",
    "Дева",
    "Весы",
    "Скорпион",
    "Стрелец",
    "Козерог",
    "Водолей",
    "Рыбы",
  ];
  var ASPECTS = [
    { id: "conjunction", name: "Соединение (0°)" },
    { id: "sextile", name: "Секстиль (60°)" },
    { id: "square", name: "Квадрат (90°)" },
    { id: "trine", name: "Трин (120°)" },
    { id: "opposition", name: "Оппозиция (180°)" },
    { id: "quincunx", name: "Квиконс (150°)" },
  ];

  var state = {
    spreadType: null,
    threeType: null,
    deckId: null,
    useReversed: true,
    question: "",
    cards: [],
    interpretation: "",
    choiceEssence: "",
    choiceOptions: [],
    choiceCount: 2,
  };
  var screens = {};
  var current = "spread-type";
  var FLOW = [
    "spread-type",
    "three-type",
    "deck",
    "reverse",
    "question",
    "shuffle",
    "result",
    "interpretation",
  ];

  // ---------- Утилиты ----------
  function $(id) {
    return document.getElementById(id);
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function haptic(t) {
    try {
      if (tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred)
        tg.HapticFeedback.impactOccurred(t || "light");
    } catch (e) { }
  }
  function showAlert(msg) {
    try {
      if (
        tg &&
        tg.isVersionAtLeast &&
        tg.isVersionAtLeast("6.2") &&
        tg.showAlert
      ) {
        tg.showAlert(msg);
        return;
      }
    } catch (e) { }
    try {
      alert(msg);
    } catch (e) { }
  }
  function positionsFor() {
    var cfg = SPREADS[state.spreadType] || SPREADS.one;

    // Три карты — позиции зависят от подтипа
    if (state.spreadType === "three") {
      return (
        (cfg.positionsByType && cfg.positionsByType[state.threeType]) ||
        cfg.positionsByType["past-present-future"]
      );
    }

    // 🆕 Выбор пути — позиции генерируются ПОД РЕАЛЬНЫЕ ВАРИАНТЫ
    // Каждый вариант = Достоинство + Недостаток + Исход, в конце «Совет»
    if (state.spreadType === "choice") {
      var opts =
        state.choiceOptions && state.choiceOptions.length
          ? state.choiceOptions
          : ["Вариант 1", "Вариант 2"]; // запасной вариант, если данные пустые
      var pos = [];
      opts.forEach(function (opt, i) {
        var label = "В" + (i + 1) + ": " + (opt || "Вариант " + (i + 1));
        pos.push(label + " — Достоинство");
        pos.push(label + " — Недостаток");
        pos.push(label + " — Исход");
      });
      pos.push("Совет");
      return pos;
    }

    return cfg.positions;
  }
  // 🆕 ГЕНЕРАЦИЯ ПОЛЕЙ ДЛЯ ВАРИАНТОВ
  // 🆕 ИСПРАВЛЕННАЯ ГЕНЕРАЦИЯ ПОЛЕЙ ДЛЯ ВАРИАНТОВ В СТРОКУ
  function renderChoiceOptions() {
    var container = $("choice-options-container");
    if (!container) return;
    var sel = $("choice-count");
    var count = sel ? parseInt(sel.value, 10) || 2 : state.choiceCount || 2;
    count = Math.max(2, Math.min(3, count)); // защита от 1 и >3
    state.choiceCount = count;

    var html = "";
    for (var i = 1; i <= count; i++) {
      var val =
        state.choiceOptions && state.choiceOptions[i - 1]
          ? state.choiceOptions[i - 1]
          : "";
      // 🔑 Генерируем современную горизонтальную строку: текст + инпут в стиле textarea
      html +=
        '<div class="input-row-inline">' +
        "<label>Вариант " +
        i +
        "</label>" +
        '<input type="text" class="choice-option-input" data-index="' +
        (i - 1) +
        '" id="variant-' +
        i +
        '" placeholder="Описание варианта ' +
        i +
        '" value="' +
        esc(val) +
        '">' +
        "</div>";
    }
    container.innerHTML = html;

    // Навешиваем событие сохранения текста при вводе в каждый инпут
    var inputs = container.querySelectorAll(".choice-option-input");
    inputs.forEach(function (inp) {
      inp.addEventListener("input", function (e) {
        var idx = parseInt(e.target.dataset.index, 10);
        if (!state.choiceOptions) state.choiceOptions = [];
        state.choiceOptions[idx] = e.target.value;
      });
    });

    // Ленивая привязка слушателя смены количества (строго один раз)
    if (sel && !sel.dataset.bound) {
      sel.dataset.bound = "1";
      sel.addEventListener("change", renderChoiceOptions);
    }
  }

  // ---------- Навигация ----------
  function showScreen(id) {
    // 🆕 ПЕРЕХВАТ ДЛЯ ЭКРАНА ВОПРОСА
    if (id === "question") {
      var stdBlock = $("standard-question-block");
      var choiceBlock = $("choice-question-block");
      if (state.spreadType === "choice") {
        if (stdBlock) stdBlock.classList.add("hidden");
        if (choiceBlock) choiceBlock.classList.remove("hidden");
        renderChoiceOptions(); // Генерируем поля ввода вариантов
      } else {
        if (stdBlock) stdBlock.classList.remove("hidden");
        if (choiceBlock) choiceBlock.classList.add("hidden");
      }
    }
    current = id;
    haptic("light");
    Object.keys(screens).forEach(function (k) {
      if (screens[k]) screens[k].classList.remove("active");
    });
    var target = screens[id];
    if (target) target.classList.add("active");
    window.scrollTo(0, 0);
  }
  function goBack() {
    if (current === "deck-directory") {
      showScreen("start");
    } else if (current === "deck-categories") {
      showScreen("deck-directory");
    } else if (current === "deck-cards-list") {
      showScreen("deck-categories");
    } else {
      var idx = FLOW.indexOf(current);
      if (idx > 0) {
        var prev = FLOW[idx - 1];
        if (state.spreadType !== "three" && prev === "three-type")
          prev = FLOW[idx - 2] || "spread-type";
        showScreen(prev);
      } else if (current === "astro") {
        showScreen("start");
      } else if (tg && tg.close) {
        tg.close();
      }
    }
  }


  function goHome() {
    // УДАЛЕНО: tg.close() больше не вызывается, приложение не закроется!
    state.spreadType = null;
    state.threeType = null;
    state.deckId = null;
    state.question = "";
    state.cards = [];
    state.interpretation = "";

    // Сбрасываем видимость кнопок перемешивания, если они были изменены
    var shuffleBtn = $("shuffle-btn");
    if (shuffleBtn) shuffleBtn.classList.remove("hidden");
    var drawBtn = $("draw-btn");
    if (drawBtn) drawBtn.classList.add("hidden");

    // Возвращаем пользователя на самый первый экран выбора расклада
    showScreen("start");
  }

  // ---------- Колоды ----------
  function renderDecks(decks) {
    var box = $("deck-list");
    if (!box) return;
    box.innerHTML = "";
    decks.forEach(function (d) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "option-row deck-option";
      b.innerHTML =
        '<span class="icon">🎴</span><span class="text">' +
        esc(d.name) +
        '</span><span class="subtext">' +
        esc(d.cards_count) +
        " карт</span>";
      b.addEventListener("click", function () {
        state.deckId = d.deck_id;
        haptic("success");
        showScreen("reverse");
      });
      box.appendChild(b);
    });
  }
  function loadDecks() {
    fetch("/api/tarot/decks")
      .then(function (r) {
        return r.ok ? r.json() : Promise.reject(new Error("http " + r.status));
      })
      .then(function (list) {
        renderDecks(list && list.length ? list : FALLBACK_DECKS);
      })
      .catch(function () {
        renderDecks(FALLBACK_DECKS);
      });
  }

  // ---------- Перемешивание / вытягивание ----------
  function onShuffle() {
    haptic("medium");
    var stack = document.querySelector(".card-stack");
    var shuffleBtn = $("shuffle-btn"),
      drawBtn = $("draw-btn");
    if (shuffleBtn) shuffleBtn.disabled = true;
    if (stack) stack.classList.add("shuffling");
    setTimeout(function () {
      if (stack) stack.classList.remove("shuffling");
      if (shuffleBtn) shuffleBtn.classList.add("hidden");
      if (drawBtn) drawBtn.classList.remove("hidden");
      if (shuffleBtn) shuffleBtn.disabled = false;
      haptic("success");
    }, 900);
  }
  function performDraw() {
    var cfg = SPREADS[state.spreadType];
    if (!cfg || !state.deckId) {
      showAlert("Выберите расклад и колоду.");
      return;
    }

    // Динамический пересчёт количества карт для расклада "Выбор пути"
    var count = cfg.count;
    if (state.spreadType === "choice") {
      var optionCount = state.choiceCount || 2;
      count = optionCount * 3 + 1; // 3 карты на вариант + 1 карта "Совет"
    }

    showScreen("result");
    var container = $("result-cards-container");
    if (container)
      container.innerHTML = '<div class="loading-text">Вытягиваем карты…</div>';

    fetch("/api/tarot/draw", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        deck_id: state.deckId,
        count: count,
        spread_type: state.spreadType,
        use_reversed: state.useReversed,
      }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.cards || !data.cards.length)
          throw new Error("empty");
        state.cards = data.cards;
        renderResults();
      })
      .catch(function (e) {
        console.error("Draw error:", e);
        if (container) container.innerHTML = "";
        showAlert("Не удалось вытянуть карты. Попробуйте ещё раз.");
        showScreen("shuffle");
      });
  }
  /**
   * Отрисовка вытянутых карт Таро с поддержкой полноэкранного режима и тактильного отклика.
   */
  function renderResults() {
    // Переименовано в renderResults, так как в performDraw вызывается именно она
    var container = $("result-cards-container"); // Исправлен ID контейнера в соответствии с performDraw
    if (!container) return;
    container.innerHTML = "";
    var positions = positionsFor();

    state.cards.forEach(function (card, i) {
      var cardItem = document.createElement("div");
      cardItem.className =
        "tarot-card-item" + (card.reversed ? " reversed" : "");
      cardItem.style.animationDelay = i * 0.1 + "s";

      // 1) Изображение карты
      var imgUrl = card.image_url || card.image || null;
      if (imgUrl) {
        var img = document.createElement("img");
        img.className = "card-image";
        img.alt = card.name || "";
        img.src = imgUrl;
        img.onerror = function () {
          var ph = document.createElement("div");
          ph.className = "card-image card-placeholder";
          ph.textContent = "🎴";
          img.replaceWith(ph);
        };
        cardItem.appendChild(img);
      } else {
        var ph = document.createElement("div");
        ph.className = "card-image card-placeholder";
        ph.textContent = "🎴";
        cardItem.appendChild(ph);
      }

      // 2) Название карты
      var nameLabel = document.createElement("div");
      nameLabel.className = "card-name";
      nameLabel.textContent = (card.name || "") + (card.reversed ? " 🔻" : "");
      cardItem.appendChild(nameLabel);

      // 3) Подпись позиции в раскладе
      var posLabel = document.createElement("div");
      posLabel.className = "card-pos";
      posLabel.textContent = positions[i] || "Позиция " + (i + 1);
      cardItem.appendChild(posLabel);

      // 4) Логика интерактивного увеличения карты во весь экран
      cardItem.addEventListener("click", function (e) {
        e.stopPropagation();
        if (cardItem.classList.contains("fullscreen")) {
          cardItem.classList.remove("fullscreen");
          haptic("light");
        } else {
          document
            .querySelectorAll(".tarot-card-item.fullscreen")
            .forEach(function (el) {
              el.classList.remove("fullscreen");
            });
          cardItem.classList.add("fullscreen");
          haptic("medium");
        }
      });

      // Добавляем готовую карту в контейнер
      container.appendChild(cardItem);
    });
  }

  // ---------- РЕАЛЬНОЕ толкование LLM ----------
  // (Дальше идет ваша функция fetchInterpretation без изменений...)

  // ---------- РЕАЛЬНОЕ толкование LLM ----------
  function fetchInterpretation() {
    var box = $("interpretation-text");
    if (!box) return;
    box.textContent = "Звезды шепчут ответ…";
    box.className = "interpretation-box loading-text";
    var payload = {
      deck_id: state.deckId,
      spread_type: state.spreadType,
      three_card_type: state.threeType,
      question: state.question,
      positions: positionsFor(),
      use_reversed: state.useReversed,
      cards: state.cards.map(function (c) {
        return {
          card_id: c.card_id,
          name: c.name,
          reversed: !!c.reversed,
          astrology: c.astrology || "",
          keywords: c.keywords || [],
        };
      }),
    };
    fetch("/api/tarot/interpret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (res) {
        if (res.ok && res.j && res.j.interpretation) {
          state.interpretation = res.j.interpretation;
          box.className = "interpretation-box";
          box.textContent = res.j.interpretation; // white-space: pre-wrap сохранит абзацы
        } else {
          box.className = "interpretation-box error-text";
          box.textContent =
            res.j && res.j.error
              ? res.j.error
              : "Не удалось получить толкование. Попробуйте позже.";
        }
      })
      .catch(function () {
        box.className = "interpretation-box error-text";
        box.textContent = "Нет связи с сервером. Попробуйте позже.";
      });
  }

  function resetToShuffle() {
    state.cards = [];
    state.interpretation = "";
    var rc = $("result-cards-container");
    if (rc) rc.innerHTML = "";
    var it = $("interpretation-text");
    if (it) {
      it.textContent = "Звезды шепчут ответ…";
      it.className = "interpretation-box loading-text";
    }
    var shuffleBtn = $("shuffle-btn"),
      drawBtn = $("draw-btn");
    if (shuffleBtn) shuffleBtn.classList.remove("hidden");
    if (drawBtn) drawBtn.classList.add("hidden");
    showScreen("shuffle");
  }

  // ---------- Астрология ----------
  function fillSelect(id, items) {
    var sel = $(id);
    if (!sel) return;
    sel.innerHTML = '<option value="">Выберите…</option>';
    items.forEach(function (it) {
      var o = document.createElement("option");
      if (typeof it === "string") {
        o.value = it;
        o.textContent = it;
      } else {
        o.value = it.id;
        o.textContent = it.name;
      }
      sel.appendChild(o);
    });
  }
  // ---------- Астрология ----------
  // ---------- Исправленная Астрология (Параметры + Текст) ----------
  function sendAstro(e) {
    e.preventDefault();
    var p1 = $("planet1").value,
      s1 = $("sign1").value,
      a = $("aspect-type").value,
      p2 = $("planet2").value,
      s2 = $("sign2").value;
    if (!p1 || !s1 || !a || !p2 || !s2) {
      showAlert("Заполните все поля параметров.");
      return;
    }
    var aName =
      (
        ASPECTS.filter(function (x) {
          return x.id === a;
        })[0] || {}
      ).name || a;
    var query = aName + ": " + p1 + " в " + s1 + " и " + p2 + " в " + s2;

    executeAstroQuery(query, e);
  }

  // Универсальный движок отправки запроса на сервер
  function executeAstroQuery(query, e) {
    var box = $("interpretation-text");
    if (!box) return;
    box.textContent = "Звезды шепчут ответ…";
    box.className = "interpretation-box loading-text";

    // 🔑 Переключаем кнопки навигации внизу: прячем Таро, показываем Астрологию
    var tarotNav = $("interpretation-tarot-nav");
    var astroNav = $("interpretation-astro-nav");
    if (tarotNav) tarotNav.classList.add("hidden");
    if (astroNav) astroNav.classList.remove("hidden");

    showScreen("interpretation");

    fetch("/api/astro/interpret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (res) {
        if (res.ok && res.j && res.j.interpretation) {
          box.className = "interpretation-box";
          box.textContent = res.j.interpretation;
        } else {
          box.className = "interpretation-box error-text";
          box.textContent =
            res.j && res.j.error
              ? res.j.error
              : "Не удалось получить толкование.";
        }
      })
      .catch(function () {
        box.className = "interpretation-box error-text";
        box.textContent = "Нет связи с сервером. Попробуйте позже.";
      });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const choiceCountSelect = document.getElementById("choice-count");
    const container = document.getElementById("choice-options-container");

    // Функция генерации полей ввода в одну строчку
    function renderVariantInputs(count) {
      container.innerHTML = ""; // Полностью очищаем контейнер перед новой сборкой

      for (let i = 1; i <= count; i++) {
        // Создаем обертку-строку
        const row = document.createElement("div");
        row.className = "input-row-inline"; // Применяет наши красивые CSS стили

        // Генерируем структуру строки: надпись + премиум инпут
        row.innerHTML = `
                <label>Вариант ${i}</label>
                <input type="text" id="variant-${i}" placeholder="Например: Описание варианта ${i}">
            `;

        container.appendChild(row);
      }
    }

    // Инициализация: создаем базовые 2 поля при первой загрузке страницы
    if (choiceCountSelect && container) {
      renderVariantInputs(parseInt(choiceCountSelect.value));

      // Отслеживаем переключение количества вариантов пользователем
      choiceCountSelect.addEventListener("change", (e) => {
        renderVariantInputs(parseInt(e.target.value));
      });
    }
  });

  // ---------- Инициализация ----------
  function init() {
    [
      "start",
      "spread-type",
      "three-type",
      "deck",
      "reverse",
      "question",
      "shuffle",
      "result",
      "interpretation",
      "astro",
      "deck-directory",
      "deck-cards-list",
      "deck-categories",
    ].forEach(function (id) {
      screens[id] = $("screen-" + id);
    });

    document.querySelectorAll(".btn-back").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        goBack();
      });
    });
    document.querySelectorAll(".btn-home").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        goHome();
      });
    });
    // Логика переходов со Стартового экрана
    var btnGoTarot = $('btn-go-tarot');
    if (btnGoTarot) {
      btnGoTarot.addEventListener('click', function () {
        haptic('success');
        showScreen('spread-type'); // Переходим на выбор раскладов Таро
      });
    }

    var btnGoAstro = $('btn-go-astro');
    if (btnGoAstro) {
      btnGoAstro.addEventListener('click', function () {
        haptic('success');
        showScreen('astro'); // Переходим сразу на экран Астрологии
      });
    }

    document.querySelectorAll(".spread-option").forEach(function (b) {
      b.addEventListener("click", function () {
        state.spreadType = b.getAttribute("data-type");
        haptic("success");
        showScreen(state.spreadType === "three" ? "three-type" : "deck");
      });
    });
    document.querySelectorAll(".three-type-option").forEach(function (b) {
      b.addEventListener("click", function () {
        state.threeType = b.getAttribute("data-type");
        haptic("success");
        showScreen("deck");
      });
    });
    var ry = $("reverse-yes"),
      rn = $("reverse-no");
    if (ry)
      ry.addEventListener("click", function () {
        state.useReversed = true;
        haptic("success");
        showScreen("question");
      });
    if (rn)
      rn.addEventListener("click", function () {
        state.useReversed = false;
        haptic("success");
        showScreen("question");
      });

    var sq = $("submit-question-btn");
    if (sq)
      sq.addEventListener("click", function () {
        if (state.spreadType === "choice") {
          var essence = $("choice-essence")
            ? $("choice-essence").value.trim()
            : "";
          if (!essence) {
            haptic("error");
            showAlert("Пожалуйста, опишите суть выбора.");
            return;
          }

          var inputs = document.querySelectorAll(".choice-option-input");
          var opts = [];
          var valid = true;
          inputs.forEach(function (inp) {
            var val = inp.value.trim();
            if (!val) valid = false;
            opts.push(val);
          });
          if (!valid) {
            haptic("error");
            showAlert("Пожалуйста, заполните все варианты.");
            return;
          }

          state.choiceEssence = essence;
          state.choiceOptions = opts;

          // 🧠 Формируем идеальный промпт для LLM (ИИ поймет контекст каждого варианта)
          var q = "Суть выбора: " + essence + "\n";
          opts.forEach(function (opt, i) {
            q += "Вариант " + (i + 1) + ": " + opt + "\n";
          });
          state.question = q;

          // 🆕 Динамически задаем количество карт для API (3 карты на вариант + 1 Совет)
          SPREADS.choice.count = opts.length * 3 + 1;
        } else {
          var v = ($("question-input") ? $("question-input").value : "").trim();
          if (!v) {
            haptic("error");
            showAlert("Пожалуйста, введите вопрос перед продолжением.");
            return;
          }
          state.question = v;
        }
        // 🆕 Слушатель изменения количества вариантов
        var choiceCountSel = $("choice-count");
        if (choiceCountSel) {
          choiceCountSel.addEventListener("change", renderChoiceOptions);
        }
        haptic("success");
        showScreen("shuffle"); // Переход к перемешиванию
      });

    var sh = $("shuffle-btn");
    if (sh) sh.addEventListener("click", onShuffle);
    var dr = $("draw-btn");
    if (dr) dr.addEventListener("click", performDraw);
    var gi = $("get-interpretation-btn");
    if (gi)
      gi.addEventListener("click", function () {
        haptic("success");

        // 🔑 Принудительно возвращаем кнопки Таро на экране интерпретации
        var tarotNav = $("interpretation-tarot-nav");
        var astroNav = $("interpretation-astro-nav");
        if (tarotNav) tarotNav.classList.remove("hidden");
        if (astroNav) astroNav.classList.add("hidden");

        showScreen("interpretation");
        fetchInterpretation();
      });

    var rs = $("retry-spread-btn");
    if (rs)
      rs.addEventListener("click", function () {
        haptic("light");
        resetToShuffle();
      });
    document
      .querySelectorAll('[data-action="back-to-cards"]')
      .forEach(function (b) {
        b.addEventListener("click", function () {
          showScreen("result");
        });
      });
    var nr = $("new-reading-btn");
    if (nr)
      nr.addEventListener("click", function () {
        resetToShuffle();
      });
    var oa = $("open-astro");
    if (oa)
      oa.addEventListener("click", function () {
        showScreen("astro");
      });
    var form = $("astrology-form");
    if (form) form.addEventListener("submit", sendAstro);

    fillSelect("planet1", PLANETS);
    fillSelect("planet2", PLANETS);
    fillSelect("sign1", SIGNS);
    fillSelect("sign2", SIGNS);
    fillSelect("aspect-type", ASPECTS);

    loadDecks();
    showScreen('start'); // 🔑 Открываем стартовый экран при первом запуске Mini App
    console.log('Mini App v4.1 initialized with Start Screen');

    // 1. Логика переключения вкладок в Астрологии
    var modeParamsBtn = $("mode-params-btn");
    var modeTextBtn = $("mode-text-btn");
    var astroForm = $("astrology-form");
    var astroTextBlock = $("astro-text-block");

    if (modeParamsBtn && modeTextBtn) {
      modeParamsBtn.addEventListener("click", function () {
        modeParamsBtn.classList.add("active");
        modeTextBtn.classList.remove("active");
        if (astroForm) astroForm.classList.remove("hidden");
        if (astroTextBlock) astroTextBlock.classList.add("hidden");
        haptic("light");
      });

      modeTextBtn.addEventListener("click", function () {
        modeTextBtn.classList.add("active");
        modeParamsBtn.classList.remove("active");
        if (astroForm) astroForm.classList.add("hidden");
        if (astroTextBlock) astroTextBlock.classList.remove("hidden");
        haptic("light");
      });
    }

    // 2. Логика отправки свободного текстового вопроса в LLM
    var submitAstroTextBtn = $("submit-astro-text-btn");
    if (submitAstroTextBtn) {
      submitAstroTextBtn.addEventListener("click", function (e) {
        var freeText = (
          $("astro-free-question") ? $("astro-free-question").value : ""
        ).trim();
        if (!freeText) {
          haptic("error");
          showAlert("Пожалуйста, введите ваш вопрос.");
          return;
        }

        // Имитируем объект события для повторного использования существующей функции sendAstro
        var fakeEvent = {
          preventDefault: function () { },
        };

        // Временно подменяем логику сбора текста внутри sendAstro
        // Передаем свободный текст напрямую в бэкенд
        executeAstroQuery(freeText, fakeEvent);
      });
    }

    // ============================================================
    // 📚 ИНТЕРАКТИВНЫЙ СПРАВОЧНИК КОЛОД (ИСПРАВЛЕННАЯ НАВИГАЦИЯ)
    // ============================================================

    // Глобальный стейт для кэширования карт открытой колоды
    var currentCatalogData = { deckId: '', deckName: '', allCards: [] };

    // 1. Открытие главного справочника колод
    var openDecksBtn = $('open-decks-directory-btn');
    if (openDecksBtn) {
      openDecksBtn.addEventListener('click', function () {
        haptic('light');
        showScreen('deck-directory');
        loadDirectoryDecks();
      });
    }

    // 2. Шаг назад: От экрана категорий к списку колод
    var backToDecksDirBtn = $('back-to-decks-dir-btn');
    if (backToDecksDirBtn) {
      backToDecksDirBtn.addEventListener('click', function () {
        haptic('light');
        showScreen('deck-directory');
      });
    }

    // 3. Шаг назад: От сетки карт к категориям
    var backToCategoriesBtn = $('back-to-categories-btn');
    if (backToCategoriesBtn) {
      backToCategoriesBtn.addEventListener('click', function () {
        haptic('light');
        showScreen('deck-categories');
      });
    }

    // Шаг А: Метод загрузки списка колод из бэкенда
    function loadDirectoryDecks() {
      var box = $('directory-deck-list');
      if (!box) return;
      box.innerHTML = '<div class="loading-text">Загрузка списка колод...</div>';

      fetch('/api/tarot/decks')
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (list) {
          box.innerHTML = '';
          var decks = (list && list.length) ? list : FALLBACK_DECKS;
          decks.forEach(function (d) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'option-row';
            btn.innerHTML = '<span class="icon">🎴</span><span class="text">' + esc(d.name) +
              '</span><span class="subtext">' + esc(d.cards_count) + ' карт</span>';

            // 🔑 ИСПРАВЛЕНО: Клик по колоде теперь ведет СТРОГО на шаг Б (Категории)
            btn.addEventListener('click', function () {
              haptic('success');
              preloadDeckAndShowCategories(d.deck_id, d.name, d.cards_count);
            });
            box.appendChild(btn);
          });
        })
        .catch(function () { box.innerHTML = '<div class="error-text">Ошибка загрузки колод</div>'; });
    }

    // Универсальный рендеринг кнопок мастей/знаков
    function createCategoryButton(container, emoji, name, clickHandler) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'option-row';
      btn.innerHTML = '<span class="icon">' + emoji + '</span><span class="text">' + esc(name) + '</span>';
      btn.addEventListener('click', function () {
        haptic('success');
        clickHandler();
      });
      container.appendChild(btn);
    }

    // Шаг Б: Загрузка всей колоды в кэш приложения и выстраивание меню категорий
    function preloadDeckAndShowCategories(deckId, deckName, cardsCount) {
      var catTitle = $('categories-deck-title');
      if (catTitle) catTitle.textContent = deckName;

      var catContainer = $('deck-categories-container');
      if (!catContainer) return;
      catContainer.innerHTML = '<div class="loading-text">Загрузка структуры колоды...</div>';
      showScreen('deck-categories');

      // 🔑 ИСПРАВЛЕНО: Запрашиваем структуру, но вместо генерации заглушек на клиенте 
      // используем реальные объекты карт, которые бэкенд прочитал из вашего deck.json
      fetch('/api/tarot/draw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck_id: deckId, count: cardsCount, use_reversed: false })
      })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (data) {
          catContainer.innerHTML = '';
          if (!data || !data.cards || !data.cards.length) {
            catContainer.innerHTML = '<div class="error-text">Колода пуста или недоступна на сервере</div>';
            return;
          }

          // 🔑 Сохраняем в кэш реальные карты со всеми их оригинальными свойствами
          currentCatalogData.deckId = deckId;
          currentCatalogData.deckName = deckName;
          currentCatalogData.allCards = data.cards;

          // Отрисовка кнопок категорий (Оракул / Таро)
          // 1. Логика для Оракула 146 карт -> Выбор по Знакам зодиака
          if (deckId === 'author_deck_146' || deckName.indexOf('146') !== -1) {
            var zodiacs = ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева', 'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы'];
            var zodiacIcons = {
              'Овен': '♈', 'Телец': '♉', 'Близнецы': '♊', 'Рак': '♋', 'Лев': '♌', 'Дева': '♍',
              'Весы': '♎', 'Скорпион': '♏', 'Стрелец': '♐', 'Козерог': '♑', 'Водолей': '♒', 'Рыбы': '♓'
            };

            zodiacs.forEach(function (zod) {
              createCategoryButton(catContainer, zodiacIcons[zod] || '🪐', zod, function () {
                // 🔑 ПРОДАКШН-ФИКС: Переводим в нижний регистр для частичного совпадения (например, "лев" в "Солнце во Льве")
                var filtered = currentCatalogData.allCards.filter(function (c) {
                  var cardAstro = (c.astrology || '').toLowerCase();
                  var searchZod = zod.toLowerCase();
                  return cardAstro.indexOf(searchZod) !== -1;
                });
                renderCatalogCardsGrid(zod, filtered);
              });
            });
          }
          else {
            var suits = [
              { id: 'major', name: 'Старшие Арканы', emoji: '✨' },
              { id: 'wands', name: 'Жезлы', emoji: '🔥' },
              { id: 'cups', name: 'Кубки', emoji: '🏆' },
              { id: 'swords', name: 'Мечи', emoji: '⚔️' },
              { id: 'pentacles', name: 'Пентакли', emoji: '💰' }
            ];
            suits.forEach(function (suit) {
              createCategoryButton(catContainer, suit.emoji, suit.name, function () {
                var filtered = currentCatalogData.allCards.filter(function (c) {
                  var nameL = (c.name || '').toLowerCase();
                  var astroL = (c.astrology || '').toLowerCase();
                  if (suit.id === 'major') {
                    return astroL.indexOf('старш') !== -1 || (
                      nameL.indexOf('жезл') === -1 && nameL.indexOf('кубк') === -1 &&
                      nameL.indexOf('меч') === -1 && nameL.indexOf('пентакл') === -1 &&
                      nameL.indexOf('чаш') === -1 && nameL.indexOf('диск') === -1 && nameL.indexOf('динари') === -1
                    );
                  }
                  if (suit.id === 'wands') return nameL.indexOf('жезл') !== -1 || astroL.indexOf('огн') !== -1;
                  if (suit.id === 'cups') return nameL.indexOf('кубк') !== -1 || nameL.indexOf('чаш') !== -1 || astroL.indexOf('вод') !== -1;
                  if (suit.id === 'swords') return nameL.indexOf('меч') !== -1 || astroL.indexOf('воздух') !== -1;
                  if (suit.id === 'pentacles') return nameL.indexOf('пентакл') !== -1 || nameL.indexOf('диск') !== -1 || nameL.indexOf('динари') !== -1 || astroL.indexOf('земл') !== -1;
                  return false;
                });
                renderCatalogCardsGrid(suit.name, filtered);
              });
            });
          }
        })
        .catch(function () { catContainer.innerHTML = '<div class="error-text">Не удалось загрузить категории колоды</div>'; });
    }

    // Шаг В: Отрисовка отфильтрованной сетки карт выбранной категории
    function renderCatalogCardsGrid(categoryName, cardsList) {
      var title = $('selected-deck-title');
      if (title) title.textContent = currentCatalogData.deckName + ' — ' + categoryName;

      var grid = $('directory-cards-grid');
      if (!grid) return;
      grid.innerHTML = '';
      showScreen('deck-cards-list');

      if (!cardsList || !cardsList.length) {
        grid.innerHTML = '<div class="loading-text">В этой категории карт пока нет.</div>';
        return;
      }

      cardsList.forEach(function (card) {
        var cardItem = document.createElement('div');
        cardItem.className = 'tarot-card-item';

        if (card.image_url) {
          var img = document.createElement('img');
          img.className = 'card-image';
          img.src = card.image_url;
          img.onerror = function () {
            this.src = '';
            this.className = 'card-image card-placeholder';
            this.parentNode.insertBefore(document.createTextNode('🎴'), this);
            this.remove();
          };
          cardItem.appendChild(img);
        } else {
          var ph = document.createElement('div'); ph.className = 'card-image card-placeholder'; ph.textContent = '🎴'; cardItem.appendChild(ph);
        }

        var nameLabel = document.createElement('div'); nameLabel.className = 'card-name'; nameLabel.textContent = card.name; cardItem.appendChild(nameLabel);
        var astroLabel = document.createElement('div'); astroLabel.className = 'card-pos'; astroLabel.textContent = card.astrology ? '🪐 ' + card.astrology : 'Архетип'; cardItem.appendChild(astroLabel);

        // Находим код клика на карту внутри функции renderCatalogCardsGrid:
        cardItem.addEventListener('click', function (e) {
          e.stopPropagation();
          haptic('medium');

          var box = $('interpretation-text');
          if (!box) return;

          var tarotNav = $("interpretation-tarot-nav"), astroNav = $("interpretation-astro-nav");
          if (tarotNav) tarotNav.classList.add('hidden');
          if (astroNav) astroNav.classList.remove('hidden');

          var backBtn = $('back-to-astro-btn');
          if (backBtn) {
            backBtn.innerHTML = '⬅️ Назад к списку карт';
            var newBack = backBtn.cloneNode(true);
            backBtn.replaceWith(newBack);
            newBack.addEventListener('click', function () { showScreen('deck-cards-list'); });
          }

          var keywords = card.keywords && card.keywords.length ? '\n🔑 <b>Ключевые слова:</b> ' + card.keywords.join(', ') : '';
          var astro = card.astrology ? '\n🪐 <b>Астрология / Символизм:</b> ' + card.astrology : '';

          // 🔑 ИСПРАВЛЕНО: Рендерим реальные поля, которые сервер извлек из файла deck.json вашей колоды
          var textHtml = '<h3>🎴 ' + esc(card.name) + '</h3>';
          textHtml += '<p style="color:var(--primary-color); margin-bottom:15px;">' + astro + keywords + '</p>';

          if (card.upright) textHtml += '<div style="margin-bottom:12px;"><b>✅ Общее значение:</b><br>' + card.upright + '</div>';
          if (card.reversed) textHtml += '<div style="margin-bottom:12px;"><b>🔻 Перевёрнутое положение:</b><br>' + card.reversed + '</div>';
          if (card.advice) textHtml += '<div style="margin-bottom:12px; color:var(--success-color);"><b>💡 Совет карты:</b><br>' + card.advice + '</div>';
          if (card.warning) textHtml += '<div style="margin-bottom:12px; color:var(--error-color);"><b>⚠️ Предупреждение:</b><br>' + card.warning + '</div>';
          if (card.business) textHtml += '<div style="margin-bottom:12px;"><b>💼 В работе и бизнесе:</b><br>' + card.business + '</div>';
          if (card.relationships) textHtml += '<div style="margin-bottom:12px;"><b>❤️ В отношениях:</b><br>' + card.relationships + '</div>';

          if (!card.upright && !card.advice) {
            textHtml += '<strong>📖 Описание архетипа и символизма:</strong><br>Данный показатель кодирует фундаментальные качества проявления архетипа в рамках методологии Школы «12 Планет».';
          }

          box.className = 'interpretation-box';
          box.style.whiteSpace = 'pre-wrap';
          box.innerHTML = textHtml;

          showScreen('interpretation');
        });
        grid.appendChild(cardItem);
      });
    }

    // Код в конце функции init() перед выводом логов:
    var backToAstroBtn = $("back-to-astro-btn");
    if (backToAstroBtn) {
      backToAstroBtn.addEventListener("click", function (e) {
        e.preventDefault();
        haptic("light");
        // 🔑 Возвращаем пользователя ровно на экран Астрологии
        showScreen("astro");
      });
    }

    // Открытие справочника колод
    var openDecksBtn = $('open-decks-directory-btn');
    if (openDecksBtn) {
      openDecksBtn.addEventListener('click', function () {
        haptic('light');
        showScreen('deck-directory');
        loadDirectoryDecks();
      });
    }

    // Кнопка возврата от карт к списку колод
    var backToDecksBtn = $('back-to-decks-list-btn');
    if (backToDecksBtn) {
      backToDecksBtn.addEventListener('click', function () {
        haptic('light');
        showScreen('deck-directory');
      });
    }

  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
