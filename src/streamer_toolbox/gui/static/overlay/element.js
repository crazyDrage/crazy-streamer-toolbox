// Draws a StreamElements "Element" (their newer kind of widget) from its settings, the toolbox's own way: an
// Element has no code of its own, it is a canvas size and a list of states, each with pictures, videos, sounds
// and texts ("compositeFields") that have a place, a look and an animation. A state without a condition is
// always there (background, idle, foreground: labels like "latest follower"); a state with one is shown when an
// event fits it (an alert: follow, sub, tip, cheer, raid, gifted subs), one after the other.
// Runs on a widget page (widget.js): the widget's JS part is TOOLBOX_ELEMENT.show(<the settings>), and the
// events come the way every widget gets them (onWidgetLoad, onEventReceived, onSessionUpdate).
// A file named without an address is in the widget's media folder (fetched when the Element was imported).
(() => {
  const MEDIA = "/overlay/widget/" + encodeURIComponent(window.TOOLBOX_WIDGET.name) + "/media/";
  const LAYER = {background: 1, static: 2, foreground: 4};  // alerts are layer 3
  const LONGEST = 60000;  // an alert whose video never ends is taken away after this

  let config = null;
  let root = null;
  let session = {};
  let currency = "$";
  const labels = [];  // the texts that are always there: filled again when the session data changes
  const waiting = [];  // events whose alert is still to come
  let showing = false;

  const seconds = text => (parseFloat(text) || 0) * (String(text).trim().endsWith("ms") ? 1 : 1000);
  const address = href => /^(https?:)?\/\//.test(href) || href.startsWith("/") ? href : MEDIA + href;
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

  // the words of a text field: what is filled in gets the field's highlight look
  function fillText(box, field, event) {
    box.replaceChildren();
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
    } else if (field.type === "text" || field.type === "latestTicker") {
      box = document.createElement("div");
      box.style.whiteSpace = field.type === "text" ? "pre-wrap" : "nowrap";
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
    box.style.cssText = "position: absolute; inset: 0; z-index: " + (event ? 3 : LAYER[state.referenceId] || 2);
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
      if (field.type === "text" || field.type === "latestTicker") {
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
    if (field.type === "text") fillText(box, field, event);
    into.append(box);
    const {enter = {}, static: hold = {}, exit = {}} = field.animation || {};
    const stays = seconds(hold.animationDuration);
    if (box.tagName === "VIDEO" && !stays) {
      play(box);
      return new Promise(over => { box.onended = over; box.onerror = over; });
    }
    if (box.tagName === "VIDEO") { box.loop = true; play(box); }
    const fade = (from, to, phase) => box.animate([{opacity: from}, {opacity: to}],
      {duration: seconds(phase.animationDuration), delay: seconds(phase.animationDelay), fill: "both"}).finished;
    const comes = enter.animationName ? fade(enter.opacity ?? 0, hold.opacity ?? 1, enter) : Promise.resolve();
    if (!stays) return null;
    return comes.then(() => new Promise(over => setTimeout(over, stays)))
      .then(() => exit.animationName ? fade(hold.opacity ?? 1, exit.opacity ?? 0, exit) : null);
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
  const always = state => (state.triggers || []).every(t => empty(t.systemCondition) && empty(t.userCondition));
  const fits = (trigger, data) => !empty(trigger.systemCondition) && holds(trigger.systemCondition, data)
    && (empty(trigger.userCondition) || holds(trigger.userCondition, data));

  // the state for an event: one with a condition of his own (a variation) before the plain one
  function stateFor(event) {
    const found = config.configStates.filter(state => !always(state) && state.triggers.some(t => fits(t, {event})));
    return found.find(state => state.triggers.some(t => !empty(t.userCondition) && fits(t, {event}))) || found[0];
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
    config.configStates.filter(always).forEach(stand);
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
    waiting.push(event);
    next();
  });

  window.TOOLBOX_ELEMENT = {
    show(settings) {
      config = {boundingBox: {width: 1920, height: 1080}, configStates: [], ...settings};
    },
  };
})();
