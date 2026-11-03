// The toolbox's stand-in for what StreamElements' overlay page gives a custom widget: the events
// (onWidgetLoad, onEventReceived, onSessionUpdate) and SE_API. Loaded before the widget's own code; the page
// calls TOOLBOX_WIDGET.start() after it. What StreamElements' own services would answer (their bot's counters,
// their word filter) is given a harmless answer, so the widget's code keeps running.
(() => {
  const widget = window.TOOLBOX_WIDGET;
  const base = "/overlay/widget/" + encodeURIComponent(widget.name);
  const fire = (name, detail) => window.dispatchEvent(new CustomEvent(name, {detail}));

  // a page without an identity of its own (the sandbox, as on StreamElements) has no browser storage: reading
  // localStorage would stop the widget's code with an error. It gets one that lasts as long as the page.
  for (const name of ["localStorage", "sessionStorage"]) {
    try {
      window[name].length;
    } catch (refused) {
      const kept = new Map();
      Object.defineProperty(window, name, {configurable: true, value: {
        getItem: key => kept.has(String(key)) ? kept.get(String(key)) : null,
        setItem: (key, value) => { kept.set(String(key), String(value)); },
        removeItem: key => { kept.delete(String(key)); },
        clear: () => kept.clear(),
        key: index => [...kept.keys()][index] ?? null,
        get length() { return kept.size; },
      }});
    }
  }

  window.SE_API = {
    store: {
      // kept in the widget's folder on this PC (store.json)
      set(key, value) {
        return fetch(base + "/store/" + encodeURIComponent(key), {
          method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(value),
        }).then(() => fire("onEventReceived", {
          listener: "kvstore:update", event: {data: {key: "customWidget." + key, value}},
        }));
      },
      get(key) {
        return fetch(base + "/store/" + encodeURIComponent(key)).then(answer => answer.ok ? answer.json() : null);
      },
    },
    counters: {get: counter => Promise.resolve({counter, value: 0})},
    sanitize: ({message}) => Promise.resolve({result: {message}, skip: false}),
    cheerFilter: message => Promise.resolve(String(message).replace(/\b[A-Za-z]+\d+\b/g, "").replace(/\s+/g, " ").trim()),
    setField: () => {},
    getOverlayStatus: () => Promise.resolve({isEditorMode: false, muted: false}),
    resumeQueue: () => {},
    responses: {sendMessage: () => Promise.resolve()},
  };

  // The toolbox says "alive" every 15 s (api/overlay_line.py). A line that drops without a word leaves the
  // socket "open" forever, so after 40 s of nothing the page drops it itself and connects again.
  // ?ack=1: the page answers every message ({type: "got", n}), so the toolbox knows what didn't arrive.
  // The page keeps the toolbox's run and the last message id it got; coming back it says them
  // (?run=..&after=..) and the toolbox sends what it missed first (core/overlay/sent_messages.py).
  let socket = null;
  let heard = Date.now();
  // kept in the browser too, so a page that loads again (OBS refreshed the source) goes on where it was
  const KEPT = "toolbox-line:" + location.pathname + (new URLSearchParams(location.search).has("preview") ? ":preview" : "");
  let run = null;
  let lastId = 0;
  try {
    const kept = JSON.parse(localStorage.getItem(KEPT)) || {};
    run = kept.run || null;
    lastId = Number(kept.lastId) || 0;
  } catch (e) {}
  const keep = () => { try { localStorage.setItem(KEPT, JSON.stringify({run, lastId})); } catch (e) {} };
  const address = () => {
    const query = new URLSearchParams(location.search);
    query.set("ack", "1");
    if (run !== null) { query.set("run", run); query.set("after", lastId); }
    return "?" + query;
  };
  // the first message on every line: a new page starts at the newest id; after a restart (another run) the
  // toolbox sends everything it kept, so the count starts again
  const hello = told => {
    if (told.run !== run) lastId = run === null ? told.last : 0;
    run = told.run;
    keep();
  };

  function connect() {
    const scheme = location.protocol === "https:" ? "wss://" : "ws://";
    // ?preview=1 (the toolbox's own preview) goes along, so it isn't counted as a Browser source in OBS
    const mine = socket = new WebSocket(scheme + location.host + base + "/ws" + address());
    heard = Date.now();
    mine.onopen = () => { heard = Date.now(); };
    mine.onmessage = message => {
      heard = Date.now();
      const told = JSON.parse(message.data);
      if (told.n !== undefined) mine.send(JSON.stringify({type: "got", n: told.n}));
      if (told.id !== undefined) { lastId = Math.max(lastId, told.id); keep(); }
      if (told.type === "hello") hello(told);
      else if (told.type === "event") fire("onEventReceived", {listener: told.listener, event: told.event});
      else if (told.type === "session") fire("onSessionUpdate", {session: told.session});
      else if (told.type === "reload") location.reload();
    };
    mine.onclose = () => { if (socket === mine) { socket = null; setTimeout(connect, 2000); } };
  }

  setInterval(() => {
    if (socket && Date.now() - heard > 40000) {
      const dead = socket;
      socket = null;
      dead.onclose = dead.onmessage = null;
      try { dead.close(); } catch (e) {}
      connect();
    }
  }, 5000);

  // StreamElements fires onWidgetLoad once everything the widget loads is there. Helper libraries that widgets
  // pull in with <script defer> (se-tools, ...) listen for it, so it must not go out before the page's load.
  widget.start = () => {
    const begin = () => {
      fire("onWidgetLoad", widget.detail);
      connect();
    };
    if (document.readyState === "complete") begin();
    else window.addEventListener("load", begin, {once: true});
  };
})();
