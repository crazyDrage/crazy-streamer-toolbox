// The box view of the flow editor (Drawflow). Python builds the graph and reads it back with tbFlow.export().
// One output may feed several boxes (they run at the same time); a box may have several outputs (If: then/else).
// Data dots (orange) come after the run dots: node.data.ports = run outputs, data_out / labels_out = data outputs,
// entries = extra run inputs after input_1 (a Loop's "stop": input_2, ...), data_in = the data inputs after those.
// A data wire only joins data dots, and a data input takes one wire.
// node.data.special: the boxes every flow has (Manual "start", a "trigger"'s Start box, "input"); see the menu.
window.tbFlowInit = function (elementId, data, shortWires, picked, groups) {
  const el = document.getElementById(elementId);
  if (!el) return;
  window.tbFlowShort = shortWires !== false;
  // drawn again (a box added or removed): the view stays where it was (his round 75: it moved to the left)
  const old = window.tbFlow && el.contains(window.tbFlow.container) ? window.tbFlow : null;
  const view = old ? { x: old.canvas_x, y: old.canvas_y, zoom: old.zoom } : null;
  // Drawflow pans only when the clicked element's *first* class is parent-drawflow. The outer div starts with
  // tb-drawflow (and NiceGUI owns its classes), so after a pan or zoom out the uncovered area didn't drag.
  // A plain inner div gets parent-drawflow as its only class.
  el.innerHTML = "";
  const canvas = document.createElement("div");
  canvas.style.cssText = "width: 100%; height: 100%;";
  el.appendChild(canvas);
  const editor = new Drawflow(canvas);
  editor.reroute = false;
  editor.start();
  editor.import(data);
  if (view) {
    editor.canvas_x = view.x;
    editor.canvas_y = view.y;
    editor.zoom = view.zoom;
    editor.zoom_last_value = view.zoom;
    editor.precanvas.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.zoom})`;
  }
  editor.on("nodeSelected", (id) => emitEvent("tb_flow_node", Number(id)));
  editor.on("nodeUnselected", () => emitEvent("tb_flow_node", null));
  editor.on("nodeRemoved", (id) => emitEvent("tb_flow_removed", Number(id)));
  editor.on("connectionCreated", (c) => {
    const data = tbFlowIsData(editor, c.output_id, c.output_class);
    if (c.output_id == c.input_id || data !== !tbFlowIsRunIn(editor, c.input_id, c.input_class)) {
      editor.removeSingleConnection(c.output_id, c.input_id, c.output_class, c.input_class);
    } else if (data) {  // a field takes one value: the new wire replaces the old one
      const target = editor.getNodeFromId(c.input_id);
      target.inputs[c.input_class].connections.filter((old) => old.node != c.output_id || old.input != c.output_class)
        .forEach((old) => editor.removeSingleConnection(old.node, c.input_id, old.input, c.input_class));
      emitEvent("tb_flow_wired", Number(c.input_id));
    }
    tbFlowPaint(el, editor);
  });
  editor.on("connectionRemoved", (c) => {
    if (c.input_class !== "input_1") emitEvent("tb_flow_wired", Number(c.input_id));
    tbFlowStubs(el, editor);
  });
  editor.on("nodeMoved", () => tbFlowStubs(el, editor));
  tbFlowDragOutside();
  tbFlowWireClicks(el, editor);
  tbFlowRightClick(el, editor);
  tbFlowMulti(el);
  canvas.addEventListener("keydown", (e) => {  // copy / paste / duplicate a box (Python does the work)
    const key = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && ["c", "v", "d"].includes(key)) {
      e.preventDefault();
      emitEvent("tb_flow_key", key);
    }
  });
  window.tbFlow = editor;
  tbFlowPaint(el, editor);
  tbFlowGroupHooks(el);
  window.tbFlowGroups = (groups || []).map((g) => ({ ...g }));
  tbFlowGroupsDraw(editor);
  tbFlowPick(picked || []);
};

// Groups (his round 83): coloured areas with a name, behind the boxes. A box belongs to a group when its middle
// is inside the area (dragged in = in it). Dragging the title moves the group and its boxes, the corner makes it
// bigger, the arrow folds it: then it is one small box, its boxes are moved out of sight onto it (a CSS
// transform: their saved spots stay) so their outside wires end at its edges; the wires among them are hidden.
// Python reads window.tbFlowGroups back with the graph ({id, label, color, x, y, w, h, folded}).
const TB_FOLDED_W = 240, TB_FOLDED_H = 70;
window.tbFlowGroups = [];

function tbFlowGroupMembers(editor, g) {
  const boxes = editor.drawflow.drawflow.Home.data;
  return Object.values(boxes).filter((box) => {
    const div = document.getElementById("node-" + box.id);
    if (!div) return false;
    const x = box.pos_x + div.offsetWidth / 2, y = box.pos_y + div.offsetHeight / 2;
    return x >= g.x && x <= g.x + g.w && y >= g.y && y <= g.y + g.h;
  }).map((box) => Number(box.id));
}

function tbFlowGroupsDraw(editor) {
  const pre = editor.precanvas;
  pre.querySelectorAll(".tb-group").forEach((div) => div.remove());
  pre.querySelectorAll(".drawflow-node.tb-in-folded").forEach((node) => {
    node.classList.remove("tb-in-folded");
    node.style.transform = "";
  });
  pre.querySelectorAll(".connection.tb-inner").forEach((wire) => wire.classList.remove("tb-inner"));
  const boxes = editor.drawflow.drawflow.Home.data;
  window.tbFlowGroups.forEach((g) => {
    const div = document.createElement("div");
    div.className = `tb-group tb-group-${g.color}` + (g.folded ? " tb-group-folded" : "");
    div.dataset.group = g.id;
    const title = document.createElement("div");
    title.className = "tb-group-title";
    title.title = "Drag to move the group with its boxes; click to change it";
    const label = document.createElement("span");
    label.className = "tb-group-label";
    label.textContent = g.label;
    const fold = document.createElement("button");
    fold.className = "tb-group-fold";
    fold.textContent = g.folded ? "▸" : "▾";
    fold.title = g.folded ? "Open" : "Fold into one box";
    title.append(label, fold);
    div.appendChild(title);
    const members = tbFlowGroupMembers(editor, g);
    if (g.folded) {
      const inside = new Set(members);
      let ins = 0, outs = 0;
      members.forEach((id) => {
        Object.values(boxes[id].outputs).forEach((o) => o.connections.forEach((c) => { if (!inside.has(Number(c.node))) outs++; }));
        Object.values(boxes[id].inputs).forEach((i) => i.connections.forEach((c) => { if (!inside.has(Number(c.node))) ins++; }));
      });
      const info = document.createElement("div");
      info.className = "tb-group-info";
      info.textContent = `${members.length} boxes · ${ins} wires in · ${outs} out`;
      div.appendChild(info);
      Object.assign(div.style, { left: g.x + "px", top: g.y + "px", width: TB_FOLDED_W + "px",
        height: TB_FOLDED_H + "px" });
      members.forEach((id) => {
        const node = document.getElementById("node-" + id);
        const box = boxes[id];
        node.classList.add("tb-in-folded");
        node.style.transformOrigin = "0 0";
        node.style.transform = `translate(${g.x - box.pos_x}px, ${g.y - box.pos_y}px) `
          + `scale(${TB_FOLDED_W / node.offsetWidth}, ${TB_FOLDED_H / node.offsetHeight})`;
      });
      pre.querySelectorAll(".connection").forEach((wire) => {
        const ends = [...wire.classList].filter((c) => c.startsWith("node_in_node-") || c.startsWith("node_out_node-"))
          .map((c) => Number(c.split("-").pop()));
        if (ends.length === 2 && ends.every((id) => inside.has(id))) wire.classList.add("tb-inner");
      });
    } else {
      const corner = document.createElement("div");
      corner.className = "tb-group-corner";
      corner.title = "Drag to make it bigger or smaller";
      div.appendChild(corner);
      Object.assign(div.style, { left: g.x + "px", top: g.y + "px", width: g.w + "px", height: g.h + "px" });
    }
    pre.insertBefore(div, pre.firstChild);  // first: the boxes and wires are drawn over it
  });
  Object.keys(boxes).forEach((id) => editor.updateConnectionNodes("node-" + id));
}

// Python changed a group (name, colour, folded): drawn again with it
window.tbFlowGroupSet = function (data) {
  const editor = window.tbFlow;
  if (!editor) return;
  const at = window.tbFlowGroups.findIndex((g) => g.id === data.id);
  if (at >= 0) window.tbFlowGroups[at] = { ...window.tbFlowGroups[at], ...data };
  else window.tbFlowGroups.push({ ...data });
  tbFlowGroupsDraw(editor);
  tbFlowStubs(editor.container.parentElement, editor);
};

function tbFlowGroupHooks(el) {
  if (el.tbGroupHooked) return;
  el.tbGroupHooked = true;
  let drag = null;
  el.addEventListener("mousedown", (e) => {
    const editor = window.tbFlow;
    const div = e.target.closest(".tb-group");
    if (e.button !== 0 || !editor || !div) return;
    e.stopPropagation();  // Drawflow mustn't move the view
    e.preventDefault();
    const g = window.tbFlowGroups.find((one) => one.id === div.dataset.group);
    if (!g) return;
    if (e.target.closest(".tb-group-fold")) {
      g.folded = !g.folded;
      tbFlowGroupsDraw(editor);
      tbFlowStubs(el, editor);
      emitEvent("tb_flow_group_folded", g.id);  // its panel, if open, shows Fold / Open the right way round
      return;
    }
    const boxes = editor.drawflow.drawflow.Home.data;
    const members = tbFlowGroupMembers(editor, g);
    drag = { g, size: !!e.target.closest(".tb-group-corner"), x: e.clientX, y: e.clientY, moved: false,
      start: { x: g.x, y: g.y, w: g.w, h: g.h },
      from: Object.fromEntries(members.map((id) => [id, [boxes[id].pos_x, boxes[id].pos_y]])) };
  }, true);
  document.addEventListener("mousemove", (e) => {
    const editor = window.tbFlow;
    if (!drag || !editor) return;
    const dx = (e.clientX - drag.x) / editor.zoom, dy = (e.clientY - drag.y) / editor.zoom;
    drag.moved = drag.moved || Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 3;
    const g = drag.g;
    if (drag.size) {
      g.w = Math.max(120, drag.start.w + dx);
      g.h = Math.max(80, drag.start.h + dy);
      const div = editor.precanvas.querySelector(`.tb-group[data-group="${g.id}"]`);
      if (div) Object.assign(div.style, { width: g.w + "px", height: g.h + "px" });
      return;
    }
    g.x = drag.start.x + dx;
    g.y = drag.start.y + dy;
    const boxes = editor.drawflow.drawflow.Home.data;
    Object.entries(drag.from).forEach(([id, [x, y]]) => {
      const box = boxes[id], node = document.getElementById("node-" + id);
      if (!box || !node) return;
      box.pos_x = x + dx;
      box.pos_y = y + dy;
      node.style.left = box.pos_x + "px";
      node.style.top = box.pos_y + "px";
    });
    if (g.folded) {
      tbFlowGroupsDraw(editor);  // its boxes sit on it again
    } else {
      const div = editor.precanvas.querySelector(`.tb-group[data-group="${g.id}"]`);
      if (div) Object.assign(div.style, { left: g.x + "px", top: g.y + "px" });
      Object.keys(drag.from).forEach((id) => editor.updateConnectionNodes("node-" + id));
    }
  });
  document.addEventListener("mouseup", () => {
    const editor = window.tbFlow;
    if (!drag || !editor) return;
    if (!drag.moved && !drag.size) emitEvent("tb_flow_group", drag.g.id);  // a click: its panel
    else tbFlowStubs(el, editor);
    drag = null;
  });
}

// Several boxes at once (his round 83). Ctrl / Shift + click a box adds it or takes it away; Shift + drag on the
// empty canvas draws a frame, the boxes it touches are picked. Dragging one picked box moves them all; Copy,
// Duplicate and Delete (menu, keys) act on all of them: Python gets the list as "tb_flow_picked" (box numbers).
// A click on another box or on the empty canvas lets them go. Hooked once per canvas area; acts on window.tbFlow.
window.tbFlowPicked = new Set();

function tbFlowPick(ids) {
  window.tbFlowPicked = new Set(ids);
  tbFlowShowPicked();
}

function tbFlowShowPicked() {
  const editor = window.tbFlow;
  if (!editor) return;
  editor.container.querySelectorAll(".drawflow-node").forEach((node) =>
    node.classList.toggle("tb-picked", window.tbFlowPicked.has(Number(node.id.replace("node-", "")))));
  emitEvent("tb_flow_picked", [...window.tbFlowPicked]);
}

function tbFlowMulti(el) {
  if (el.tbMultiHooked) return;
  el.tbMultiHooked = true;
  const picked = () => window.tbFlowPicked;
  const numberOf = (node) => Number(node.id.replace("node-", ""));
  let moving = null, frame = null, last = null;  // last: the box clicked last without a key, it joins the pick
  el.addEventListener("mousedown", (e) => {
    const editor = window.tbFlow;
    if (e.button !== 0 || !editor) return;
    const node = e.target.closest(".drawflow-node");
    const extra = e.ctrlKey || e.metaKey || e.shiftKey;
    if (node && extra && !e.target.closest(".input, .output")) {
      e.stopPropagation();  // Drawflow mustn't select or drag it
      e.preventDefault();
      const id = numberOf(node);
      if (!picked().size && last !== null && document.getElementById("node-" + last)) picked().add(last);
      if (picked().has(id)) picked().delete(id); else picked().add(id);
      tbFlowShowPicked();
      return;
    }
    if (node) {
      const id = numberOf(node);
      last = id;
      if (picked().has(id) && picked().size > 1) {
        const boxes = editor.drawflow.drawflow.Home.data;
        moving = { id, moved: false, from: Object.fromEntries([...picked()].filter((n) => boxes[n])
          .map((n) => [n, [boxes[n].pos_x, boxes[n].pos_y]])) };
      } else if (picked().size) {
        tbFlowPick([]);
      }
      return;
    }
    if (!e.target.matches(".drawflow, .parent-drawflow")) return;
    last = null;
    if (e.shiftKey) {  // a frame instead of moving the view
      e.stopPropagation();
      e.preventDefault();
      const area = el.getBoundingClientRect();
      frame = { x: e.clientX, y: e.clientY, div: document.createElement("div") };
      frame.div.className = "tb-pick-frame";
      Object.assign(frame.div.style, { left: e.clientX - area.left + "px", top: e.clientY - area.top + "px" });
      el.appendChild(frame.div);
      if (!e.ctrlKey && !e.metaKey) picked().clear();
    } else if (picked().size) {
      tbFlowPick([]);
    }
  }, true);
  // after Drawflow's own move (its listener sits on the canvas inside): the others follow the dragged one
  el.addEventListener("mousemove", (e) => {
    const editor = window.tbFlow;
    if (frame) {
      const area = el.getBoundingClientRect();
      Object.assign(frame.div.style, {
        left: Math.min(e.clientX, frame.x) - area.left + "px", top: Math.min(e.clientY, frame.y) - area.top + "px",
        width: Math.abs(e.clientX - frame.x) + "px", height: Math.abs(e.clientY - frame.y) + "px" });
      return;
    }
    if (!moving || !editor || !editor.drag) return;
    const boxes = editor.drawflow.drawflow.Home.data;
    const lead = boxes[moving.id], start = moving.from[moving.id];
    if (!lead || !start) return;
    const dx = lead.pos_x - start[0], dy = lead.pos_y - start[1];
    moving.moved = moving.moved || dx !== 0 || dy !== 0;
    Object.entries(moving.from).forEach(([id, [x, y]]) => {
      if (Number(id) === moving.id) return;
      const box = boxes[id], div = document.getElementById("node-" + id);
      if (!box || !div) return;
      box.pos_x = x + dx;
      box.pos_y = y + dy;
      div.style.left = box.pos_x + "px";
      div.style.top = box.pos_y + "px";
      editor.updateConnectionNodes("node-" + id);
    });
  });
  document.addEventListener("mouseup", () => {
    const editor = window.tbFlow;
    if (frame) {
      const r = frame.div.getBoundingClientRect();
      frame.div.remove();
      frame = null;
      if (editor) editor.container.querySelectorAll(".drawflow-node:not(.tb-in-folded)").forEach((node) => {
        const b = node.getBoundingClientRect();
        if (b.right >= r.left && b.left <= r.right && b.bottom >= r.top && b.top <= r.bottom) {
          picked().add(numberOf(node));
        }
      });
      tbFlowShowPicked();
      return;
    }
    if (moving && !moving.moved) {  // a plain click on one of them: only that one
      tbFlowPick([]);
    } else if (moving && editor) {
      tbFlowStubs(el, editor);
    }
    moving = null;
  });
  // Delete with several picked: all of them (Drawflow alone would delete only the one it has selected)
  el.addEventListener("keydown", (e) => {
    if (e.key !== "Delete" || picked().size < 2 || e.target.closest("input, textarea, [contenteditable]")) return;
    e.stopPropagation();
    e.preventDefault();
    emitEvent("tb_flow_menu", { do: "delete", node: [...picked()][0] });
  }, true);
}

// Drawflow listens for mouse moves and the release only on its own area. Let go of a drag (view, box, wire)
// outside it and the drag never ended: the view jumped back on the next drag or kept following the mouse.
// Moves and the release outside the area are passed on to it. Hooked once; it acts on the current editor.
function tbFlowDragOutside() {
  if (window.tbFlowDragHooked) return;
  window.tbFlowDragHooked = true;
  const outside = (e) => {
    const editor = window.tbFlow;
    return editor && editor.container.isConnected && !editor.container.contains(e.target)
      && (editor.editor_selected || editor.drag || editor.connection) ? editor : null;
  };
  document.addEventListener("mousemove", (e) => { const editor = outside(e); if (editor) editor.position(e); });
  document.addEventListener("mouseup", (e) => { const editor = outside(e); if (editor) editor.dragEnd(e); });
}

function tbFlowEntries(node) {
  return (node && node.data.entries) || [];
}

// input_1 and the entries (a Loop's stop) are run dots; the data dots come after them
function tbFlowIsRunIn(editor, nodeId, input) {
  const node = editor.drawflow.drawflow.Home.data[nodeId];
  return Number(input.split("_")[1]) <= 1 + tbFlowEntries(node).length;
}

function tbFlowIsData(editor, nodeId, output) {
  const node = editor.drawflow.drawflow.Home.data[nodeId];
  return Number(output.split("_")[1]) > ((node && node.data.ports) || []).length;
}

// Colours each output dot and each wire by its port (then / else, yes / no, each, ...): the CSS has tb-port-<name>.
// Data dots and wires get tb-data. A dot's name is in its row inside the box (Python writes the rows).
function tbFlowPaint(el, editor) {
  const nodes = editor.drawflow.drawflow.Home.data;
  const number = (cls) => Number(cls.split("_")[1]);
  const portOf = (nodeId, output) => {
    const ports = (nodes[nodeId] && nodes[nodeId].data.ports) || [];
    return ports[number(output) - 1];
  };
  el.querySelectorAll(".drawflow-node").forEach((node) => {
    const data = (nodes[node.id.replace("node-", "")] || {}).data || {};
    const ports = data.ports || [];
    const entries = data.entries || [];
    node.querySelectorAll(".output").forEach((dot) => {
      const index = number([...dot.classList].find((c) => c.startsWith("output_"))) - 1;
      if (index < ports.length) {
        dot.classList.add("tb-port-" + ports[index]);
      } else {
        dot.classList.add("tb-data");
      }
    });
    const order = data.order_in || [];  // a box with lines: each line's run dot above its value (Python's rows match)
    node.querySelectorAll(".input").forEach((dot) => {
      const input = number([...dot.classList].find((c) => c.startsWith("input_")));
      dot.style.order = order.length ? String(order.indexOf(input)) : "";
      let index = input - 2;
      if (index < entries.length) {  // run dots: the box's own and the entries ("stop") when it has some
        // a line's own run dot (Choose value, End) is a plain run dot, not a "stop"
        const lines = data.lines_in || [];
        const entry = index >= 0 && !lines.includes(entries[index]);
        dot.classList.toggle("tb-entry", entry);
        if (entry) dot.classList.add("tb-entry-" + entries[index]);  // its own colour: stop red, switch blue
        // the box's own run dot is "start" (green) when it has extra ones that aren't lines (a Loop)
        if (index < 0 && entries.some((e) => !lines.includes(e))) dot.classList.add("tb-entry-start");
        return;
      }
      index -= entries.length;
      dot.classList.add("tb-data");
    });
    if (order.length) editor.updateConnectionNodes(node.id);  // its wires were drawn to the dots' old places
  });
  el.querySelectorAll(".connection").forEach((wire) => {
    const from = [...wire.classList].find((c) => c.startsWith("node_out_node-"));
    const output = [...wire.classList].find((c) => c.startsWith("output_"));
    const nodeId = from && from.replace("node_out_node-", "");
    if (nodeId && output && tbFlowIsData(editor, nodeId, output)) wire.classList.add("tb-data");
    const port = nodeId && output && portOf(nodeId, output);
    if (port) wire.classList.add("tb-port-" + port);
  });
  tbFlowStubs(el, editor);
}

// Long orange wires as short ends (like LOGO!'s Cut/Join): the wire fades (it still works, hover shows it) and
// its ends get tags: "← 2 Split · width" at the field, "→ 4, 5" at the output. Only a view: nothing is saved.
const TB_LONG_WIRE = 400;

function tbFlowStubs(el, editor) {
  el.querySelectorAll(".tb-stub").forEach((stub) => stub.remove());
  el.querySelectorAll(".connection.tb-cut").forEach((wire) => wire.classList.remove("tb-cut"));
  if (!window.tbFlowShort) return;
  const nodes = editor.drawflow.drawflow.Home.data;
  const targets = {};  // "node|output_n" → the boxes it feeds
  el.querySelectorAll(".connection.tb-data").forEach((wire) => {
    const path = wire.querySelector(".main-path");
    if (!path || path.getTotalLength() < TB_LONG_WIRE) return;
    const classes = [...wire.classList];
    const pick = (prefix) => (classes.find((c) => c.startsWith(prefix)) || "").replace(prefix, "");
    const from = pick("node_out_node-"), to = pick("node_in_node-");
    const output = "output_" + pick("output_"), input = "input_" + pick("input_");
    if (!nodes[from] || !nodes[to]) return;
    wire.classList.add("tb-cut");
    const source = nodes[from].data, index = Number(output.split("_")[1]) - 1 - (source.ports || []).length;
    const field = ((source.labels_out || [])[index] || "").split(" · ")[0].replace(" (input)", "");
    tbFlowStub(el, to, "input", input, "← " + source.tag + (field && field !== "result" ? " · " + field : ""));
    (targets[from + "|" + output] = targets[from + "|" + output] || []).push(nodes[to].data.tag.split(" ")[0]);
  });
  Object.entries(targets).forEach(([key, tags]) => {
    const [nodeId, output] = key.split("|");
    tbFlowStub(el, nodeId, "output", output, "→ " + tags.join(", "));
  });
}

function tbFlowStub(el, nodeId, side, dotClass, text) {
  const dot = el.querySelector(`#node-${nodeId} .${side}.${dotClass}`);
  if (!dot) return;
  const stub = document.createElement("span");
  stub.className = "tb-stub tb-stub-" + side;
  stub.textContent = text;
  dot.appendChild(stub);
}

