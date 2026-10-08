import asyncio
import unittest

from streamer_toolbox.core.flows.retrigger import Retrigger


class TestRetrigger(unittest.IsolatedAsyncioTestCase):
    async def test_pokes_before_the_wait_count_once_it_starts(self) -> None:
        retrigger, loop = Retrigger(), asyncio.get_running_loop()
        retrigger.poke()
        retrigger.poke()
        start = loop.time()
        self.assertEqual(await retrigger.wait(0.05, "add"), 2)
        self.assertGreaterEqual(loop.time() - start, 0.15 - 0.01)
        self.assertFalse(retrigger.open)

    async def test_start_over_ignores_pokes_from_before(self) -> None:
        retrigger, loop = Retrigger(), asyncio.get_running_loop()
        retrigger.poke()
        start = loop.time()
        self.assertEqual(await retrigger.wait(0.05, "restart"), 1)
        self.assertLess(loop.time() - start, 0.1)


if __name__ == "__main__":
    unittest.main()
