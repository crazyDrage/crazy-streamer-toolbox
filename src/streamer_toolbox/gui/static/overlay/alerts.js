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
  let timer = null;
  let sound = null;
  let held = null;  // edit mode: the alert that stays on screen

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
  function makeDraggable(piece, media, index, align) {
    piece.classList.add("draggable");
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
        const [x, y] = spot(event);
        parent.postMessage({type: "toolbox_alert_text", index, x, y}, "*");
      };
      piece.addEventListener("pointermove", move);
      piece.addEventListener("pointerup", up);
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
      const words = [...media.querySelectorAll(".part.over")].map(part => [part, parseFloat(getComputedStyle(part).fontSize)]);
      const grown = () => media.getBoundingClientRect().height / start;  // the picture may be held by the screen's width
      const height = event => {
        const pulled = (event.clientY - down.clientY) * (fromBottom ? -1 : 1) * grows;
        return Math.round(Math.max(5, Math.min((start + pulled) / screen * 100, 100)) * 10) / 10;
      };
      const move = event => {
        box.style.setProperty("--alert-media-height", `calc(var(--vh) * ${height(event)})`);
        box.classList.add("sized");
        for (const [part, size] of words) part.style.fontSize = size * grown() + "px";
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

  // edit mode: the whole alert can be dragged anywhere on the screen; where its middle ends up goes to the editor
  function makeMovable(box, spot) {
    box.addEventListener("pointerdown", down => {
      down.preventDefault();
      box.setPointerCapture(down.pointerId);
      const screen = stage.getBoundingClientRect();
      const now = spot.getBoundingClientRect();
      const grabX = down.clientX - (now.left + now.width / 2);
      const grabY = down.clientY - (now.top + now.height / 2);
      const clamp = value => Math.round(Math.max(0, Math.min(value, 100)) * 10) / 10;
      const where = event => [clamp((event.clientX - grabX - screen.left) / screen.width * 100),
                              clamp((event.clientY - grabY - screen.top) / screen.height * 100)];
      let moved = false;
      const move = event => {
        if (!moved && Math.hypot(event.clientX - down.clientX, event.clientY - down.clientY) < 4) return;
        moved = true;
        const [x, y] = where(event);
        spot.classList.add("free", "moving");
        spot.style.left = x + "%";
        spot.style.top = y + "%";
      };
      const up = event => {
        box.removeEventListener("pointermove", move);
        box.removeEventListener("pointerup", up);
        spot.classList.remove("moving");
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
      if (piece.kind === "text") part.innerHTML = textHtml(piece.text, alert.highlights || []);
      else part.textContent = piece.text;
      if (piece.size) part.style.fontSize = piece.size + "px";
      if (piece.color) part.style.color = piece.color;
      if (piece.align) part.style.textAlign = piece.align;
      if (piece.on_picture && media) {
        const align = piece.align || "center";
        part.classList.add("over", "align-" + align);
        part.dataset.index = piece.index;
        part.style.left = (piece.x !== undefined ? piece.x : 50) + "%";
        part.style.top = (piece.y !== undefined ? piece.y : 50) + "%";
        if (piece.width) part.style.width = piece.width + "%";  // of the picture: its words wrap inside
        media.appendChild(part);
        if (EDIT) makeDraggable(part, media, piece.index, align);
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
    box.style.animationName = "alert-in-" + (look.animation_in || "fade");
    if (alert.sound) {
      sound = new Audio(alert.sound);
      sound.volume = alert.volume;
      sound.play().catch(() => {});  // a normal browser blocks sound until a click; OBS doesn't
    }
    const fade = fadeMs(look);
    timer = setTimeout(() => {
      box.style.animationName = "alert-out-" + (look.animation_out || "fade");
      timer = setTimeout(() => { clear(); if (held) show(held, true); }, fade);
    }, Math.max(alert.seconds * 1000 - fade, 0));
  }

  function connect() {
    const scheme = location.protocol === "https:" ? "wss://" : "ws://";
    // ?preview=1 (the toolbox's own preview) goes along, so it isn't counted as a Browser source in OBS
    const socket = new WebSocket(scheme + location.host + "/overlay/alerts/ws" + location.search);
    socket.onmessage = event => {
      const message = JSON.parse(event.data);
      if (message.type === "alert") show(message.alert);
      else if (message.type === "clear") clear();
    };
    socket.onclose = () => setTimeout(connect, 2000);
  }

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