// Removing a wire: Drawflow only takes a click right on the line (and orange wires are dotted, so most clicks
// fall into a gap), then wants the Delete key or a right click. Here a click near any wire selects it (it turns
// red) and puts a × button there; the × removes it.
const TB_WIRE_REACH = 18;  // px around a wire that still count as a click on it

function tbFlowWireClicks(el, editor) {
  let down = null;
  el.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; }, true);
  el.addEventListener("click", (e) => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return;  // the view was dragged
    if (!e.target.matches(".drawflow, .parent-drawflow, svg.connection")) return;
    const path = tbFlowWireAt(el, e.clientX, e.clientY);
    if (!path) return;
    editor.connection_selected = path;
    path.classList.add("selected");
    tbFlowWireButton(el, editor, e.clientX, e.clientY);
  });
  editor.on("connectionSelected", () => { if (down) tbFlowWireButton(el, editor, down.x, down.y); });
  ["connectionUnselected", "nodeSelected", "translate", "zoom", "connectionRemoved"]
    .forEach((name) => editor.on(name, () => tbFlowWireButtonHide(el)));
}

function tbFlowWireAt(el, x, y) {
  const paths = [...el.querySelectorAll(".connection .main-path")];
  return paths.find((path) => {
    const style = path.style, keep = [style.strokeWidth, style.strokeDasharray];
    style.strokeWidth = TB_WIRE_REACH + "px";
    style.strokeDasharray = "none";
    const point = new DOMPoint(x, y).matrixTransform(path.getScreenCTM().inverse());
    const hit = path.isPointInStroke(point);
    [style.strokeWidth, style.strokeDasharray] = keep;
    return hit;
  }) || null;
}

