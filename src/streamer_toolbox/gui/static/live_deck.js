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
  document.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key) || !document.querySelector(".tb-deck")) return;
    if (document.querySelector(".tb-deck-edit, .q-dialog") || event.target.closest("input, textarea")) return;
    emitEvent("tb_deck_turn", { by: event.key === "ArrowRight" ? 1 : -1 });
  });

  // Fit the screen: the deck as wide as it can be while all of it stays in the window
  let fitting = false;
  const fit = () => {
    fitting = false;
    document.querySelectorAll(".tb-deck[data-fit=screen]").forEach((board) => {
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
