import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.variables.boxes.wait_until_variable import WaitUntilVariable
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestWaitUntilVariable(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = VariableStore(Path(self._tmp.name) / "variables")
        self.box = WaitUntilVariable(self.store)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    async def test_goes_on_at_once_when_it_already_passes(self) -> None:
        self.store.set("ready", True)
        self.assertTrue(await self.box.run("ready", "==", "true", 0.01))

    async def test_goes_on_when_the_variable_changes(self) -> None:
        waiting = asyncio.create_task(self.box.run("count", ">=", 3, 5))
        for count in range(1, 4):
            await asyncio.sleep(0)
            self.store.set("count", count)
        self.assertTrue(await waiting)

    async def test_gives_false_when_the_time_runs_out(self) -> None:
        self.store.set("count", 1)
        self.assertFalse(await self.box.run("count", ">=", 3, 0.05))

    async def test_a_missing_variable_is_empty_text(self) -> None:
        self.assertTrue(await self.box.run("token", "==", "", 0.01))
        waiting = asyncio.create_task(self.box.run("token", "!=", "", 0))  # 0 = no limit
        await asyncio.sleep(0)
        self.store.set("token", "abc")
        self.assertTrue(await waiting)

    async def test_stops_listening_after(self) -> None:
        await self.box.run("x", "==", "", 0.01)
        await self.box.run("x", "==", "1", 0.01)
        self.assertEqual([], self.store._listeners)