function tbFlowWireButton(el, editor, x, y) {
  tbFlowWireButtonHide(el);
  const area = el.getBoundingClientRect();
  const button = document.createElement("button");
  button.className = "tb-wire-delete";
  button.title = "Remove this wire";
  button.textContent = "×";
  Object.assign(button.style, { left: x - area.left + "px", top: y - area.top + "px" });
  ["mousedown", "touchstart", "pointerdown"].forEach((name) =>
    button.addEventListener(name, (e) => e.stopPropagation()));  // Drawflow mustn't see it as a canvas click
  button.addEventListener("click", (e) => {
    e.stopPropagation();
    if (editor.connection_selected) editor.removeConnection();
    editor.connection_selected = null;
    tbFlowWireButtonHide(el);
  });
  el.appendChild(button);
}

function tbFlowWireButtonHide(el) {
  el.querySelectorAll(".tb-wire-delete").forEach((button) => button.remove());
}

// The right click menu on the canvas (his "go" of 2026-10-14), instead of the browser's and Drawflow's own
// (Drawflow puts a × on a right-clicked box or wire). A box, a wire or the empty canvas each get their own.
// Python does the work for boxes: "tb_flow_menu" {do, node} or {do, x, y} (a spot on the canvas).
function tbFlowRightClick(el, editor) {
  el.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    e.stopPropagation();  // capture: Drawflow's own handler on the canvas never sees it
    const node = e.target.closest(".drawflow-node");
    const ask = (what) => () => emitEvent("tb_flow_menu", what);
    if (node) {
      const id = Number(node.id.replace("node-", ""));
      const special = editor.drawflow.drawflow.Home.data[id].data.special;
      if (special) {  // Manual Start and Input can't be copied or deleted; a trigger's Start box can be deleted
        const test = { label: "Test run…", icon: "play_circle", run: ask({ do: "test", node: id }) };
        const change = { label: "Change", icon: "edit", run: ask({ do: "change", node: id }) };
        const remove = { label: "Delete", icon: "delete", danger: true, run: ask({ do: "delete", node: id }) };
        tbMenu(e.clientX, e.clientY, special === "input" ? [change] : special === "start" ? [test]
          : [change, test, remove]);
        return;
      }
      const many = window.tbFlowPicked.has(id) && window.tbFlowPicked.size > 1 ? window.tbFlowPicked.size : 0;
      if (many) {  // several picked (his round 83): the menu is for all of them
        tbMenu(e.clientX, e.clientY, [
          { label: `Copy ${many} boxes`, icon: "content_copy", run: ask({ do: "copy", node: id }) },
          { label: `Duplicate ${many} boxes`, icon: "library_add", run: ask({ do: "duplicate", node: id }) },
          { label: `Delete ${many} boxes`, icon: "delete", danger: true, run: ask({ do: "delete", node: id }) },
        ]);
        return;
      }
      tbMenu(e.clientX, e.clientY, [
        { label: "Change", icon: "edit", run: ask({ do: "change", node: id }) },
        { label: "Copy", icon: "content_copy", run: ask({ do: "copy", node: id }) },
        { label: "Duplicate", icon: "library_add", run: ask({ do: "duplicate", node: id }) },
        { label: "Test run from here", icon: "play_arrow", run: ask({ do: "test_from", node: id }) },
        { label: "Delete", icon: "delete", danger: true, run: ask({ do: "delete", node: id }) },
      ]);
      return;
    }
    const wire = tbFlowWireAt(el, e.clientX, e.clientY);
    if (wire) {
      tbMenu(e.clientX, e.clientY, [{ label: "Remove wire", icon: "link_off", danger: true, run: () => {
        editor.connection_selected = wire;
        editor.removeConnection();
        editor.connection_selected = null;
      } }]);
      return;
    }
    // where on the canvas (Drawflow's own numbers: the view may be moved and zoomed)
    const area = editor.precanvas.getBoundingClientRect();
    const spot = { x: (e.clientX - area.x) / editor.zoom, y: (e.clientY - area.y) / editor.zoom };
    tbMenu(e.clientX, e.clientY, [
      { label: "Add box here", icon: "add", run: ask({ do: "add", ...spot }) },
      { label: "Paste", icon: "content_paste", run: ask({ do: "paste", ...spot }) },
      { label: "Add group here", icon: "select_all", run: ask({ do: "group", ...spot }) },
    ]);
  }, true);
}

