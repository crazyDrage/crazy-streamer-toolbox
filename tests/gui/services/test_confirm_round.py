import asyncio
import unittest

from streamer_toolbox.gui.services.confirm_round import ConfirmRound


class TestConfirmRound(unittest.IsolatedAsyncioTestCase):
    async def test_first_answer_wins(self) -> None:
        round_ = ConfirmRound()
        self.assertTrue(round_.answer(True))
        self.assertFalse(round_.answer(False))
        self.assertIs(await round_.wait(1), True)

    async def test_answer_while_waiting(self) -> None:
        round_ = ConfirmRound()
        asyncio.get_running_loop().call_later(0.01, round_.answer, False)
        self.assertIs(await round_.wait(1), False)

    async def test_timeout_returns_none_and_late_answer_is_ignored(self) -> None:
        round_ = ConfirmRound()
        self.assertIsNone(await round_.wait(0.01))
        self.assertFalse(round_.answer(True))


if __name__ == "__main__":
    unittest.main()
