import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.object_actions import ObjectActions
from streamer_toolbox.core.data.text_actions import TextActions
from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore

FILE = Path(__file__).parents[3] / "src" / "streamer_toolbox" / "connections" / "vtube_studio" / \
    "default_flows.flows.toml"


class TestVtsDefaultFlows(unittest.IsolatedAsyncioTestCase):
    """VTube Studio's default flows (from his own "model_pos" flows, 10-30): a spot saves where the model is and
    moves it back, loading the model first when another one is loaded. VTube Studio's boxes are stand-ins."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.model = "Dragon"
        self.position = {"x": 0.1, "y": -0.4, "rotation": 5.0, "size": -20.0, "model": "Dragon"}
        self.moves: list[dict[str, Any]] = []
        self.loaded: list[str] = []
        actions = ActionRegistry()
        self.variables = VariableStore(folder / "variables.json")
        LogicActions(self.variables).add_to(actions)
        TextActions().add_to(actions)
        ObjectActions().add_to(actions)
        actions.add("vts.get_model", self._get_model, "")
        actions.add("vts.get_model_position", self._get_position, "")
        actions.add("vts.move_model", self._move, "")
        actions.add("vts.load_model", self._load, "")
        self.actions = actions
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"),
                                 FlowRunner(actions, self.variables), actions)
        self.flows.load()

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _get_model(self) -> str:
        return self.model

    async def _get_position(self) -> dict[str, Any]:
        return dict(self.position)

    async def _move(self, x: float, y: float, rotation: float, size: float, seconds: float = 1.0) -> None:
        self.moves.append({"x": x, "y": y, "rotation": rotation, "size": size, "seconds": float(seconds)})

    async def _load(self, model: str) -> None:
        self.loaded.append(model)
        self.model = model

    def _add_and_switch_on(self) -> None:
        added, _ = DefaultFlows(self.flows).add(FILE)
        self.assertEqual(added, ["VTube Studio - default - model position: save/load",
                                 "VTube Studio - default - model position: desktop"])
        for flow in self.flows.all():  # they come in switched off: the spot calls the other, both must be on
            self.assertFalse(flow.enabled)
            self.flows.save(replace(flow, enabled=True), flow.name)

    async def test_a_spot_saves_and_moves_back(self) -> None:
        self._add_and_switch_on()
        await self.actions.run("flow.vts_model_position_desktop", do_save="True")
        self.assertEqual(self.variables.get("VTS_pos_desktop")["x"], 0.1)
        await self.actions.run("flow.vts_model_position_desktop", time="2")
        self.assertEqual(self.moves, [{"x": 0.1, "y": -0.4, "rotation": 5.0, "size": -20.0, "seconds": 2.0}])
        self.assertEqual(self.loaded, [])

    async def test_moving_back_loads_the_right_model_first_and_saving_skips_another(self) -> None:
        self._add_and_switch_on()
        self.variables.set("VTS_pos_human", dict(self.position))
        self.model = "Cat"
        await self.actions.run("flow.vts_model_position", do_save="False", model_pos_value_name="VTS_pos_human",
                               model_name="Dragon")
        self.assertEqual((self.loaded, len(self.moves)), (["Dragon"], 1))
        self.model = "Cat"
        await self.actions.run("flow.vts_model_position", do_save="true", model_pos_value_name="VTS_pos_cat_spot",
                               model_name="Dragon")
        self.assertIsNone(self.variables.get("VTS_pos_cat_spot"))  # another model loaded: nothing saved


if __name__ == "__main__":
    unittest.main()
