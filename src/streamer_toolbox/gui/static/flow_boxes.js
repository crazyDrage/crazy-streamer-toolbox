// The box view of the flow editor (Drawflow). Python builds the graph and reads it back with tbFlow.export().
// One output may feed several boxes (they run at the same time); a box may have several outputs (If: then/else).
// Data dots (orange) come after the run dots: node.data.ports = run outputs, data_out / labels_out = data outputs,
// entries = extra run inputs after input_1 (a Loop's "stop": input_2, ...), data_in = the data inputs after those.
// A data wire only joins data dots, and a data input takes one wire. data_in "*" is the "by name" dot: a wire dropped there isn't kept; Python wires
// the box's fields named like the result's keys instead (tb_flow_by_name).
window.tbFlowInit = function (elementId, data, shortWires) {
  const el = document.getElementById(elementId);
  if (!el) return;
  window.tbFlowShort = shortWires !== false;
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
  editor.on("nodeSelected", (id) => emitEvent("tb_flow_node", Number(id)));
  editor.on("nodeUnselected", () => emitEvent("tb_flow_node", null));
  editor.on("nodeRemoved", (id) => emitEvent("tb_flow_removed", Number(id)));
  editor.on("connectionCreated", (c) => {
    const data = tbFlowIsData(editor, c.output_id, c.output_class);
    if (c.output_id == c.input_id || data !== !tbFlowIsRunIn(editor, c.input_id, c.input_class)) {
      editor.removeSingleConnection(c.output_id, c.input_id, c.output_class, c.input_class);
    } else if (data && tbFlowDataIn(editor, c.input_id, c.input_class) === "*") {
      editor.removeSingleConnection(c.output_id, c.input_id, c.output_class, c.input_class);
      const source = editor.getNodeFromId(c.output_id).data;
      const field = (source.data_out || [])[Number(c.output_class.split("_")[1]) - 1 - (source.ports || []).length];
      emitEvent("tb_flow_by_name", { target: Number(c.input_id), source: Number(c.output_id), field: field || "" });
    } else if (data) {  // a field takes one value: the new wire replaces the old one
      const input = editor.getNodeFromId(c.input_id).inputs[c.input_class];
      input.connections.filter((old) => old.node != c.output_id || old.input != c.output_class)
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
  canvas.addEventListener("keydown", (e) => {  // copy / paste / duplicate a box (Python does the work)
    const key = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && ["c", "v", "d"].includes(key)) {
      e.preventDefault();
      emitEvent("tb_flow_key", key);
    }
  });
  window.tbFlow = editor;
  tbFlowPaint(el, editor);
};

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

function tbFlowDataIn(editor, nodeId, input) {
  const node = editor.drawflow.drawflow.Home.data[nodeId];
  return ((node && node.data.data_in) || [])[Number(input.split("_")[1]) - 2 - tbFlowEntries(node).length];
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
// Data dots and wires get tb-data; dots get their name as a label (data-label) where a box has more than one.
function tbFlowPaint(el, editor) {
  const nodes = editor.drawflow.drawflow.Home.data;
  const number = (cls) => Number(cls.split("_")[1]);
  const portOf = (nodeId, output) => {
    const ports = (nodes[nodeId] && nodes[nodeId].data.ports) || [];
    return ports[number(output) - 1];
  };
  el.querySelectorAll(".drawflow-node").forEach((node) => {
    const data = (nodes[node.id.replace("node-", "")] || {}).data || {};
    const ports = data.ports || [], labelsOut = data.labels_out || [], dataIn = data.data_in || [];
    const entries = data.entries || [];
    node.querySelectorAll(".output").forEach((dot) => {
      const index = number([...dot.classList].find((c) => c.startsWith("output_"))) - 1;
      if (index < ports.length) {
        dot.classList.add("tb-port-" + ports[index]);
        if (ports.length > 1) dot.dataset.label = (data.port_labels || [])[index] || ports[index];
      } else {
        dot.classList.add("tb-data");
        dot.classList.toggle("tb-data-first", index === ports.length);
        dot.dataset.label = labelsOut[index - ports.length] || "";
      }
    });
    node.querySelectorAll(".input").forEach((dot) => {
      let index = number([...dot.classList].find((c) => c.startsWith("input_"))) - 2;
      if (index < entries.length) {  // run dots: "start" and the entries ("stop") when it has some
        if (entries.length) dot.dataset.label = index < 0 ? "start" : entries[index];
        dot.classList.toggle("tb-entry", index >= 0);
        return;
      }
      index -= entries.length;
      dot.classList.add("tb-data");
      dot.classList.toggle("tb-by-name", dataIn[index] === "*");
      dot.dataset.label = dataIn[index] === "*" ? "by name" : (dataIn[index] || "").replace(/_/g, " ");
    });
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

window.tbFlowUpdateNode = function (id, html, css) {
  const node = document.getElementById("node-" + id);
  if (!node) return;
  node.querySelector(".drawflow_content_node").innerHTML = html;
  node.classList.toggle("tb-off", css.includes("tb-off"));
  window.tbFlow.drawflow.drawflow.Home.data[id].html = html;
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
