// The canvas of the widget editor (Overlay → Widget editor, WidgetDesigner): the pieces of a designed widget
// drawn the way element.js draws them in OBS, shrunk to fit. The pieces of the layer being edited can be
// clicked (picked), dragged (moved) and made bigger or smaller at their corner handle; the arrow keys move the
// picked one a pixel (Shift: ten), Delete removes it, Ctrl+D copies it. Near the middle or an edge of the canvas,
// or an edge or the middle of another piece, a piece snaps there (hold Alt not to). What changes goes to the
// page's Python side as an event; it draws the canvas again.
// Mouse, pen and finger alike (pointer events), so it works on the phone too.
(() => {
  const SNAP = 12;  // canvas pixels
  const FITS_UNDER = 230;  // screen pixels above and below the canvas: the tabs, the editor's rows, the hint
  const stages = {};

  function show(id, event, data) {
    const outer = document.getElementById(id);
    if (!outer) return;
    let stage = stages[id];
    if (!stage || stage.outer !== outer) {
      stage = stages[id] = {outer, event, data: null, scale: 1, nudge: null};
      outer.tabIndex = 0;
      outer.style.outline = "none";
      outer.addEventListener("keydown", key => keys(stage, key));
      outer.addEventListener("pointerdown", down => {
        if (down.target === outer || down.target === stage.canvas) tell(stage, {do: "select", id: ""});
      });
      new ResizeObserver(() => fit(stage)).observe(outer);
    }
    stage.event = event;
    stage.data = data;
    outer.style.aspectRatio = `${data.width} / ${data.height}`;
    // as big as the window lets it: the whole width, but no higher than the window under the editor's top rows
    // (his round 85: "it should use the whole window"); widget_designer.py _fitted says the same
    outer.style.width = `min(100%, calc((100vh - ${FITS_UNDER}px) * ${data.width} / ${data.height}))`;
    draw(stage);
  }

  const tell = (stage, what) => emitEvent(stage.event, what);

  function fit(stage) {
    if (!stage.canvas) return;
    stage.scale = stage.outer.clientWidth / stage.data.width;
    stage.canvas.style.transform = `scale(${stage.scale})`;
    stage.canvas.style.setProperty("--tb-px", 1 / stage.scale + "px");  // one screen pixel, in canvas pixels
  }

  function draw(stage) {
    const {outer, data} = stage;
    outer.replaceChildren();
    const canvas = stage.canvas = document.createElement("div");
    canvas.style.cssText = `position: absolute; left: 0; top: 0; width: ${data.width}px; height: ${data.height}px; ` +
      "transform-origin: top left; overflow: hidden";
    outer.append(canvas);
    for (const piece of data.pieces) canvas.append(make(stage, piece));
    for (const side of ["x", "y"]) {
      const guide = document.createElement("div");
      guide.className = "tb-design-guide tb-design-guide-" + side;  // a line one screen pixel wide
      guide.style.display = "none";
      canvas.append(guide);
      stage["guide_" + side] = guide;
    }
    fit(stage);
  }

  function words(box, piece) {
    for (const [text, filled] of piece.parts || []) {
      const part = document.createElement("span");
      if (filled) Object.assign(part.style, piece.highlight || {});
      part.textContent = text;
      box.append(part);
    }
  }

  function make(stage, piece) {
    const box = document.createElement("div");
    box.className = "tb-design-piece" + (piece.editable ? " editable" : " other") +
      (piece.id === stage.data.selected ? " picked" : "");
    box.dataset.id = piece.id;
    box.style.position = "absolute";
    if (piece.kind === "text") box.style.whiteSpace = "pre-wrap";
    Object.assign(box.style, piece.style || {});
    if (piece.kind === "image" || piece.kind === "video") {
      const seen = document.createElement(piece.kind === "image" ? "img" : "video");
      seen.draggable = false;
      if (piece.kind === "video") Object.assign(seen, {muted: true, autoplay: true, loop: true, playsInline: true});
      seen.style.cssText = "display: block; width: 100%;" + ((piece.style || {}).height ? " height: 100%;" : "");
      if (piece.src) {
        seen.src = piece.src;
      } else {
        box.classList.add("empty");
        box.textContent = piece.kind === "image" ? "Pick a picture" : "Pick a video";
      }
      if (piece.src) box.append(seen);
    } else if (piece.kind === "goal") {  // as element.js draws it: the part reached, the words in the middle
      box.style.overflow = "hidden";
      const fill = document.createElement("div");
      fill.style.cssText = `position: absolute; left: 0; top: 0; bottom: 0; width: ${piece.percent}%`;
      Object.assign(fill.style, piece.fill || {});
      const label = document.createElement("div");
      label.style.cssText = "position: absolute; inset: 0; display: flex; align-items: center; " +
        "justify-content: center; white-space: nowrap";
      label.textContent = piece.label;
      box.append(fill, label);
    } else if (piece.kind === "text") {
      if (box.style.whiteSpace === "nowrap") box.style.overflow = "hidden";  // a ticker: one line, cut off
      words(box, piece);
    }
    if (!piece.editable) return box;
    if (piece.id === stage.data.selected) {
      const handle = document.createElement("div");
      handle.className = "tb-design-handle";
      box.append(handle);
      handle.addEventListener("pointerdown", down => resize(stage, piece, box, down));
    }
    box.addEventListener("pointerdown", down => drag(stage, piece, box, down));
    return box;
  }

  // where a piece is, in canvas pixels
  const spot = box => ({left: parseFloat(box.style.left) || 0, top: parseFloat(box.style.top) || 0});

  function drag(stage, piece, box, down) {
    if (down.button > 0) return;
    down.preventDefault();
    down.stopPropagation();
    stage.outer.focus({preventScroll: true});
    if (piece.id !== stage.data.selected) {
      stage.data.selected = piece.id;
      for (const other of stage.canvas.querySelectorAll(".picked")) other.classList.remove("picked");
      box.classList.add("picked");
      tell(stage, {do: "select", id: piece.id});
    }
    box.setPointerCapture(down.pointerId);
    const start = spot(box);
    const lines = snapLines(stage, box);
    let moved = false;
    const move = event => {
      const dx = (event.clientX - down.clientX) / stage.scale, dy = (event.clientY - down.clientY) / stage.scale;
      if (!moved && Math.hypot(dx, dy) * stage.scale < 3) return;
      moved = true;
      let left = start.left + dx, top = start.top + dy;
      [left, top] = event.altKey ? (guides(stage, null, null), [left, top]) : snap(stage, box, lines, left, top);
      box.style.left = Math.round(left) + "px";
      box.style.top = Math.round(top) + "px";
    };
    const up = () => {
      box.removeEventListener("pointermove", move);
      box.removeEventListener("pointerup", up);
      box.removeEventListener("pointercancel", up);
      guides(stage, null, null);
      if (moved) tell(stage, {do: "move", id: piece.id, ...spot(box)});
    };
    box.addEventListener("pointermove", move);
    box.addEventListener("pointerup", up);
    box.addEventListener("pointercancel", up);
  }

  // the lines a piece snaps to: the canvas's edges and middle, and those of every other piece on it
  function snapLines(stage, box) {
    const {width, height} = stage.data;
    const lines = {x: [width / 2, 0, width], y: [height / 2, 0, height]};
    for (const other of stage.canvas.querySelectorAll(".tb-design-piece")) {
      if (other === box || !other.offsetWidth) continue;
      const left = other.offsetLeft, top = other.offsetTop, w = other.offsetWidth, h = other.offsetHeight;
      lines.x.push(left, left + w / 2, left + w);
      lines.y.push(top, top + h / 2, top + h);
    }
    return lines;
  }

  // a piece's left edge, middle or right edge onto the nearest line (the same up and down)
  function snap(stage, box, lines, left, top) {
    const w = box.offsetWidth, h = box.offsetHeight;
    const nearest = (at, size, along) => {
      let best = null;
      for (const line of along) {
        for (const part of [0, size / 2, size]) {
          const off = Math.abs(at + part - line);
          if (off < SNAP && (!best || off < best.off)) best = {off, at: line - part, line};
        }
      }
      return best;
    };
    const x = nearest(left, w, lines.x), y = nearest(top, h, lines.y);
    guides(stage, x ? x.line : null, y ? y.line : null);
    return [x ? x.at : left, y ? y.at : top];
  }

  function guides(stage, x, y) {
    stage.guide_x.style.display = x === null ? "none" : "block";
    stage.guide_y.style.display = y === null ? "none" : "block";
    if (x !== null) stage.guide_x.style.left = x + "px";
    if (y !== null) stage.guide_y.style.top = y + "px";
  }

  // the corner: a picture, video or ticker gets wider (a picture's height follows), a text bigger as a whole
  // (width and letters), a shape or a goal bar wider and higher on their own
  function resize(stage, piece, box, down) {
    down.preventDefault();
    down.stopPropagation();
    const handle = down.target;
    handle.setPointerCapture(down.pointerId);
    const width = box.offsetWidth, height = box.offsetHeight;
    const font = parseFloat(getComputedStyle(box).fontSize) || 16;
    const free = piece.resize === "free", scale = piece.resize === "scale";
    let factor = 1, high = height;
    const move = event => {
      const grown = width + (event.clientX - down.clientX) / stage.scale;
      factor = Math.max(grown, 8) / width;
      box.style.width = Math.round(width * factor) + "px";
      if (scale) box.style.fontSize = Math.max(Math.round(font * factor), 1) + "px";
      if (free) {
        high = Math.max(Math.round(height + (event.clientY - down.clientY) / stage.scale), 4);
        box.style.height = high + "px";
      }
    };
    const up = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", up);
      handle.removeEventListener("pointercancel", up);
      if (factor === 1 && high === height) return;
      tell(stage, {do: "resize", id: piece.id, width: Math.round(width * factor),
                   fontSize: scale ? Math.max(Math.round(font * factor), 1) : null, height: free ? high : null});
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", up);
    handle.addEventListener("pointercancel", up);
  }

  // the align buttons of the piece's settings: onto an edge or the middle of the canvas
  function align(id, how) {
    const stage = stages[id];
    const picked = stage && stage.canvas && stage.canvas.querySelector(".picked");
    if (!picked) return;
    const {width, height} = stage.data, w = picked.offsetWidth, h = picked.offsetHeight;
    const now = spot(picked);
    const left = {left: 0, center: (width - w) / 2, right: width - w}[how] ?? now.left;
    const top = {top: 0, middle: (height - h) / 2, bottom: height - h}[how] ?? now.top;
    picked.style.left = Math.round(left) + "px";
    picked.style.top = Math.round(top) + "px";
    tell(stage, {do: "move", id: stage.data.selected, ...spot(picked)});
  }

  function keys(stage, key) {
    const picked = stage.data.selected && stage.canvas.querySelector(".picked");
    const ctrl = key.ctrlKey || key.metaKey;
    if (ctrl && ["z", "y"].includes(key.key.toLowerCase())) {
      key.preventDefault();
      tell(stage, {do: key.key.toLowerCase() === "y" || key.shiftKey ? "redo" : "undo"});
      return;
    }
    if (!picked) return;
    if (ctrl && key.key.toLowerCase() === "d") {
      key.preventDefault();
      tell(stage, {do: "duplicate", id: stage.data.selected});
      return;
    }
    if (key.key === "Delete" || key.key === "Backspace") {
      key.preventDefault();
      tell(stage, {do: "delete", id: stage.data.selected});
      return;
    }
    const steps = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[key.key];
    if (!steps) return;
    key.preventDefault();
    const size = key.shiftKey ? 10 : 1;
    const now = spot(picked);
    picked.style.left = (now.left + steps[0] * size) + "px";
    picked.style.top = (now.top + steps[1] * size) + "px";
    clearTimeout(stage.nudge);  // once the keys rest, not one save per press
    const id = stage.data.selected;
    stage.nudge = setTimeout(() => tell(stage, {do: "move", id, ...spot(picked)}), 400);
  }

  window.TOOLBOX_DESIGNER = {show, align};
})();
