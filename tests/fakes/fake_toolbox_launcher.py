class FakeToolboxLauncher:
    """Stands in for ToolboxLauncher in the starter: remembers how it was made; run() ends right away."""

    def __init__(self, command: list[str], url: str, opener, update=None, launch=None) -> None:
        self.command, self.url, self.opener, self.update, self.launch = command, url, opener, update, launch
        self.stopped = False

    def run(self) -> int:
        return 0

    def stop(self) -> None:
        self.stopped = True
