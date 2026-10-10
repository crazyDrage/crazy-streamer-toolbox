class FakeWriter:
    """The source of a fake `send` for a generated actions class: answers by (method, path) from a script and
    keeps every call (method, path, httpx kwargs), like tests/fakes/fake_helix.py."""

    def write(self, fake_class: str, actions_class: str) -> str:
        return f'''from typing import Any


class {fake_class}:
    """Stands in for {actions_class}'s send: answers by (method, path); every call is kept (made by box_gen)."""

    def __init__(self, answers: dict[tuple[str, str], Any] | None = None) -> None:
        self.answers = dict(answers or {{}})
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def __call__(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, kwargs))
        return self.answers.get((method, path))
'''
