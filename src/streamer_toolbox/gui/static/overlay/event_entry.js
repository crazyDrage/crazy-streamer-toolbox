// The widget editor's event list (his round 89: an event history, a chat history, ...): each event that comes
// is drawn as a small table of its own (EntryTable: cells with a text, a picture or a video; a text and a
// picture's address have the event's values by their names, {user}) and put
// into the list where new ones come in; the others move away, the oldest go when the
// list is full or (a setting) after some seconds. Used on the widget page (element.js) and in the editor
// (widget_designer.js, the same drawing with example events), so what he sees there is what OBS shows.
(() => {
  const FROM = {top: "translateY(-100%)", bottom: "translateY(100%)", left: "translateX(-100%)", right: "translateX(100%)"};

  // {user} → the event's value of that name; a name the event has no value of stays as it is (he sees it).
  // A list of things (a chat message's emotes) shows their names
  function fill(text, data) {
    return String(text || "").replace(/\{([\w-]+)\}/g, (code, key) => {
      if (!(key in data)) return code;
      const value = data[key];
      if (Array.isArray(value)) return value.map(one => one && typeof one === "object" ? one.name ?? "" : one).join(" ");
      return value ?? "";
    });
  }

  // where a picture or video cell's address (filled in) is loaded from: a web address as it is, a path on this
  // PC through the widget's own route (opts.local; the toolbox gives only what its addresses make), a kept file
  // (/toolbox/media/...) from the toolbox
  function source(address, opts) {
    // the media buffer's files (box "Keep media locally") are on the toolbox's own address
    if (/^(https?:|data:|blob:)/i.test(address) || address.startsWith("/toolbox/media/")) return address;
    return opts.local ? opts.local + encodeURIComponent(address) : "";
  }

  // an emoji dictionary, {"Kappa": a picture's address}: an object, or one written as JSON text
  function dictionary(found) {
    if (typeof found === "string") {
      try { found = JSON.parse(found); } catch { return null; }
    }
    return found && typeof found === "object" && !Array.isArray(found) ? found : null;
  }

  // the words as text and, where a word is in the dictionary, its picture (his 2026-11-16: the text's
  // emoji_dict). Only whole words (between spaces), with their capitals: "Kappa" but not "kappa" or "Kappas".
  // Chat is what anyone writes: it only ever goes in as text, never as HTML
  function withEmoji(box, text, emoji, size, opts) {
    for (const part of text.split(/(\s+)/)) {
      const address = part && Object.prototype.hasOwnProperty.call(emoji, part) ? String(emoji[part] || "").trim() : "";
      const src = address ? source(address, opts) : "";
      if (!src) {
        box.append(document.createTextNode(part));
        continue;
      }
      const seen = document.createElement("img");
      seen.alt = seen.title = part;
      seen.draggable = false;
      seen.style.cssText = "display: inline-block; vertical-align: middle; width: auto";
      seen.style.height = size ? size + "px" : "1.4em";
      seen.onerror = () => seen.replaceWith(document.createTextNode(part));  // no picture: the word again
      seen.src = src;
      box.append(seen);
    }
  }

  // a style's value can be one of the event's too ({color}: their name colour)
  function filled(style, data) {
    return Object.fromEntries(Object.entries(style || {}).map(([key, value]) => [key, typeof value === "string" ? fill(value, data) : value]));
  }

  // where a picture or video (a cell's, a layer's) comes from: its address filled in, else its file
  function sourceOf(own, data, opts) {
    const address = fill(own.address, data).trim();
    return address ? source(address, opts) : own.file ? (opts.media || (f => f))(own.file) : "";
  }

  // a layer behind (z 0) or in front (z 2) of the cells (z 1): covers the whole entry, its corners too
  // (his round 90: a picture as every event's background, a glass in front)
  function layer(own, z, data, opts) {
    const src = sourceOf(own, data, opts);
    if (!src) return null;
    const fit = own.fit || "cover";
    const seen = document.createElement(own.kind === "video" ? "video" : "div");
    seen.style.cssText = "position: absolute; inset: 0; width: 100%; height: 100%; border-radius: inherit; pointer-events: none";
    seen.style.zIndex = String(z);
    seen.style.opacity = String(own.opacity ?? 1);
    if (own.kind === "video") {
      Object.assign(seen, {muted: true, autoplay: true, loop: true, playsInline: true});
      seen.style.objectFit = fit === "repeat" ? "cover" : fit;
      seen.onerror = () => seen.remove();
      seen.src = src;
    } else {
      seen.style.backgroundImage = `url(${JSON.stringify(src)})`;
      seen.style.backgroundPosition = "center";
      seen.style.backgroundRepeat = fit === "repeat" ? "repeat" : "no-repeat";
      seen.style.backgroundSize = {cover: "cover", contain: "contain", fill: "100% 100%", repeat: "auto"}[fit] || "cover";
    }
    return seen;
  }

  // one event as its table: a CSS grid, each cell where its column and row say; opts.values(data): values it
  // gets besides
  function draw(table, given, opts = {}) {
    const data = {...given, ...(opts.values ? opts.values(given) : {})};
    const entry = document.createElement("div");
    entry.style.cssText = "display: grid; flex-shrink: 0; box-sizing: border-box; align-items: center; position: relative; isolation: isolate";
    // the last column takes what is left over (a long message under a picture and a name): the others stay as
    // narrow as what they hold, so a 25px picture has its name right next to it (his 11-16)
    const columns = Math.max(Number(table.columns) || 1, 1);
    entry.style.gridTemplateColumns = columns > 1 ? `repeat(${columns - 1}, auto) 1fr` : "auto";
    entry.style.columnGap = entry.style.rowGap = "6px";
    Object.assign(entry.style, filled(table.style, data));
    for (const cell of table.cells || []) {
      const box = document.createElement("div");
      box.style.gridColumn = `${cell.col + 1} / span ${cell.cols}`;
      box.style.gridRow = `${cell.row + 1} / span ${cell.rows}`;
      box.style.minWidth = "0";
      box.style.position = "relative";
      box.style.zIndex = "1";
      box.style.overflowWrap = "anywhere";
      box.style.whiteSpace = "pre-wrap";
      Object.assign(box.style, filled(cell.style, data));
      if (cell.kind === "text") {
        const emoji = cell.emoji_dict ? dictionary(data[cell.emoji_dict]) : null;
        if (emoji) withEmoji(box, fill(cell.text, data), emoji, Number(cell.emoji_size) || 0, opts);
        else box.textContent = fill(cell.text, data);
      } else {
        // the first lists' own kind "picture": the {picture} value (a flow can give it)
        const src = sourceOf(cell.kind === "picture" ? {address: "{picture}"} : cell, data, opts);
        if (src) {
          const seen = document.createElement(cell.kind === "video" ? "video" : "img");
          seen.style.cssText = "display: block; width: 100%; height: 100%; object-fit: cover; border-radius: inherit";
          seen.draggable = false;
          if (cell.kind === "video") Object.assign(seen, {muted: true, autoplay: true, loop: true, playsInline: true});
          seen.onerror = () => seen.remove();  // no picture for them: the cell stays empty
          seen.src = src;
          box.append(seen);
        }
      }
      entry.append(box);
    }
    const layers = table.layers || {};
    for (const [side, z] of [["back", 0], ["front", 2]]) {
      const seen = layers[side] && layer(layers[side], z, data, opts);
      if (seen) entry.append(seen);  // absolute: not a grid item
    }
    return entry;
  }

  // the list in a piece's box: list(box, settings, opts) → {add(kind, data), drop(test), entries()}
  function list(box, settings, opts = {}) {
    const newest = settings.newest || "top";
    const across = newest === "left" || newest === "right";
    const inner = document.createElement("div");
    inner.style.cssText = "position: absolute; inset: 0; display: flex; overflow: hidden";
    inner.style.flexDirection = across ? "row" : "column";
    inner.style.alignItems = "flex-start";
    inner.style.justifyContent = newest === "bottom" || newest === "right" ? "flex-end" : "flex-start";
    inner.style.gap = (settings.gap ?? 8) + "px";
    box.append(inner);
    const looks = Object.fromEntries((settings.entries || []).filter(e => e.on !== false).map(e => [e.event, e.table]));
    const shown = [];  // {kind, data, at, element}, the newest last

    // the others slide to their new places instead of jumping there
    function moving(change) {
      const before = new Map(shown.map(one => [one.element, one.element.getBoundingClientRect()]));
      change();
      if (opts.still) return;
      const scale = (opts.scale ? opts.scale() : 1) || 1;  // the page is shrunk to fit: screen → canvas pixels
      for (const [element, was] of before) {
        if (!element.isConnected) continue;
        const now = element.getBoundingClientRect();
        const dx = (was.left - now.left) / scale, dy = (was.top - now.top) / scale;
        if (dx || dy) element.animate([{transform: `translate(${dx}px, ${dy}px)`}, {transform: "none"}], {duration: 300, easing: "ease-out"});
      }
    }

    function remove(one, gently) {
      const at = shown.indexOf(one);
      if (at < 0) return;
      shown.splice(at, 1);
      clearTimeout(one.timer);
      if (!gently || opts.still) return moving(() => one.element.remove());
      one.element.animate([{opacity: 1}, {opacity: 0}], {duration: 400, fill: "forwards"}).finished
        .then(() => moving(() => one.element.remove()));
    }

    function add(kind, data, at = Date.now(), still = false) {
      const table = looks[kind];
      if (!table) return null;
      const one = {kind, data, at, element: draw(table, data, opts)};
      const first = newest === "top" || newest === "left";
      moving(() => {
        shown.push(one);
        if (first) inner.prepend(one.element); else inner.append(one.element);
        while (shown.length > (settings.count || 10)) remove(shown[0], false);
      });
      const seconds = Number(settings.enter_seconds ?? 0.4) * 1000;
      if (!still && !opts.still && settings.enter && seconds) {
        const frames = {fade: [{opacity: 0}, {opacity: 1}],
                        slide: [{transform: FROM[newest], opacity: 0}, {transform: "none", opacity: 1}],
                        pop: [{transform: "scale(0.6)", opacity: 0}, {transform: "scale(1.05)", opacity: 1, offset: 0.7},
                              {transform: "none"}]}[settings.enter];
        if (frames) one.element.animate(frames, {duration: seconds, easing: "ease-out"});
      }
      const stays = Number(settings.stays || 0) * 1000;
      if (stays && !opts.still) {
        const left = stays - (Date.now() - at);
        if (left <= 0) { remove(one, false); return null; }
        one.timer = setTimeout(() => remove(one, true), left);
      }
      return one;
    }

    return {
      add,
      drop: test => shown.filter(one => test(one.kind, one.data)).forEach(one => remove(one, true)),
      entries: () => shown.map(({kind, data, at}) => ({kind, data, at})),
    };
  }

  window.TOOLBOX_ENTRY = {draw, list, fill, withEmoji, dictionary};  // the last two: alert texts too (element.js)
})();
