// The alerts overlay: listens to the toolbox and shows each alert it sends (the toolbox keeps the line, so
// this page only ever has one). Reconnects by itself when the toolbox restarts.
//   ?at=center|bottom  where alerts sit (an alert's own look wins)
//   ?preview=1         the toolbox's preview frame: shrunk to fit, not counted as a Browser source
//   ?edit=1            the look editor's frame: no socket; the editor posts the alert, it stays, and the text
//                      can be dragged over the picture (the new spot is posted back)
(() => {
  const stage = document.getElementById("stage");
  const query = new URLSearchParams(location.search);
  const EDIT = query.has("edit");
  const at = query.get("at");
  const DEFAULT_PLACE = at === "center" || at === "bottom" ? at : "top";
  if (EDIT || query.has("preview")) {
    // shown as if the canvas were 1920 wide, shrunk to the frame
    const fit = () => {
      const root = document.documentElement;
      root.style.zoom = innerWidth / 1920;
      root.style.setProperty("--vw", "19.2px");  // zoom doesn't scale vw / vh: say what 1 % of the canvas is
      root.style.setProperty("--vh", (19.2 * innerHeight / innerWidth) + "px");
    };
    addEventListener("resize", fit);
    fit();
  }
  const PICTURE_HEIGHT = 150;  // a picture piece without a size of its own (AlertPart.PICTURE_HEIGHT)
  const READY_MS = 1500;  // the longest an alert waits for its picture before it starts anyway
  let timer = null;
  let sound = null;
  let held = null;  // edit mode: the alert that stays on screen
  // the toolbox already keeps the alerts apart; only alerts sent again to a page that came back can arrive
  // while one is showing: they wait here for their turn
  const line = [];
  let playing = false;

  function play(alert) {
    if (playing) { line.push(alert); return; }
    playing = true;
    show(alert);
  }

  function played() {
    playing = false;
    if (line.length) play(line.shift());
  }

  function escapeHtml(text) {
    return text.replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  }

  // the text with its highlights (the viewer's name, the amount) in <b>, everything else escaped
  function textHtml(text, highlights) {
    const parts = highlights.filter(Boolean).map(h => h.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    if (!parts.length) return escapeHtml(text);
    return text.split(new RegExp(`(${parts.join("|")})`, "g"))
      .map((piece, i) => i % 2 ? `<b>${escapeHtml(piece)}</b>` : escapeHtml(piece)).join("");
  }

  function clear() {
    clearTimeout(timer);
    if (sound) { sound.pause(); sound = null; }
    stage.replaceChildren();
  }

  // an alert's look: only what it sets; the rest stays the page's own (alerts.css, OBS's Custom CSS)
  function applyLook(box, look) {
    const set = (name, value) => { if (value !== undefined && value !== "" && value !== false) box.style.setProperty(name, value); };
    set("--alert-size", look.text_size !== undefined && look.text_size + "px");
    set("--alert-media-height", look.picture_height !== undefined && `calc(var(--vh) * ${look.picture_height})`);
    set("--alert-color", look.text_color);
    set("--alert-accent", look.accent_color);
    set("--alert-font", look.font !== undefined && `"${look.font}", "Segoe UI", system-ui, sans-serif`);
    set("--alert-fade", look.animation_seconds !== undefined && look.animation_seconds * 1000 + "ms");
    box.classList.toggle("sized", look.picture_height !== undefined);
    stage.className = look.place || DEFAULT_PLACE;
  }

  function fadeMs(look) {
    return (look.animation_seconds !== undefined ? look.animation_seconds : 0.4) * 1000;
  }

  // edit mode: a piece of the words on the picture can be dragged; where its anchor ends up (the left end,
  // middle or right end of its top edge, by its alignment) goes to the editor with the piece's place in the
  // alert's list
  function makeDraggable(piece, media, index, align, widens) {
    piece.classList.add("draggable");
    const nudge = (dx, dy) => {  // the arrow keys: its spot in percent of the picture, one canvas pixel a step
      const keep = value => Math.round(Math.max(0, Math.min(value, 100)) * 100) / 100;
      const x = keep(parseFloat(piece.style.left) + dx / media.offsetWidth * 100);
      const y = keep(parseFloat(piece.style.top) + dy / media.offsetHeight * 100);
      piece.style.left = x + "%";
      piece.style.top = y + "%";
      tellLater({type: "toolbox_alert_text", index, x, y});
    };
    if (markedKey === index) mark(piece, index, nudge, false);
    piece.addEventListener("pointerdown", down => {
      down.preventDefault();
      down.stopPropagation();  // this piece moves, not the whole alert
      piece.setPointerCapture(down.pointerId);
      const now = piece.getBoundingClientRect();
      const anchorX = align === "left" ? now.left : align === "right" ? now.right : now.left + now.width / 2;
      const grabX = down.clientX - anchorX;
      const grabY = down.clientY - now.top;  // a piece hangs from its top edge
      const clamp = value => Math.round(Math.max(0, Math.min(value, 100)) * 10) / 10;
      const spot = event => {
        const box = media.getBoundingClientRect();
        return [clamp((event.clientX - grabX - box.left) / box.width * 100),
                clamp((event.clientY - grabY - box.top) / box.height * 100)];
      };
      const move = event => {
        const [x, y] = spot(event);
        piece.style.left = x + "%";
        piece.style.top = y + "%";
      };
      const up = event => {
        piece.removeEventListener("pointermove", move);
        piece.removeEventListener("pointerup", up);
        mark(piece, index, nudge);
        const [x, y] = spot(event);
        parent.postMessage({type: "toolbox_alert_text", index, x, y}, "*");
      };
      piece.addEventListener("pointermove", move);
      piece.addEventListener("pointerup", up);
    });
    if (widens) makeWidenable(piece, media, index, align, nudge);  // a picture piece keeps its own shape
  }

  // edit mode: a handle on a piece's side sets how wide it may be (percent of the picture) before its words wrap,
  // so it fits a box on a card (his round 76). It sits on the side away from where the piece is anchored; a piece
  // anchored at its middle grows on both sides.
  function makeWidenable(piece, media, index, align, nudge) {
    const handle = document.createElement("div");
    handle.className = "widen" + (align === "right" ? " left" : "");
    piece.appendChild(handle);
    handle.addEventListener("pointerdown", down => {
      down.preventDefault();
      down.stopPropagation();  // the piece gets wider, it doesn't move
      handle.setPointerCapture(down.pointerId);
      const start = piece.getBoundingClientRect().width;
      const grows = align === "center" ? 2 : align === "right" ? -1 : 1;
      const width = event => {
        const wide = (start + (event.clientX - down.clientX) * grows) / media.getBoundingClientRect().width * 100;
        return Math.round(Math.max(2, Math.min(wide, 100)) * 10) / 10;
      };
      const move = event => { piece.style.width = width(event) + "%"; };
      const up = event => {
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", up);
        move(event);
        mark(piece, index, nudge);
        parent.postMessage({type: "toolbox_alert_width", index, width: width(event)}, "*");
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", up);
    });
  }

  // edit mode: a handle on the picture's corner makes it bigger or smaller; its new height (percent of the
  // screen) goes to the editor. The words that are on the picture grow and shrink with it: their new sizes go
  // along (words below or above the picture keep theirs). An alert that hangs from the top grows downwards, one that stands on the bottom
  // grows upwards (its handle is on the top corner), the others grow around their middle.
  function makeResizable(box, media) {
    const fromBottom = stage.className === "bottom";
    const grows = stage.className === "top" || fromBottom ? 1 : 2;
    const handle = document.createElement("div");
    handle.className = "resize" + (fromBottom ? " upper" : "");
    media.appendChild(handle);
    handle.addEventListener("pointerdown", down => {
      down.preventDefault();
      down.stopPropagation();  // the picture changes size, the alert doesn't move
      handle.setPointerCapture(down.pointerId);
      const screen = stage.getBoundingClientRect().height;
      const start = media.getBoundingClientRect().height;
      // a words piece grows by its font size, a picture piece by its height
      const sizeOf = part => part.classList.contains("part-picture") ? "height" : "fontSize";
      const words = [...media.querySelectorAll(".part.over")].map(part => [part, parseFloat(getComputedStyle(part)[sizeOf(part)])]);
      const grown = () => media.getBoundingClientRect().height / start;  // the picture may be held by the screen's width
      const height = event => {
        const pulled = (event.clientY - down.clientY) * (fromBottom ? -1 : 1) * grows;
        return Math.round(Math.max(5, Math.min((start + pulled) / screen * 100, 100)) * 10) / 10;
      };
      const move = event => {
        box.style.setProperty("--alert-media-height", `calc(var(--vh) * ${height(event)})`);
        box.classList.add("sized");
        for (const [part, size] of words) part.style[sizeOf(part)] = size * grown() + "px";
      };
      const up = event => {
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", up);
        move(event);
        const sizes = words.map(([part, size]) => [Number(part.dataset.index), Math.round(size * grown() * 10) / 10]);
        parent.postMessage({type: "toolbox_alert_size", height: height(event), sizes}, "*");
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", up);
    });
  }

  // edit mode: a click marks the alert or a piece on its picture (his round 72); the arrow keys then move it one
  // pixel of the 1920 wide canvas, with Shift ten. What is marked stays marked when the editor sends the alert
  // again (markedKey: "alert" or the piece's place in the list).
  let marked = null;
  let markedKey = null;
  let nudged = null;
  // focus: false when the editor sent the alert again (a field there was typed in): the keys stay in that field
  // (his round 85: "it will remove my cursor after one letter")
  function mark(element, key, nudge, focus = true) {
    for (const old of document.querySelectorAll(".marked")) old.classList.remove("marked");
    element.classList.add("marked");
    marked = {element, nudge};
    markedKey = key;
    // the keys must come here: a drag's preventDefault keeps the focus on the editor page around this frame
    // (his round 74: "arrow keys does nothing")
    if (focus) window.focus();
  }
  if (EDIT) {
    addEventListener("keydown", event => {
      const step = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[event.key];
      if (!step || !marked || !marked.element.isConnected) return;
      event.preventDefault();
      const by = event.shiftKey ? 10 : 1;
      marked.nudge(step[0] * by, step[1] * by);
    });
  }
  // the spot goes to the editor once the keys rest (not one save per key press)
  const tellLater = message => {
    clearTimeout(nudged);
    nudged = setTimeout(() => parent.postMessage(message, "*"), 400);
  };

  // where the alert's middle is, in percent of the screen (also for an alert at top / middle / bottom)
  function middle(spot) {
    const screen = stage.getBoundingClientRect(), now = spot.getBoundingClientRect();
    return [(now.left + now.width / 2 - screen.left) / screen.width * 100,
            (now.top + now.height / 2 - screen.top) / screen.height * 100];
  }

  // the alert's middle may go this far: far enough for the whole alert to be outside the frame (his round 72);
  // "Set to center" in the editor brings it back
  const OUTSIDE = 100;
  const roundSpot = value => Math.round(Math.max(-OUTSIDE, Math.min(value, 100 + OUTSIDE)) * 10) / 10;

  // edit mode: the whole alert can be dragged anywhere on the screen, also out of it; where its middle ends up
  // goes to the editor. A click without moving marks it for the arrow keys.
  function makeMovable(box, spot) {
    const place = (x, y) => {
      spot.classList.add("free");
      spot.style.left = x + "%";
      spot.style.top = y + "%";
    };
    const nudge = (dx, dy) => {
      // from the spot it has, not a measured one: a pixel is 0.05 % of the width, and a middle measured a hair
      // below its spot rounded back to it, so Right moved once and then stuck (his round 76)
      const [x, y] = spot.classList.contains("free")
        ? [parseFloat(spot.style.left), parseFloat(spot.style.top)] : middle(spot);
      const fine = value => Math.round(Math.max(-OUTSIDE, Math.min(value, 100 + OUTSIDE)) * 100) / 100;
      const spotX = fine(x + dx / stage.offsetWidth * 100), spotY = fine(y + dy / stage.offsetHeight * 100);
      place(spotX, spotY);
      tellLater({type: "toolbox_alert_spot", x: spotX, y: spotY});
    };
    if (markedKey === "alert") mark(box, "alert", nudge, false);
    box.addEventListener("pointerdown", down => {
      down.preventDefault();
      box.setPointerCapture(down.pointerId);
      const screen = stage.getBoundingClientRect();
      const now = spot.getBoundingClientRect();
      const grabX = down.clientX - (now.left + now.width / 2);
      const grabY = down.clientY - (now.top + now.height / 2);
      const clamp = roundSpot;
      const where = event => [clamp((event.clientX - grabX - screen.left) / screen.width * 100),
                              clamp((event.clientY - grabY - screen.top) / screen.height * 100)];
      let moved = false;
      const move = event => {
        if (!moved && Math.hypot(event.clientX - down.clientX, event.clientY - down.clientY) < 4) return;
        moved = true;
        spot.classList.add("moving");
        place(...where(event));
      };
      const up = event => {
        box.removeEventListener("pointermove", move);
        box.removeEventListener("pointerup", up);
        spot.classList.remove("moving");
        mark(box, "alert", nudge);
        if (!moved) return;
        const [x, y] = where(event);
        parent.postMessage({type: "toolbox_alert_spot", x, y}, "*");
      };
      box.addEventListener("pointermove", move);
      box.addEventListener("pointerup", up);
    });
  }

  function show(alert, still) {
    clear();
    const look = alert.look || {};
    const box = document.createElement("div");
    box.className = "alert";
    applyLook(box, look);
    let media = null;
    if (alert.image) {
      media = document.createElement("div");
      media.className = "media";
      const picture = document.createElement(alert.video ? "video" : "img");
      picture.src = alert.image;
      picture.draggable = false;
      if (alert.video) {
        picture.autoplay = true;
        picture.loop = Boolean(still);
        picture.volume = alert.volume;
        picture.muted = Boolean(alert.sound) || Boolean(still);  // its own sound only when the alert has no other
      }
      const measured = () => {
        const [wide, high] = alert.video ? [picture.videoWidth, picture.videoHeight] : [picture.naturalWidth, picture.naturalHeight];
        if (!wide || !high) return;
        box.style.setProperty("--alert-aspect", wide / high);
        box.classList.add("measured");
      };
      picture.addEventListener(alert.video ? "loadedmetadata" : "load", measured);
      media.appendChild(picture);
      measured();  // a picture the page already has is ready at once
      box.appendChild(media);
    }
    // the words, piece by piece: a piece set "on the picture" sits there at its own spot, the others stack
    // below (or above) the picture
    const words = document.createElement("div");
    words.className = "words";
    for (const piece of alert.parts || []) {
      const part = document.createElement("div");
      part.className = "part part-" + piece.kind;
      if (piece.kind === "picture") {  // a picture or video of its own (his round 85), as high as its size
        const shown = document.createElement(piece.video ? "video" : "img");
        shown.src = piece.file;
        shown.draggable = false;
        if (piece.video) Object.assign(shown, {autoplay: true, loop: true, muted: true, playsInline: true});
        part.appendChild(shown);
        part.style.height = (piece.size || PICTURE_HEIGHT) + "px";
      } else if (piece.kind === "text") part.innerHTML = textHtml(piece.text, alert.highlights || []);
      else part.textContent = piece.text;
      if (piece.lines && piece.kind !== "picture") {  // at most that many lines, the rest cut with "…" (inside, so the editor's bar isn't cut)
        const clamp = document.createElement("div");
        clamp.className = "clamp";
        clamp.style.webkitLineClamp = piece.lines;
        clamp.append(...part.childNodes);
        part.appendChild(clamp);
      }
      if (piece.size && piece.kind !== "picture") part.style.fontSize = piece.size + "px";
      if (piece.color) {  // the piece's own colour also for the name and amount in its words (round 76)
        part.style.color = piece.color;
        part.style.setProperty("--alert-accent", piece.color);
      }
      if (piece.align) part.style.textAlign = piece.align;
      if (piece.on_picture && media) {
        const align = piece.align || "center";
        part.classList.add("over", "align-" + align);
        part.dataset.index = piece.index;
        part.style.left = (piece.x !== undefined ? piece.x : 50) + "%";
        part.style.top = (piece.y !== undefined ? piece.y : 50) + "%";
        if (piece.width && piece.kind !== "picture") part.style.width = piece.width + "%";  // its words wrap inside
        media.appendChild(part);
        if (EDIT) makeDraggable(part, media, piece.index, align, piece.kind !== "picture");
      } else {
        words.appendChild(part);
      }
    }
    box.classList.add(look.text_place === "above" ? "above" : "below");
    if (words.children.length) box.appendChild(words);
    const spot = document.createElement("div");
    spot.className = "spot";
    if (look.place === "free") {
      spot.classList.add("free");
      spot.style.left = (look.screen_x !== undefined ? look.screen_x : 50) + "%";
      spot.style.top = (look.screen_y !== undefined ? look.screen_y : 50) + "%";
    }
    spot.appendChild(box);
    stage.appendChild(spot);
    if (EDIT) makeMovable(box, spot);
    if (EDIT && media) makeResizable(box, media);
    if (still) return;  // the editor's standing picture: no animation, no sound, no end
    // the animation, sound and seconds start once the picture can be drawn (his round 74: a fade in that began
    // while a gif was still being read looked much shorter than the fade out); at most READY_MS later
    box.style.visibility = "hidden";
    let started = false;
    const start = () => {
      if (started || !box.isConnected) return;
      started = true;
      box.style.visibility = "";
      box.style.animationName = "alert-in-" + (look.animation_in || "fade");
      if (alert.sound) {
        sound = new Audio(alert.sound);
        sound.volume = alert.volume;
        sound.play().catch(() => {});  // a normal browser blocks sound until a click; OBS doesn't
      }
      const fade = fadeMs(look);
      timer = setTimeout(() => {
        box.style.animationName = "alert-out-" + (look.animation_out || "fade");
        timer = setTimeout(() => { clear(); if (held) show(held, true); played(); }, fade);
      }, Math.max(alert.seconds * 1000 - fade, 0));
    };
    const picture = media && media.querySelector("img, video");
    if (!picture) {
      start();
      return;
    }
    const ready = alert.video
      ? new Promise(done => {
          if (picture.readyState >= 2) done();
          picture.addEventListener("loadeddata", done, {once: true});
          picture.addEventListener("error", done, {once: true});
        })
      : picture.decode().catch(() => {});  // a picture that can't be read: the words still show
    ready.then(start);
    setTimeout(start, READY_MS);
  }

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
    const mine = socket = new WebSocket(scheme + location.host + "/overlay/alerts/ws" + address());
    heard = Date.now();
    mine.onopen = () => { heard = Date.now(); };
    mine.onmessage = event => {
      heard = Date.now();
      const message = JSON.parse(event.data);
      if (message.n !== undefined) mine.send(JSON.stringify({type: "got", n: message.n}));
      if (message.id !== undefined) { lastId = Math.max(lastId, message.id); keep(); }
      if (message.type === "hello") hello(message);
      else if (message.type === "alert") play(message.alert);
      else if (message.type === "clear") { line.length = 0; playing = false; clear(); }
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

  if (EDIT) {
    document.body.classList.add("edit");
    addEventListener("message", event => {
      const message = event.data || {};
      if (message.type === "hold") { held = message.alert; show(held, true); }
      else if (message.type === "play") show(message.alert);
    });
    parent.postMessage({type: "toolbox_alert_ready"}, "*");
  } else {
    connect();
  }
})();
