class FakeEntryPoint:
    """Stands in for importlib.metadata.EntryPoint of a pip-installed plugin."""

    def __init__(self, name: str, plugin_class: type) -> None:
        self.name = name
        self._plugin_class = plugin_class

    def load(self) -> type:
        return self._plugin_class
