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
    """GET /media/kept/<folder>/<file>: only what the buffer keeps, shown, never run."""

    async def asyncSetUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        web = FakeMediaWeb()
        web.picture(PIC)
        self.buffer = MediaBuffer(Path(self._dir.name), web.transport)
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

    async def test_anything_else_is_not_found(self) -> None:
        await self.buffer.keep(PIC)
        for path in ("/media/kept/media/index.json", "/media/kept/media/" + "0" * 32 + ".png",
                     "/media/kept/other/" + "0" * 32 + ".png"):
            self.assertEqual(404, self.client.get(path).status_code, path)


if __name__ == "__main__":
    unittest.main()