// Test run: a line under each box that ran (what it gave), red for the one that failed. Gone on the next redraw.
window.tbFlowMark = function (marks) {
  document.querySelectorAll(".tb-ran").forEach((line) => line.remove());
  document.querySelectorAll(".drawflow-node.tb-failed").forEach((node) => node.classList.remove("tb-failed"));
  Object.entries(marks).forEach(([id, mark]) => {
    const node = document.getElementById("node-" + id);
    const content = node && node.querySelector(".drawflow_content_node");
    if (!content) return;
    const line = document.createElement("div");
    line.className = "tb-ran" + (mark.failed ? " tb-ran-failed" : "") + (mark.debug ? " tb-ran-debug" : "");
    line.textContent = mark.text;
    content.appendChild(line);
    node.classList.toggle("tb-failed", mark.failed);
  });
};

window.tbFlowSetShort = function (on) {
  window.tbFlowShort = on;
  const el = window.tbFlow && window.tbFlow.container;
  if (el) tbFlowStubs(el, window.tbFlow);
};

// wired (optional): the box's fields that have a wire now (field → its ${box...}), see DrawflowGraph.read
window.tbFlowUpdateNode = function (id, html, css, wired) {
  const node = document.getElementById("node-" + id);
  if (!node) return;
  node.querySelector(".drawflow_content_node").innerHTML = html;
  node.classList.toggle("tb-off", css.includes("tb-off"));
  window.tbFlow.drawflow.drawflow.Home.data[id].html = html;
  if (wired !== undefined) window.tbFlow.drawflow.drawflow.Home.data[id].data.wired = wired;
};

