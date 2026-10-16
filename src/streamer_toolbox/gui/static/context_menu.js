// The toolbox's own right click menu, on every page (his wish of 2026-10-15: never the browser's own, it
// leads to errors and wrong behaviour). A place with its own menu (the flow canvas, a Quasar context menu)
// handles the click first; everywhere else this one comes: Cut / Copy / Paste in a text field, Copy for
// selected text, then Back, Reload and Open in new window (the link under the mouse, or this page).
(() => {
  if (window.tbMenu) return;

  // A small menu at a point: items [{label, icon, danger, run}] or "-" for a line. Gone on a click anywhere,
  // Esc, scroll or resize.
  window.tbMenu = function (x, y, items) {
    tbMenuClose();
    const menu = document.createElement("div");
    menu.className = "tb-menu";
    items.forEach((item) => {
      if (item === "-") {
        menu.appendChild(Object.assign(document.createElement("div"), { className: "tb-menu-line" }));
        return;
      }
      const row = document.createElement("button");
      row.className = "tb-menu-item" + (item.danger ? " tb-menu-danger" : "");
      row.innerHTML = `<i class="q-icon notranslate material-icons">${item.icon || ""}</i><span></span>`;
      row.querySelector("span").textContent = item.label;
      row.addEventListener("mousedown", (e) => e.preventDefault());  // a text field keeps its focus
      row.addEventListener("click", () => { tbMenuClose(); item.run(); });
      menu.appendChild(row);
    });
    document.body.appendChild(menu);
    const box = menu.getBoundingClientRect();  // stays on the screen
    menu.style.left = Math.max(0, Math.min(x, window.innerWidth - box.width - 4)) + "px";
    menu.style.top = Math.max(0, Math.min(y, window.innerHeight - box.height - 4)) + "px";
    setTimeout(() => {
      ["pointerdown", "wheel", "resize", "blur", "keydown"].forEach((name) =>
        window.addEventListener(name, tbMenuAway, true));
    });
  };

  function tbMenuAway(e) {
    if (e.type === "keydown" && e.key !== "Escape") return;
    if (e.type === "pointerdown" && e.target.closest && e.target.closest(".tb-menu")) return;
    tbMenuClose();
  }

  window.tbMenuClose = function () {
    document.querySelectorAll(".tb-menu").forEach((menu) => menu.remove());
    ["pointerdown", "wheel", "resize", "blur", "keydown"].forEach((name) =>
      window.removeEventListener(name, tbMenuAway, true));
  };

  // a new browser window (not a tab) the size of this one
  window.tbNewWindow = function (url) {
    window.open(url, "_blank", `popup,width=${window.outerWidth},height=${window.outerHeight}`);
  };

  function textField(target) {
    const field = target.closest && target.closest("input, textarea, [contenteditable=''], [contenteditable=true]");
    if (!field || field.readOnly || field.disabled) return null;
    const kind = (field.type || "text").toLowerCase();
    return field.tagName !== "INPUT" || ["text", "search", "url", "email", "number", "password", "tel"]
      .includes(kind) ? field : null;
  }

  function textItems(field) {
    const selected = String(window.getSelection() || "") !== ""
      || (field && field.selectionStart !== undefined && field.selectionStart !== field.selectionEnd);
    const items = [];
    if (field) {
      if (selected) items.push({ label: "Cut", icon: "content_cut", run: () => document.execCommand("cut") });
      if (selected) items.push({ label: "Copy", icon: "content_copy", run: () => document.execCommand("copy") });
      if (navigator.clipboard && navigator.clipboard.readText) {  // not over plain http from another device
        items.push({ label: "Paste", icon: "content_paste", run: async () => {
          try {
            field.focus();
            document.execCommand("insertText", false, await navigator.clipboard.readText());
          } catch (e) { /* the browser said no: Ctrl+V still works */ }
        } });
      }
      items.push({ label: "Select all", icon: "select_all", run: () => { field.focus(); field.select?.(); } });
    } else if (selected) {
      items.push({ label: "Copy", icon: "content_copy", run: () => document.execCommand("copy") });
    }
    return items;
  }

  document.addEventListener("contextmenu", (e) => {
    if (e.defaultPrevented) return;  // a place with its own menu took it
    e.preventDefault();
    const field = textField(e.target);
    const link = e.target.closest && e.target.closest("a[href]");
    const items = textItems(field);
    if (items.length) items.push("-");
    items.push({ label: "Back", icon: "arrow_back", run: () => history.back() });
    items.push({ label: "Reload", icon: "refresh", run: () => location.reload() });
    items.push({ label: link ? "Open link in new window" : "Open in new window", icon: "open_in_new",
      run: () => tbNewWindow(link ? link.href : location.href) });
    tbMenu(e.clientX, e.clientY, items);
  });
})();
