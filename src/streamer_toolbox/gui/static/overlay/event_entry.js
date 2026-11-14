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
  // PC through the widget's own route (opts.local; the toolbox gives only what its addresses make)
  function source(address, opts) {
    if (/^(https?:|data:|blob:)/i.test(address)) return address;
    return opts.local ? opts.local + encodeURIComponent(address) : "";
  }

  // a style's value can be one of the event's too ({color}: their name colour)
  function filled(style, data) {
    return Object.fromEntries(Object.entries(style || {}).map(([key, value]) => [key, typeof value === "string" ? fill(value, data) : value]));
  }

  // one event as its table: a CSS grid, each cell where its column and row say; opts.values(data): values it
  // gets besides
  function draw(table, given, opts = {}) {
    const data = {...given, ...(opts.values ? opts.values(given) : {})};
    const entry = document.createElement("div");
    entry.style.cssText = "display: grid; flex-shrink: 0; box-sizing: border-box; align-items: center";
    entry.style.gridTemplateColumns = `repeat(${table.columns || 1}, auto)`;
    entry.style.columnGap = entry.style.rowGap = "6px";
    Object.assign(entry.style, filled(table.style, data));
    for (const cell of table.cells || []) {
      const box = document.createElement("div");
      box.style.gridColumn = `${cell.col + 1} / span ${cell.cols}`;
      box.style.gridRow = `${cell.row + 1} / span ${cell.rows}`;
      box.style.minWidth = "0";
      box.style.overflowWrap = "anywhere";
      box.style.whiteSpace = "pre-wrap";
      Object.assign(box.style, filled(cell.style, data));
      if (cell.kind === "text") {
        box.textContent = fill(cell.text, data);
      } else {
        // the first lists' own kind "picture": the {picture} value (a flow can give it)
        const address = fill(cell.kind === "picture" ? "{picture}" : cell.address, data).trim();
        const src = address ? source(address, opts) : cell.file ? (opts.media || (f => f))(cell.file) : "";
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

  window.TOOLBOX_ENTRY = {draw, list, fill};
})();
