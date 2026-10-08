import io


class FakeChildProcess:
    """A toolbox process that ends with a given code."""

    def __init__(self, code: int) -> None:
        self.code = code
        self.stdin = io.BytesIO()

    def poll(self) -> None:
        return None

    def wait(self) -> int:
        return self.code
