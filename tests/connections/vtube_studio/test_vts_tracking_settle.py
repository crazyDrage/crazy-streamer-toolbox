import asyncio
import unittest

from streamer_toolbox.connections.vtube_studio.vts_tracking_settle import VtsTrackingSettle

FOUND = {"face": True, "left_hand": False, "right_hand": False}
LOST = {"face": False, "left_hand": False, "right_hand": False}


class VtsTrackingSettleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.told: list[dict] = []
        self.settle = VtsTrackingSettle(self.told.append, seconds=0.05)

    async def test_a_change_that_stays_is_told_once(self) -> None:
        self.settle.offer(FOUND)
        self.assertEqual(self.told, [])
        await asyncio.sleep(0.12)
        self.assertEqual(self.told, [FOUND])

    async def test_a_missed_picture_is_not_told(self) -> None:
        self.settle.offer(FOUND)
        await asyncio.sleep(0.12)
        self.settle.offer(LOST)
        self.settle.offer(FOUND)
        await asyncio.sleep(0.12)
        self.assertEqual(self.told, [FOUND])

    async def test_lost_for_longer_is_told(self) -> None:
        self.settle.offer(FOUND)
        await asyncio.sleep(0.12)
        self.settle.offer(LOST)
        await asyncio.sleep(0.12)
        self.assertEqual(self.told, [FOUND, LOST])

    async def test_stop_drops_what_waits(self) -> None:
        self.settle.offer(FOUND)
        self.settle.stop()
        await asyncio.sleep(0.12)
        self.assertEqual(self.told, [])
