from streamer_toolbox.core.interfaces.message_inbox import MessageInbox


class FakeMessageInbox(MessageInbox):
    """Keeps what came in: lets in only `key`, says each open and close."""

    def __init__(self, key: str = "right") -> None:
        self._key = key
        self.said: list[tuple[str, str, str]] = []  # ("opened" / "received" / "closed", type, text)

    def refusal(self, key: str) -> str:
        return "" if key == self._key else "wrong key"

    def opened(self, kind: str) -> None:
        self.said.append(("opened", kind, ""))

    def received(self, kind: str, text: str) -> None:
        self.said.append(("received", kind, text))

    def closed(self, kind: str) -> None:
        self.said.append(("closed", kind, ""))

    def known_types(self) -> list[str]:
        return sorted({kind for said, kind, _ in self.said if said in ("opened", "added")})

    def add_type(self, kind: str) -> None:
        self.said.append(("added", kind, ""))

    def live_types(self) -> list[str]:
        return []

    def forget(self, kind: str) -> None:
        self.said.append(("forgot", kind, ""))
