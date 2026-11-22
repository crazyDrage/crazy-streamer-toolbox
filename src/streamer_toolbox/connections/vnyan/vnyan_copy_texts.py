import base64
import secrets
import string
from collections.abc import Callable

PREFIX = "VNYANGRAPH:"
# VNyan's separators (decoded from his exports, 11-22: temp/feedback/vnyan/nyan_block.md)
NODES = "\x1c"  # between the group, the nodes and the wires
NEXT = "\x1d"  # between two nodes; between the flow wires and the value wires
PART = "\x1e"  # between the parts of a node; between two wires
FIELD = "\x1f"  # inside a part: x and y, a setting's name and value, a wire's two ends
SEPARATORS = NODES + NEXT + PART + FIELD
ID_LETTERS = string.ascii_letters + string.digits


class VNyanCopyTexts:
    """What the VNyan tab's Copy buttons give (his 11-22): node blocks to paste into a VNyan node graph, made
    like his own exports. A block is VNYANGRAPH: + base64 (no padding) of

        group <FS> node <GS> node ... <FS> flow wires <GS> value wires

    group = id, title, 0, 0, x<US>y, width<US>height; node = id, type, group id, 0, x<US>y, settings (name<US>
    value<US>...); a wire = "<to node><input>" <US> "<from node><output>", wires apart by <RS>.

    - data block: a WebSocket Command node with an EMPTY Command Text, its Data into a Dictionary Values node
      with one key per value the toolbox sends (Send data to VNyan).
    - text block: a WebSocket Command node with a Command Text, its Value into Number to Text (Send message).
    - send block: a WebSocket Message node with the toolbox's address (VNyan → toolbox)."""

    def __init__(self, new_id: Callable[[], str] | None = None) -> None:
        self._new_id = new_id or (lambda: "".join(secrets.choice(ID_LETTERS) for _ in range(2)))

    def data_block(self, keys: list[str]) -> str:
        keys = [_clean(key) for key in keys if _clean(key)]
        if not keys:
            raise ValueError('Which values? Type them like {"command": "throw", "item": "tomato"}')
        group, command, values = self._ids(3)
        options = ["opts", str(len(keys)), "name", ""]
        for number, key in enumerate(keys):
            options += [f"k{number}", key]
        return _encode(
            _group(group, "toolbox data block - Command Text needs to stay empty", -409, 19, 529,
                   417 + 26 * (len(keys) - 1)),
            [_node(command, "Websocket", group, -279, -121, ["command", ""]),
             _node(values, "DictionaryGetFlex", group, -122, -155, options)],
            [], [(values + "0", command + "2")])

    def text_block(self, command_text: str) -> str:
        command_text = _clean(command_text)
        if not command_text:
            raise ValueError("Which Command Text? The message the Send message to VNyan box sends")
        group, command, number = self._ids(3)
        return _encode(
            _group(group, "toolbox text block - it triggers if the text starts with the Command Text", -173, 14,
                   497, 247),
            [_node(command, "Websocket", group, -64, -104, ["command", command_text]),
             _node(number, "NumberToText", group, 189, -123, [])],
            [], [(number + "0", command + "0")])

    def send_block(self, address: str, message: str = "") -> str:
        group, send = self._ids(2)
        # the group and the node where his text block has them (11-22: the first try stuck out of its group)
        return _encode(
            _group(group, "toolbox send block", -173, 14, 497, 247),
            [_node(send, "WSMessage", group, -64, -104, ["address", _clean(address), "message", _clean(message)])],
            [], [])

    def _ids(self, count: int) -> list[str]:
        ids: list[str] = []
        while len(ids) < count:
            new = self._new_id()
            if new not in ids:
                ids.append(new)
        return ids


def decode(text: str) -> str:
    """A block's inner text (for tests and for looking at an export)."""
    code = text.strip().removeprefix(PREFIX)
    return base64.b64decode(code + "=" * (-len(code) % 4)).decode("utf-8")


def _encode(group: str, nodes: list[str], flow: list[tuple[str, str]], values: list[tuple[str, str]]) -> str:
    wires = PART.join(FIELD.join(pair) for pair in flow) + NEXT + PART.join(FIELD.join(pair) for pair in values)
    inner = group + NODES + NEXT.join(nodes) + NODES + wires
    return PREFIX + base64.b64encode(inner.encode("utf-8")).decode("ascii").rstrip("=")


def _group(group_id: str, title: str, x: int, y: int, width: int, height: int) -> str:
    return PART.join([group_id, title, "0", "0", f"{x}{FIELD}{y}", f"{width}{FIELD}{height}"])


def _node(node_id: str, kind: str, group_id: str, x: int, y: int, settings: list[str]) -> str:
    return PART.join([node_id, kind, group_id, "0", f"{x}{FIELD}{y}", FIELD.join(settings)])


def _clean(text: str) -> str:
    """Without VNyan's separators (they would break the block) and without spaces around it."""
    return "".join(c for c in str(text) if c not in SEPARATORS).strip()
