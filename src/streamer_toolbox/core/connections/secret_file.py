from pathlib import Path


class SecretFile:
    """A token, key or password a connection needs, kept in its own file next to the settings
    (config/secrets/<id>_token.txt): its first line, nothing else. Never in toolbox.toml, never shown. He types it
    into the field on the connection's tab (SecretInput), which writes it here: he never opens the file
    (his rule, 2026-10-10: every token has an input field, no files to edit)."""

    def __init__(self, path: Path, what: str, where: str = "") -> None:
        self.path = path
        self._what = what    # "token", "API key", ...
        self._where = where  # where the streamer finds it, for the message when the file is empty

    def read(self) -> str:
        """The secret; ValueError with words the streamer can act on while the file is missing or empty."""
        secret = self.read_or_empty()
        if not secret:
            where = f" ({self._where})" if self._where else ""
            raise ValueError(f"No {self._what} yet: type the {self._what}{where} into its field on the "
                             "connection's tab (Connections)")
        return secret

    def read_or_empty(self) -> str:
        """The secret, or "" when there is none (for secrets a program only wants when it is set up so)."""
        text = self.path.read_text(encoding="utf-8").strip() if self.path.is_file() else ""
        return text.splitlines()[0].strip() if text else ""

    def write(self, secret: str) -> None:
        """Keeps a new secret (the tab's input field, SecretInput); "" takes it away."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(secret).strip().splitlines()[0].strip() + "\n" if str(secret).strip() else "",
                             encoding="utf-8")

    def hide(self, text: str) -> str:
        """`text` without the secret in it, for anything that gets shown or logged."""
        secret = self.read_or_empty()
        return text.replace(secret, f"<{self._what}>") if secret else text