// Full screen: the whole page goes full screen and the flow area covers it, so menus and dialogs (which Quasar
// puts at the end of the page) still show on top. Esc leaves full screen and the area shrinks back.
window.tbFlowFullscreen = function (areaId) {
  const area = document.getElementById(areaId);
  if (!area) return;
  if (area.classList.contains("tb-full")) {
    if (document.fullscreenElement) document.exitFullscreen();
    area.classList.remove("tb-full");
    return;
  }
  area.classList.add("tb-full");
  document.documentElement.requestFullscreen?.().catch(() => {});
  document.addEventListener("fullscreenchange", function left() {
    if (!document.fullscreenElement) {
      area.classList.remove("tb-full");
      document.removeEventListener("fullscreenchange", left);
    }
  });
};

// The box panel, docked left of the canvas: slides in (open = true), out (false) or toggles (no argument).
// Folded it's a thin strip with its buttons. Remembered per browser (may be unavailable: then it's just open).
window.tbFlowPanel = function (panelId, open) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  const folded = open === undefined ? !panel.classList.contains("tb-folded") : !open;
  panel.classList.toggle("tb-folded", folded);
  if (tbFlowPhone()) return;  // on a phone it covers the canvas: open only while editing, not remembered
  try { localStorage.setItem("tb-flow-panel-folded", folded ? "1" : ""); } catch (e) {}
};

window.tbFlowPanelRestore = function (panelId) {
  const panel = document.getElementById(panelId);
  let folded = tbFlowPhone();
  try { folded = folded || localStorage.getItem("tb-flow-panel-folded") === "1"; } catch (e) {}
  if (panel) panel.classList.toggle("tb-folded", folded);
};

// the box was closed: on a phone the panel slides out so the canvas shows again
window.tbFlowPanelClosed = function (panelId) {
  if (tbFlowPhone()) tbFlowPanel(panelId, false);
};

window.tbFlowPhone = () => window.matchMedia("(max-width: 700px)").matches;  // same width as flow_boxes.css
