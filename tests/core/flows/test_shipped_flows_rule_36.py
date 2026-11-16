import tomllib
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src" / "streamer_toolbox"


def _values(value):
    if isinstance(value, dict):
        for inner in value.values():
            yield from _values(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _values(inner)
    else:
        yield value


class TestShippedFlowsRule36(unittest.TestCase):
    """Rule 36 (his round 90: "the user can't deal with that"): no ${...} typed into a box's field in a flow the
    toolbox ships. A field is a plain value or one whole wire; words with values are a Build text box."""

    def test_every_field_is_a_plain_value_or_one_whole_wire(self) -> None:
        files = sorted(SRC.rglob("*.flows.toml"))
        self.assertTrue(files)
        for path in files:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            for flow in data.get("flows", []):
                for node in flow.get("nodes", []):
                    for value in _values(node.get("params", {})):
                        text = str(value)
                        with self.subTest(file=path.name, flow=flow.get("name"), box=node.get("id")):
                            self.assertTrue("${" not in text or (text.startswith("${") and text.endswith("}")
                                                                 and text.count("${") == 1), text)


if __name__ == "__main__":
    unittest.main()
