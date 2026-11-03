import re
import unittest
from pathlib import Path

from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_pack import FlowPack

CONNECTIONS = Path(__file__).parents[2] / "src" / "streamer_toolbox" / "connections"
REF = re.compile(r"\$\{box\.(\w+)\.(\w+)\}")


class TestDefaultFlowFiles(unittest.TestCase):
    """The ready-made flows the connections give: every file reads, every trigger is a known event, and every
    value a box takes from a Start box is a field that event has (a typo would leave an empty chat message)."""

    def test_every_file(self) -> None:
        files = sorted(CONNECTIONS.glob("*/default_flows.flows.toml"))
        self.assertGreaterEqual(len(files), 2)
        for file in files:
            with self.subTest(file.parent.name):
                pack = FlowPack.from_text(file.read_text(encoding="utf-8"))
                self.assertTrue(pack.folder)
                for flow in pack.flows:
                    kinds = {t.id: t.kind for t in flow.triggers}
                    for kind in kinds.values():
                        self.assertIn(kind, EVENT_FIELDS, flow.name)
                    for node in flow.nodes:
                        for value in node.params.values():
                            for box, field in REF.findall(str(value)):
                                if box in kinds:
                                    self.assertIn(field, EVENT_FIELDS[kinds[box]], f"{flow.name}: {value}")
                                elif box == "input":  # the flow's Input box: one of its inputs
                                    self.assertIn(field, [i.name for i in flow.inputs], f"{flow.name}: {value}")
                                else:
                                    self.assertIsNotNone(flow.node(box), f"{flow.name}: {value}")


if __name__ == "__main__":
    unittest.main()
