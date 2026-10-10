import json
from collections.abc import Callable
from fnmatch import fnmatch
from typing import Any

import httpx

DEFAULT_URL = "http://127.0.0.1:8850"


class ToolboxCli:
    """The running toolbox from a terminal: list the actions, show one, run one. It only calls the HTTP API
    (GET /actions, POST /action/<name>), so it can do exactly what its caller may: without a token that is
    the local caller of this PC. Each method prints through `out` and gives the exit code (0 = fine)."""

    def __init__(self, url: str = DEFAULT_URL, token: str = "", out: Callable[[str], None] = print,
                 transport: httpx.BaseTransport | None = None, timeout: float = 60.0) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._url = url.rstrip("/")
        self._client = httpx.Client(base_url=self._url, headers=headers, transport=transport, timeout=timeout)
        self._out = out

    def list(self, pattern: str = "*") -> int:
        """Every action whose name fits the pattern ("obs.*"; a word without * is searched in the names)."""
        actions = self._actions()
        if actions is None:
            return 1
        if "*" not in pattern:
            pattern = f"*{pattern}*"
        found = [a for a in actions if fnmatch(a["name"], pattern)]
        width = max((len(a["name"]) for a in found), default=0)
        for action in found:
            self._out(f"{action['name']:<{width}}  {action.get('label') or ''}")
        self._out(f"{len(found)} of {len(actions)} actions")
        return 0

    def info(self, name: str) -> int:
        """One action: what it does and the parameters it takes."""
        actions = self._actions()
        if actions is None:
            return 1
        action = next((a for a in actions if a["name"] == name), None)
        if action is None:
            self._out(f"unknown action {name} (or this caller may not run it)")
            return 1
        self._out(f"{action['name']}: {action.get('label') or ''}")
        if action.get("description"):
            self._out(action["description"])
        for param in action.get("params") or []:
            self._out(f"  {param['name']}{'' if param.get('required') else '  (optional)'}")
        return 0

    def run(self, name: str, params: dict[str, Any]) -> int:
        """Runs the action and prints its result (text as it is, anything else as JSON)."""
        answer = self._ask("POST", f"/action/{name}", params)
        if answer is None:
            return 1
        result = answer.get("result")
        if result is not None:
            self._out(result if isinstance(result, str) else json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    def _actions(self) -> list[dict[str, Any]] | None:
        return self._ask("GET", "/actions")

    def _ask(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
        """The answer's JSON, or None after printing what went wrong."""
        try:
            answer = self._client.request(method, path, json=params or None)
        except httpx.HTTPError as e:
            self._out(f"no answer from the toolbox at {self._url}: is it running? ({e or type(e).__name__})")
            return None
        try:
            body = answer.json()
        except ValueError:
            body = {}
        if answer.is_success:
            return body
        reason = body.get("error") or body.get("detail") if isinstance(body, dict) else None
        self._out(f"failed ({answer.status_code}): {reason or answer.text}")
        return None
