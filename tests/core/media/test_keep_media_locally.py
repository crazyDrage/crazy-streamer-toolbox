import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.current_box import current_box
from streamer_toolbox.core.media.media_actions import MediaActions
from streamer_toolbox.core.media.media_buffer import MediaBuffer
from tests.fakes.fake_media_web import FakeMediaWeb

PIC = "https://example.com/kit.png"


class TestKeepMediaLocally(unittest.IsolatedAsyncioTestCase):
    """The box: a web address in, where the toolbox keeps it out; a chat never stops at it."""

    async def asyncSetUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.web = FakeMediaWeb()
        self.web.picture(PIC)
        self.actions = ActionRegistry()
        MediaActions(MediaBuffer(Path(self._dir.name), self.web.transport, resolve=self.web.resolve)).add_to(self.actions)

    async def asyncTearDown(self) -> None:
        self._dir.cleanup()

    async def test_gives_the_toolbox_address_and_the_file(self) -> None:
        out = await self.actions.run("media.keep_locally", url=PIC)  # on Live / the API: no box
        self.assertTrue(out["kept"])
        self.assertRegex(out["address"], r"^/toolbox/media/shared/media/[0-9a-f]{16}\.png$")
        self.assertTrue(Path(out["file"]).is_file())

    async def test_in_a_flow_the_address_is_the_boxs_own(self) -> None:
        """His 11-15: "every flow, and box in the flow should have an endpoint"."""
        token = current_box.set(("event_chat", "n3"))
        try:
            out = await self.actions.run("media.keep_locally", url=PIC, name="Kit Fox!")
        finally:
            current_box.reset(token)
        self.assertRegex(out["address"], r"^/toolbox/media/flows/box/event_chat/n3/[0-9a-f]{16}_Kit-Fox\.png$")
        self.assertEqual(Path(self._dir.name).resolve() / "flows" / "box" / "event_chat" / "n3",
                         Path(out["file"]).parent)

    async def test_nothing_to_keep_gives_nothing(self) -> None:
        self.assertEqual({"address": "", "file": "", "kept": False},
                         await self.actions.run("media.keep_locally", url=" "))
        self.assertEqual([], self.web.asked)

    async def test_when_it_cant_be_kept_the_web_address_goes_on(self) -> None:
        with self.assertLogs("streamer_toolbox.core.media.boxes.keep_media_locally", "WARNING"):
            out = await self.actions.run("media.keep_locally", url="https://example.com/gone.png")
        self.assertEqual({"address": "https://example.com/gone.png", "file": "", "kept": False}, out)


if __name__ == "__main__":
    unittest.main()
