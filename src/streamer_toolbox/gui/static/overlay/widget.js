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

  function connect() {
    const scheme = location.protocol === "https:" ? "wss://" : "ws://";
    // ?preview=1 (the toolbox's own preview) goes along, so it isn't counted as a Browser source in OBS
    const socket = new WebSocket(scheme + location.host + base + "/ws" + location.search);
    socket.onmessage = message => {
      const told = JSON.parse(message.data);
      if (told.type === "event") fire("onEventReceived", {listener: told.listener, event: told.event});
      else if (told.type === "session") fire("onSessionUpdate", {session: told.session});
      else if (told.type === "reload") location.reload();
    };
    socket.onclose = () => setTimeout(connect, 2000);
  }

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
