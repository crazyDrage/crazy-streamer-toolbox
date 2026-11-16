import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamer_toolbox.api.media_router import build_media_router
from streamer_toolbox.core.media.media_buffer import MediaBuffer
from tests.fakes.fake_media_web import PNG, FakeMediaWeb

PIC = "https://example.com/kit.png"


class TestMediaRouter(unittest.IsolatedAsyncioTestCase):
    """GET /toolbox/media/...: only what the buffer keeps, shown, never run; a box's address and its latest."""

    async def asyncSetUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        web = FakeMediaWeb()
        web.picture(PIC)
        self.buffer = MediaBuffer(Path(self._dir.name), web.transport, resolve=web.resolve)
        app = FastAPI()
        app.include_router(build_media_router(self.buffer))
        self.client = TestClient(app)

    async def asyncTearDown(self) -> None:
        self._dir.cleanup()

    async def test_a_kept_file_is_served(self) -> None:
        kept = await self.buffer.keep(PIC)
        answer = self.client.get(kept.address)
        self.assertEqual((200, PNG), (answer.status_code, answer.content))
        self.assertEqual("image/png", answer.headers["content-type"])
        self.assertEqual("sandbox", answer.headers["content-security-policy"])
        self.assertEqual("nosniff", answer.headers["x-content-type-options"])
        self.assertEqual("max-age=86400", answer.headers["cache-control"])

    async def test_a_boxs_address_and_its_latest(self) -> None:
        kept = await self.buffer.keep(PIC, box=("event_chat", "n3"))
        self.assertEqual(PNG, self.client.get(kept.address).content)
        latest = self.client.get("/toolbox/media/flows/box/event_chat/n3/latest.png")
        self.assertEqual((200, PNG, "no-cache"), (latest.status_code, latest.content, latest.headers["cache-control"]))

    async def test_anything_else_is_not_found(self) -> None:
        await self.buffer.keep(PIC)
        await self.buffer.keep(PIC, box=("event_chat", "n3"))
        for path in ("/toolbox/media/shared/media/index.json", "/toolbox/media/shared/media/" + "0" * 16 + ".png",
                     "/toolbox/media/shared/other/latest.png", "/toolbox/media/flows/box/event_chat/n4/latest.png",
                     "/toolbox/media/flows/box/Event/n3/latest.png", "/toolbox/media/flows/box/event_chat/n3/index.json",
                     "/toolbox/media/../../secrets/x.png", "/media/kept/media/latest.png"):
            self.assertEqual(404, self.client.get(path).status_code, path)


if __name__ == "__main__":
    unittest.main()
