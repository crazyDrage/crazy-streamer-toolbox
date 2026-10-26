import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.json_box import JsonBox
from streamer_toolbox.core.actions.json_box_field import JsonBoxField
from streamer_toolbox.core.actions.json_boxes import JsonBoxes
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.values.value_kinds import ValueKinds
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.web.web_target import WebTarget

KEYS = {"name", "label", "help", "group", "target", "input", "output"}
Secret = Callable[[str, str, str], SecretFile]  # (name, label, hint) → the plugin's key (PluginContext.secret)


class WebBoxes:
    """Boxes that talk to a web API, written as JSON only: no code. Every `*.json` file in a folder holds some:

        {"group": "Jokes",
         "boxes": [{"name": "joke", "label": "Random joke", "help": "Gets a joke",
                    "target": {"method": "GET", "url": "https://official-joke-api.appspot.com/jokes/{type}/random"},
                    "input": [{"name": "type", "kind": "choice", "choices": ["general", "programming"]}],
                    "output": {"setup": "0.setup", "punchline": "0.punchline"}}]}

    - target: where it goes (WebTarget): `url`, `method` (GET, POST, PUT, PATCH, DELETE; default GET), and maybe
      `headers`. {field} in the url or a header is that field's value; {secret.name} is a key the streamer
      types on the plugin's card under Plugins (never in the file, never in a box). The file may say how
      each key's field reads: "secrets": {"key": {"label": "API key", "hint": "On your account page"}}.
    - input: the box's fields, written like a JSON box's (name, kind, label, hint, optional, default, send_as,
      choices). The ones not used in the url or a header are sent: after the ? for GET and DELETE, else as a
      JSON body.
    - output: the box's data dots and where each one's value is in the answer ("items.0.name"); without it the
      box has one dot, "answer", with all of it.

    A web box is only for flows (anything that sends web requests is), and an answer of 400 and up fails it
    with the status and the start of the answer."""

    def __init__(self, folder: Path, kinds: ValueKinds | None = None,
                 transport: httpx.AsyncBaseTransport | None = None, secret: Secret | None = None) -> None:
        self._targets: dict[str, WebTarget] = {}
        self._transport = transport  # tests answer without a network
        self._secret = secret
        self._keys: dict[str, SecretFile] = {}
        self._key_texts = _key_texts(folder)
        self._boxes = JsonBoxes(folder, kinds, self._read)

    @property
    def boxes(self) -> list[JsonBox]:
        return self._boxes.boxes

    def add_to(self, actions: ActionRegistry, category: str) -> None:
        self._boxes.add_to(actions, category, self._send)

    def _read(self, data: dict[str, Any], group: str) -> JsonBox:
        unknown = set(data) - KEYS
        if unknown or not data.get("name") or not isinstance(data.get("target"), dict):
            raise ValueError(f"a web box needs \"name\" and \"target\" and may have label, help, group, input, "
                             f"output (got {', '.join(sorted(data))})")
        name = str(data["name"])
        try:
            target = WebTarget.from_dict(data["target"], data.get("output", {}))
        except ValueError as e:
            raise ValueError(f"box {name!r}: {e}") from None
        self._targets[name] = target
        fields = tuple(JsonBoxField.from_dict(f) for f in data.get("input", ()))
        if len({f.name for f in fields}) != len(fields):
            raise ValueError(f"box {name!r} has a field name twice")
        unknown_places = target.places() - {f.sent_name for f in fields}
        if unknown_places:
            raise ValueError(f"box {name!r}: {{{', '.join(sorted(unknown_places))}}} in the target is no input")
        for key in sorted(target.secrets() - set(self._keys)):
            if self._secret is None:
                raise ValueError(f"box {name!r}: {{secret.{key}}} needs a plugin to keep the key")
            label, hint = self._key_texts.get(key, (key.replace("_", " ").capitalize(), ""))
            self._keys[key] = self._secret(key, label, hint)
        return JsonBox(name, name, str(data.get("label", "")), str(data.get("help", "")), fields, {},
                       str(data.get("group", group)), True, tuple(target.output))

    async def _send(self, name: str, data: dict[str, Any]) -> dict[str, Any]:
        target = self._targets[name]
        keys = {key: self._keys[key].read() for key in sorted(target.secrets())}  # raises: where to type one
        rest = {k: v for k, v in data.items() if k not in target.places()}
        url = target.address(data, keys)
        query = rest if target.method in ("GET", "DELETE") else None
        body = json.dumps(rest, ensure_ascii=False).encode() if rest and query is None else None
        headers = target.sent_headers(data, keys)
        if body is not None and not any(k.casefold() == "content-type" for k in headers):
            headers["Content-Type"] = "application/json"
        shown = self._hidden(target, url)
        async with web_client(self._transport, timeout=10.0) as client:
            try:
                answer = await client.request(target.method, url, params=query or None, content=body,
                                              headers=headers)
            except httpx.TimeoutException:
                raise TimeoutError(f"{shown} didn't answer within 10 s") from None
            except httpx.HTTPError as e:
                raise ConnectionError(self._hidden(target, f"can't reach {shown}: {e}")) from None
        if answer.status_code >= 400:
            raise RuntimeError(self._hidden(target, f"{target.method} {shown} answered {answer.status_code}: "
                                                    f"{answer.text[:200]}"))
        return target.outputs_from(understand(answer.text))

    def _hidden(self, target: WebTarget, text: str) -> str:
        """The text without the target's keys in it (also as they look in an address)."""
        for key in target.secrets():
            secret = self._keys[key].read_or_empty()
            if secret:
                text = text.replace(secret, f"<{key}>").replace(quote(secret, safe=""), f"<{key}>")
        return text


def _key_texts(folder: Path) -> dict[str, tuple[str, str]]:
    """The label and hint of each key, from the files' "secrets" (a wrong file is reported by JsonBoxes)."""
    texts: dict[str, tuple[str, str]] = {}
    for file in sorted(folder.glob("*.json")):
        try:
            for key, text in dict(json.loads(file.read_text(encoding="utf-8")).get("secrets", {})).items():
                texts[str(key)] = (str(text.get("label", key)), str(text.get("hint", "")))
        except (ValueError, AttributeError, TypeError):
            continue
    return texts
