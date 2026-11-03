import textwrap

from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec


class ActionsClassWriter:
    """The source of a service's group class: it is given `send` and its add_to(actions) adds the service's Box
    classes (BoxClassWriter), all under the service's name."""

    def write(self, spec: ServiceSpec, boxes: dict[str, str], base_module: str) -> str:
        """boxes: box class → the module it is in, in the spec's order."""
        lines = sorted([f"from {module} import {name}" for name, module in boxes.items()]
                       + [f"from {base_module} import Send",
                          "from streamer_toolbox.core.actions.action_registry import ActionRegistry"])
        lines += ["", "", f"class {spec.class_name}:",
                  f'    """{spec.description or spec.service + " boxes"} (made by box_gen; TODO: pickers, hints).', "",
                  '    One Box class per box, in boxes/."""', "",
                  "    def __init__(self, send: Send) -> None:", "        self._send = send", "",
                  "    def add_to(self, actions: ActionRegistry) -> None:"]
        lead = "        for box in ("
        items = ", ".join(f"{name}(self._send)" for name in boxes)
        wrapped = textwrap.wrap(items, 116 - len(lead), break_long_words=False, break_on_hyphens=False)
        lines.append(lead + ("\n" + " " * len(lead)).join(wrapped) + (",):" if len(boxes) == 1 else "):"))
        lines.append(f'            actions.add_box(box, "{spec.service}")')
        return "\n".join(lines) + "\n"
