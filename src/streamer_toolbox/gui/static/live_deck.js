// The Live deck while editing: drag a button to move it, drag its corner to change its size. Both snap to
// the page's cells. Python hears "tb_deck_spot" {index, x, y, w, h} when the button is let go somewhere new.
// Not editing: swipes and arrow keys turn the page, full screen, and Fit the screen (round 63).
(() => {
  if (window.tbDeckReady) return;
  window.tbDeckReady = true;
  let drag = null;
  let swallowClick = false;
  const clamp = (value, low, high) => Math.min(Math.max(value, low), high);

  document.addEventListener("pointerdown", (event) => {
    const tile = event.target.closest(".tb-deck-edit .tb-deck-button");
    if (!tile || event.button !== 0) return;
    const board = tile.closest(".tb-deck");
    const box = board.getBoundingClientRect();
    const columns = Number(board.dataset.columns);
    const rows = Number(board.dataset.rows);
    const start = { x: Number(tile.dataset.x), y: Number(tile.dataset.y), w: Number(tile.dataset.w),
      h: Number(tile.dataset.h) };
    drag = { tile, columns, rows, start, now: { ...start }, size: Boolean(event.target.closest(".tb-deck-grip")),
      fromX: event.clientX, fromY: event.clientY, cellW: box.width / columns, cellH: box.height / rows };
    tile.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  document.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const dx = Math.round((event.clientX - drag.fromX) / drag.cellW);
    const dy = Math.round((event.clientY - drag.fromY) / drag.cellH);
    const { start, now, columns, rows, tile } = drag;
    if (drag.size) {
      now.w = clamp(start.w + dx, 1, columns - start.x);
      now.h = clamp(start.h + dy, 1, rows - start.y);
    } else {
      now.x = clamp(start.x + dx, 0, columns - start.w);
      now.y = clamp(start.y + dy, 0, rows - start.h);
    }
    tile.style.left = `${(now.x / columns) * 100}%`;
    tile.style.top = `${(now.y / rows) * 100}%`;
    tile.style.width = `${(now.w / columns) * 100}%`;
    tile.style.height = `${(now.h / rows) * 100}%`;
    tile.classList.add("tb-deck-dragged");
  });

  const end = () => {
    if (!drag) return;
    const { tile, start, now } = drag;
    drag = null;
    tile.classList.remove("tb-deck-dragged");
    if (now.x === start.x && now.y === start.y && now.w === start.w && now.h === start.h) return;
    swallowClick = true;  // letting go is not a click on the button
    setTimeout(() => { swallowClick = false; }, 300);
    emitEvent("tb_deck_spot", { index: Number(tile.dataset.index), ...now });
  };
  document.addEventListener("pointerup", end);
  document.addEventListener("pointercancel", end);

  // not editing: a swipe sideways or an arrow key goes to the next / last page ("tb_deck_turn" {by})
  let swipe = null;
  document.addEventListener("pointerdown", (event) => {
    const board = event.target.closest(".tb-deck");
    swipe = board && !board.classList.contains("tb-deck-edit") ? { x: event.clientX, y: event.clientY } : null;
  });
  document.addEventListener("pointerup", (event) => {
    if (!swipe) return;
    const dx = event.clientX - swipe.x;
    const dy = event.clientY - swipe.y;
    swipe = null;
    if (Math.abs(dx) < 80 || Math.abs(dy) > Math.abs(dx) / 2) return;
    swallowClick = true;  // a swipe that ends on a button doesn't press it
    setTimeout(() => { swallowClick = false; }, 300);
    emitEvent("tb_deck_turn", { by: dx < 0 ? 1 : -1 });
  });
  // Page Up / Down turn the page also while editing (his 11-18 pick 2); the arrows only when not editing
  document.addEventListener("keydown", (event) => {
    const page = { PageDown: 1, PageUp: -1 }[event.key];
    const arrow = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!(page || arrow) || !document.querySelector(".tb-deck")) return;
    if (document.querySelector(".q-dialog") || event.target.closest("input, textarea")) return;
    if (arrow && document.querySelector(".tb-deck-edit")) return;
    event.preventDefault();
    emitEvent("tb_deck_turn", { by: page || arrow });
  });

  // editing: Ctrl+C / X / V / Z, Delete, Escape on what is under the mouse ("tb_deck_key" {key, index, x, y};
  // index: the button under it or -1, x / y: the cell under it or -1)
  let mouseX = -1;
  let mouseY = -1;
  document.addEventListener("pointermove", (event) => { mouseX = event.clientX; mouseY = event.clientY; });
  document.addEventListener("keydown", (event) => {
    const board = document.querySelector(".tb-deck-edit");
    if (!board || document.querySelector(".q-dialog") || event.target.closest("input, textarea")) return;
    const letter = event.key.toLowerCase();
    const key = (event.ctrlKey || event.metaKey) && ["c", "x", "v", "z"].includes(letter) ? letter
      : ["Delete", "Backspace", "Escape"].includes(event.key) ? event.key : "";
    if (!key) return;
    event.preventDefault();
    const under = document.elementFromPoint(mouseX, mouseY);
    const tile = under && under.closest(".tb-deck-edit .tb-deck-button");
    const box = board.getBoundingClientRect();
    const inside = mouseX >= box.left && mouseX < box.right && mouseY >= box.top && mouseY < box.bottom;
    emitEvent("tb_deck_key", { key, index: tile ? Number(tile.dataset.index) : -1,
      x: inside ? Math.floor(((mouseX - box.left) / box.width) * Number(board.dataset.columns)) : -1,
      y: inside ? Math.floor(((mouseY - box.top) / box.height) * Number(board.dataset.rows)) : -1 });
  });

  // Fit the screen: the deck as wide as it can be while all of it stays in the window (full screen: the css)
  let fitting = false;
  const fit = () => {
    fitting = false;
    const full = Boolean(document.fullscreenElement);
    document.querySelectorAll(".tb-deck").forEach((board) => {
      if (full || board.dataset.fit !== "screen") {
        board.style.maxWidth = "";
        return;
      }
      const left = window.innerHeight - board.getBoundingClientRect().top - 8;
      const columns = Number(board.dataset.columns);
      const rows = Number(board.dataset.rows);
      board.style.maxWidth = `${Math.max(columns * 16, (left * columns) / rows)}px`;
    });
  };
  const fitSoon = () => { if (!fitting) { fitting = true; requestAnimationFrame(fit); } };
  window.addEventListener("resize", fitSoon);
  document.addEventListener("fullscreenchange", fitSoon);
  new MutationObserver(fitSoon).observe(document.documentElement, { childList: true, subtree: true });

  document.addEventListener("click", (event) => {
    if (!swallowClick) return;
    swallowClick = false;
    event.stopPropagation();
    event.preventDefault();
  }, true);
})();
