// Draws a StreamElements "Element" (their newer kind of widget) from its settings, the toolbox's own way: an
// Element has no code of its own, it is a canvas size and a list of states, each with pictures, videos, sounds
// and texts ("compositeFields") that have a place, a look and an animation. A state without a condition is
// always there (background, idle, foreground: labels like "latest follower"); a state with one is shown when an
// event fits it (an alert: follow, sub, tip, cheer, raid, gifted subs), one after the other.
// Runs on a widget page (widget.js): the widget's JS part is TOOLBOX_ELEMENT.show(<the settings>), and the
// events come the way every widget gets them (onWidgetLoad, onEventReceived, onSessionUpdate).
// A file named without an address is in the widget's media folder (fetched when the Element was imported).
// The widget editor's own additions (ElementDesign): shapes, goal bars (toolbox.goal), tickers of the recent
// ones (toolbox.ticker), a layer that is off or in front of the alerts (toolbox.off / toolbox.front), a
// condition by chance ({"var": "random"}, new for each event).
(() => {
  const MEDIA = "/overlay/widget/" + encodeURIComponent(window.TOOLBOX_WIDGET.name) + "/media/";
  const LAYER = {background: 1, static: 2, foreground: 4};  // alerts are layer 3
  const LONGEST = 60000;  // an alert whose video never ends is taken away after this

  let config = null;
  let root = null;
  let session = {};
  let currency = "$";
  const labels = [];  // the texts that are always there: filled again when the session data changes
  const reacting = [];  // the pieces that are always there and move when an event comes (the widget editor's)
  const waiting = [];  // events whose alert is still to come
  let showing = false;

  const seconds = text => (parseFloat(text) || 0) * (String(text).trim().endsWith("ms") ? 1 : 1000);
  const address = href => /^(https?:)?\/\//.test(href) || href.startsWith("/") ? href : MEDIA + href;
  // the widget editor's animations (the alert editor's names): how a piece comes in, goes out, or moves on an
  // event. A slide starts or ends outside the canvas. StreamElements' own (fade-in, ...) are a fade
  const away = () => config.boundingBox.height;
  const wide = () => config.boundingBox.width;
  const COMING = {
    fade: () => [{opacity: 0}, {}],
    slide_down: () => [{transform: `translateY(${-away()}px)`}, {transform: "none"}],
    slide_up: () => [{transform: `translateY(${away()}px)`}, {transform: "none"}],
    slide_left: () => [{transform: `translateX(${wide()}px)`}, {transform: "none"}],
    slide_right: () => [{transform: `translateX(${-wide()}px)`}, {transform: "none"}],
    zoom: () => [{opacity: 0, transform: "scale(0.5)"}, {transform: "none"}],
    pop: () => [{opacity: 0, transform: "scale(0.5)"}, {opacity: 1, transform: "scale(1.1)", offset: 0.7},
                {transform: "none"}],
  };
  const GOING = {
    fade: () => [{}, {opacity: 0}],
    slide_up: () => [{transform: "none"}, {transform: `translateY(${-away()}px)`}],
    slide_down: () => [{transform: "none"}, {transform: `translateY(${away()}px)`}],
    slide_left: () => [{transform: "none"}, {transform: `translateX(${-wide()}px)`}],
    slide_right: () => [{transform: "none"}, {transform: `translateX(${wide()}px)`}],
    zoom: () => [{transform: "none"}, {opacity: 0, transform: "scale(0.5)"}],
  };
  const REACTIONS = {
    pop: [{transform: "none"}, {transform: "scale(1.25)", offset: 0.4}, {transform: "none"}],
    shake: [0, -14, 14, -10, 10, -5, 0].map(x => ({transform: `translateX(${x}px)`})),
    jump: [{transform: "none"}, {transform: "translateY(-40px)", offset: 0.4}, {transform: "none", offset: 0.7},
           {transform: "translateY(-12px)", offset: 0.85}, {transform: "none"}],
    pulse: [{opacity: 1}, {opacity: 0.3}, {opacity: 1}, {opacity: 0.3}, {opacity: 1}],
    spin: [{transform: "rotate(0)"}, {transform: "rotate(360deg)"}],
    flash: [{filter: "none"}, {filter: "brightness(2.5)", offset: 0.3}, {filter: "none"}],
  };
  const file = (field, kind) => (field.media || []).find(m => String(m.mimeType || "").startsWith(kind) && m.role !== "placeholder");

  // {event.data.username}, {session.twitch.follower-latest.name}: the session data is the same for every platform
  function lookup(path, event, nth) {
    const parts = path.trim().split(".");
    let value;
    if (parts[0] === "session") {
      value = session;
      parts.splice(0, 2);
      if (nth !== undefined && parts[0]) {  // a ticker: the nth of the recent ones instead of the latest
        value = (session[parts[0].replace(/-latest$/, "-recent")] || [])[nth];
        parts.shift();
      }
    } else if (parts[0] === "event") {
      value = event || {data: {currency}};
      parts.shift();
    }
    for (const part of parts) value = value === undefined || value === null ? undefined : value[part];
    return value === undefined || value === null ? "" : String(value);
  }

  // a goal bar: how far the count is, and its words ({value} / {target}, {percent})
  function fillGoal(box, field) {
    const goal = (field.toolbox || {}).goal || {};
    const value = Number(lookup("session.twitch." + (goal.value || "follower-session.count"))) || 0;
    const target = Math.max(Number(goal.target) || 1, 1);
    const percent = Math.min(100, Math.floor(value / target * 100));
    box.tbFill.style.width = percent + "%";
    box.tbLabel.textContent = String(goal.label ?? "{value} / {target}").replaceAll("{value}", value)
      .replaceAll("{target}", target).replaceAll("{percent}", percent + "%");
  }

  // the editor's ticker: the recent ones' names (and amounts), running along, in a row, or one per line
  function fillTicker(box, field) {
    const ticker = field.toolbox.ticker;
    const sign = ticker.kind === "tip" ? currency : "";
    const names = (session[ticker.kind + "-recent"] || []).slice(0, ticker.count || 10).map(entry =>
      String(entry.name || "") + (ticker.amount && entry.amount ? ` (${sign}${entry.amount})` : ""));
    const between = ticker.look === "lines" ? "\n" : String(ticker.between ?? " ");
    const line = document.createElement(ticker.look === "run" ? "div" : "span");
    names.forEach((name, nth) => {
      const filled = document.createElement("span");
      Object.assign(filled.style, field.highlightedStyle || {});
      filled.textContent = name;
      line.append(filled);
      if (ticker.look === "run" || nth < names.length - 1) line.append(between);
    });
    box.append(line);
    if (ticker.look !== "run" || !names.length) return;
    line.style.display = "inline-block";
    line.style.whiteSpace = "pre";
    const once = [...line.childNodes];
    const times = line.offsetWidth ? 2 * Math.min(Math.ceil(box.clientWidth / line.offsetWidth), 50) : 2;
    for (let copy = 1; copy < times; copy++) line.append(...once.map(node => node.cloneNode(true)));
    const round = seconds(((field.animation || {}).static || {}).animationDuration) || 10000;
    line.animate([{transform: "translateX(0)"}, {transform: "translateX(-50%)"}], {duration: round * 2, iterations: Infinity});
  }

  // the words of a text field: what is filled in gets the field's highlight look
  function fillText(box, field, event) {
    if (field.type === "goal") return fillGoal(box, field);
    box.replaceChildren();
    if (field.type === "latestTicker" && (field.toolbox || {}).ticker) return fillTicker(box, field);
    const content = (field.text || []).map(line => line.content || "").join("\n");
    const say = (text, nth) => {
      text.split(/\{([^{}]+)\}/).forEach((piece, index) => {
        if (index % 2 === 0) return box.append(piece);
        const filled = document.createElement("span");
        Object.assign(filled.style, field.highlightedStyle || {});
        filled.textContent = lookup(piece, event, nth);
        box.append(filled);
      });
    };
    if (field.type !== "latestTicker") return say(content);
    // a ticker names the latest one many times: each time is the next of the recent ones, as many as there are
    const line = document.createElement("div");
    line.style.display = "inline-block";
    const outer = box;
    box = line;
    content.split(/(?<=\/)/).forEach((piece, nth) => {
      const names = [...piece.matchAll(/\{session\.[^.}]+\.([^.}]+)-latest/g)].map(found => found[1]);
      if (names.every(name => (session[name + "-recent"] || [])[nth])) say(piece, nth);
    });
    outer.append(line);
    // it runs round: as many times side by side as fill the strip, and all of that twice
    const once = [...line.childNodes];
    const times = once.length && line.offsetWidth ? 2 * Math.min(Math.ceil(outer.clientWidth / line.offsetWidth), 50) : 1;
    for (let copy = 1; copy < times; copy++) line.append(...once.map(node => node.cloneNode(true)));
    const round = seconds(((field.animation || {}).static || {}).animationDuration) || 8000;
    line.animate([{transform: "translateX(0)"}, {transform: "translateX(-50%)"}], {duration: round * 2, iterations: Infinity});
  }

  function make(field) {
    let box = null;
    if (field.type === "image" && file(field, "image")) {
      box = document.createElement("img");
      box.src = address(file(field, "image").href);
    } else if (field.type === "video" && file(field, "video")) {
      box = document.createElement("video");
      box.src = address(file(field, "video").href);
      box.volume = Math.max(0, Math.min(Number(field.volume ?? 1), 1));
      box.playbackRate = Number(field.playbackRate) || 1;
      box.playsInline = true;
    } else if (field.type === "shape") {
      box = document.createElement("div");
    } else if (field.type === "goal") {
      box = document.createElement("div");
      box.style.overflow = "hidden";
      box.tbFill = document.createElement("div");
      box.tbFill.style.cssText = "position: absolute; left: 0; top: 0; bottom: 0; width: 0; transition: width 0.8s ease";
      Object.assign(box.tbFill.style, field.fillStyle || {});
      box.tbLabel = document.createElement("div");
      box.tbLabel.style.cssText = "position: absolute; inset: 0; display: flex; align-items: center; " +
        "justify-content: center; white-space: nowrap";
      box.append(box.tbFill, box.tbLabel);
    } else if (field.type === "text" || field.type === "latestTicker") {
      box = document.createElement("div");
      box.style.whiteSpace = field.type === "text" ? "pre-wrap" : "nowrap";  // (a ticker's own style may say)
      if (field.type === "latestTicker") box.style.overflow = "hidden";
      for (const font of (field.media || []).filter(m => m.role === "font-face" && m.href)) addFont(address(font.href));
    }
    if (box) {
      box.style.position = "absolute";
      Object.assign(box.style, field.style || {});
    }
    return box;
  }

  function addFont(href) {
    if ([...document.styleSheets].some(sheet => sheet.href && sheet.href.endsWith(href))) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.append(link);
  }

  // a video starts; a page that may not play sound yet (a browser before a click, not OBS) plays it silent
  function play(video) {
    return video.play().catch(() => { video.muted = true; return video.play(); }).catch(() => {});
  }

  function layer(state, event) {
    const box = document.createElement("div");
    const front = (state.toolbox || {}).front ?? state.referenceId === "foreground";
    box.style.cssText = "position: absolute; inset: 0; z-index: " +
      (event ? 3 : front ? LAYER.foreground : state.referenceId === "background" ? LAYER.background : LAYER.static);
    root.append(box);
    return box;
  }

  // a state that is always there: everything in it stands, a video runs round
  function stand(state) {
    const into = layer(state, null);
    for (const field of Object.values((state.settings || {}).compositeFields || {})) {
      const box = make(field);
      if (!box) continue;
      if (box.tagName === "VIDEO") { box.loop = true; play(box); }
      into.append(box);
      if (((field.toolbox || {}).react || {}).events) reacting.push([box, field.toolbox.react]);
      if (field.type === "text" || field.type === "latestTicker" || field.type === "goal") {
        labels.push([box, field]);
        fillText(box, field, null);
      }
    }
  }

  // one piece of an alert, from coming in to going out; gives a promise for "it is over", or null for a piece
  // without a length of its own (it stays as long as the others)
  function perform(field, box, into, event) {
    if (field.type === "audio") {
      const sound = file(field, "audio");
      if (!sound) return null;
      const audio = new Audio(address(sound.href));
      audio.volume = Math.max(0, Math.min(Number(field.volume ?? 1), 1));
      const start = setTimeout(() => audio.play().catch(() => {}), (Number(field.delaySeconds) || 0) * 1000);
      into.stop.push(() => { clearTimeout(start); audio.pause(); });
      return null;
    }
    if (!box) return null;
    into.append(box);
    if (["text", "latestTicker", "goal"].includes(field.type)) fillText(box, field, event);
    const {enter = {}, static: hold = {}, exit = {}} = field.animation || {};
    const stays = seconds(hold.animationDuration);
    if (box.tagName === "VIDEO" && !stays) {
      play(box);
      return new Promise(over => { box.onended = over; box.onerror = over; });
    }
    if (box.tagName === "VIDEO") { box.loop = true; play(box); }
    const timing = phase => ({duration: seconds(phase.animationDuration), delay: seconds(phase.animationDelay),
                              fill: "both"});
    const move = (phase, ours, from, to) => box.animate(
      ours[phase.animationName] ? ours[phase.animationName]() : [{opacity: from}, {opacity: to}], timing(phase)).finished;
    const comes = enter.animationName ? move(enter, COMING, enter.opacity ?? 0, hold.opacity ?? 1) : Promise.resolve();
    if (!stays) return null;
    return comes.then(() => new Promise(over => setTimeout(over, stays)))
      .then(() => exit.animationName ? move(exit, GOING, hold.opacity ?? 1, exit.opacity ?? 0) : null);
  }

  async function alertFor(state, event) {
    const into = layer(state, event);
    into.stop = [];
    const fields = Object.values((state.settings || {}).compositeFields || {});
    const lengths = fields.map(field => perform(field, make(field), into, event)).filter(Boolean);
    const all = lengths.length ? Promise.all(lengths) : new Promise(over => setTimeout(over, 5000));
    await Promise.race([all.catch(() => {}), new Promise(over => setTimeout(over, LONGEST))]);
    into.stop.forEach(stop => stop());
    into.remove();
  }

  // a small reader for the conditions (JsonLogic): what the Elements seen so far use, and its neighbours
  function holds(rule, data) {
    if (rule === null || typeof rule !== "object") return rule;
    if (Array.isArray(rule)) return rule.map(part => holds(part, data));
    const [name] = Object.keys(rule);
    if (name === undefined) return true;
    const given = [].concat(rule[name]);
    if (name === "var") return String(given[0]).split(".").reduce((value, key) => value == null ? undefined : value[key], data) ?? given[1];
    if (name === "and") return given.every(part => holds(part, data));
    if (name === "or") return given.some(part => holds(part, data));
    const [a, b] = given.map(part => holds(part, data));
    switch (name) {
      case "==": return a == b;
      case "===": return a === b;
      case "!=": return a != b;
      case "!==": return a !== b;
      case ">": return a > b;
      case ">=": return a >= b;
      case "<": return a < b;
      case "<=": return a <= b;
      case "!": return !a;
      case "in": return b != null && b.includes(a);
      default: return false;  // a word this reader doesn't know: the state isn't shown
    }
  }

  const empty = rule => !rule || !Object.keys(rule).length;
  const on = state => !(state.toolbox || {}).off;
  const always = state => (state.triggers || []).every(t => empty(t.systemCondition) && empty(t.userCondition));
  const fits = (trigger, data) => !empty(trigger.systemCondition) && holds(trigger.systemCondition, data)
    && (empty(trigger.userCondition) || holds(trigger.userCondition, data));

  // the state for an event: one with a condition of his own (a variation) before the plain one
  // (an imported Element: the first in the list that fits; one saved in the widget editor, toolbox.top_first:
  // the last, as the editor lists them the other way round, the top one first); a chance is one number for
  // the event, so of two with 50% one plays
  function stateFor(event) {
    const data = {event, random: Math.random()};
    const found = config.configStates.filter(state => on(state) && !always(state) && state.triggers.some(t => fits(t, data)));
    const order = (config.toolbox || {}).top_first ? [...found].reverse() : found;
    return order.find(state => state.triggers.some(t => !empty(t.userCondition) && fits(t, data))) || found[0];
  }

  async function next() {
    if (showing) return;
    showing = true;
    while (waiting.length) {
      const event = waiting.shift();
      const state = stateFor(event);
      if (state) await alertFor(state, event);
    }
    showing = false;
  }

  // a widget event of the toolbox (listener "follower-latest", {name, amount, ...}) in an Element's words
  function elementEvent(listener, told) {
    const kind = listener.replace(/-latest$/, "");
    if (kind === listener || !told) return null;
    const type = kind === "follower" ? "follow" : kind === "subscriber" && told.bulkGifted ? "communityGiftPurchase" : kind;
    return {topic: "event", type, provider: "twitch", data: {
      username: told.name, displayName: told.name, amount: told.amount, message: told.message || "",
      gifted: Boolean(told.gifted), tier: told.tier, sender: told.sender, currency,
    }};
  }

  function fit() {
    root.style.transform = "scale(" + innerWidth / config.boundingBox.width + ")";
  }

  function begin() {
    root = document.getElementById("toolbox-element");
    if (!root || !config) return;
    root.replaceChildren();
    root.style.cssText = `position: absolute; left: 0; top: 0; width: ${config.boundingBox.width}px; ` +
      `height: ${config.boundingBox.height}px; overflow: hidden; transform-origin: top left`;
    fit();
    addEventListener("resize", fit);
    config.configStates.filter(state => always(state) && on(state)).forEach(stand);
  }

  addEventListener("onWidgetLoad", load => {
    session = (load.detail.session || {}).data || {};
    currency = (load.detail.currency || {}).symbol || "$";
    begin();
  });
  addEventListener("onSessionUpdate", update => {
    session = update.detail.session || {};
    for (const [box, field] of labels) fillText(box, field, null);
  });
  addEventListener("onEventReceived", received => {
    const event = elementEvent(received.detail.listener, received.detail.event);
    if (!event || !config) return;
    const kind = received.detail.listener.replace(/-latest$/, "");
    const category = event.type === "follow" ? "follower" : event.type;
    for (const [box, react] of reacting) {
      if (react.events.includes(category) || react.events.includes(kind)) {
        box.animate(REACTIONS[react.animation] || REACTIONS.pop, {duration: (react.seconds || 0.8) * 1000});
      }
    }
    waiting.push(event);
    next();
  });

  window.TOOLBOX_ELEMENT = {
    show(settings) {
      config = {boundingBox: {width: 1920, height: 1080}, configStates: [], ...settings};
    },
  };
})();
