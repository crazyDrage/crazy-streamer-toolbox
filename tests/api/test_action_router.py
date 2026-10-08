import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.api.action_router import build_action_router
from streamer_toolbox.api.caller import Caller
from streamer_toolbox.api.caller_auth import CallerAuth

KIT_TOKEN = "kit-token-0123456789abcdef"
CALLERS = [Caller("sammi", ("*",), local=True), Caller("kit", ("hello.greet",), token=KIT_TOKEN)]


class TestActionRouter(unittest.TestCase):
    def setUp(self) -> None:
        registry = ActionRegistry()

        async def greet(name: str = "chat") -> str:
            return f"hello {name}"

        async def fit(video_path: str) -> str:
            return video_path

        async def broken(scene: str) -> None:
            raise RuntimeError(f"No source was found by the name of `{scene}`")

        registry.add("hello.greet", greet, "say hello")
        registry.add("obs.switch_scene", broken, "switch")
        registry.add("obs.fit_raid_clip", fit, "fit")
        app = FastAPI()
        self.runs: list[tuple] = []
        app.include_router(build_action_router(registry, CallerAuth(CALLERS),
                                               lambda *run: self.runs.append(run)))
        self.local = TestClient(app, client=("127.0.0.1", 50000))
        self.lan = TestClient(app, client=("192.168.1.101", 50000))

    def test_local_caller_runs_action_with_json_params(self) -> None:
        r = self.local.post("/action/hello.greet", json={"name": "Kit"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"action": "hello.greet", "result": "hello Kit"})

    def test_post_without_body_uses_defaults(self) -> None:
        self.assertEqual(self.local.post("/action/hello.greet").json()["result"], "hello chat")

    def test_failing_action_answers_500_with_the_reason(self) -> None:
        r = self.local.post("/action/obs.switch_scene", json={"scene": "undefined"})
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json(), {"action": "obs.switch_scene",
                                    "error": "No source was found by the name of `undefined`"})
        self.assertEqual(self.runs[-1][:3], ("sammi", "obs.switch_scene", False))

    def test_unknown_action_is_404(self) -> None:
        self.assertEqual(self.local.post("/action/nope").status_code, 404)

    def test_lan_without_token_is_401(self) -> None:
        self.assertEqual(self.lan.post("/action/hello.greet").status_code, 401)
        self.assertEqual(self.lan.get("/actions").status_code, 401)

    def test_bearer_token_identifies_caller(self) -> None:
        r = self.lan.post("/action/hello.greet", headers={"Authorization": f"Bearer {KIT_TOKEN}"})
        self.assertEqual(r.status_code, 200)

    def test_toolbox_token_header_identifies_caller(self) -> None:
        r = self.lan.post("/action/hello.greet", headers={"X-Toolbox-Token": KIT_TOKEN})
        self.assertEqual(r.status_code, 200)

    def test_wrong_token_is_401_even_from_this_pc(self) -> None:
        r = self.local.post("/action/hello.greet", headers={"X-Toolbox-Token": "wrong-token-0123456789"})
        self.assertEqual(r.status_code, 401)

    def test_tokenless_browser_request_is_refused(self) -> None:
        r = self.local.post("/action/hello.greet", headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)
        r = self.local.post("/action/hello.greet", headers={"Origin": "https://evil.example",
                                                            "X-Toolbox-Token": KIT_TOKEN})
        self.assertEqual(r.status_code, 200)

    def test_action_outside_allowlist_looks_unknown(self) -> None:
        r = self.lan.post("/action/obs.fit_raid_clip", headers={"X-Toolbox-Token": KIT_TOKEN},
                          json={"video_path": "a.mp4"})
        self.assertEqual(r.status_code, 404)

    def test_list_shows_only_allowed_actions_with_params(self) -> None:
        r = self.lan.get("/actions", headers={"X-Toolbox-Token": KIT_TOKEN})
        self.assertEqual(r.json(), [{"name": "hello.greet", "label": "Greet", "description": "say hello",
                                     "params": [{"name": "name", "required": False}]}])
        self.assertEqual([a["name"] for a in self.local.get("/actions").json()],
                         ["hello.greet", "obs.fit_raid_clip", "obs.switch_scene"])

    def test_runs_are_reported_with_the_caller_name(self) -> None:
        self.local.post("/action/hello.greet", json={"name": "Kit"})
        self.assertEqual(self.runs, [("sammi", "hello.greet", True, "hello Kit")])

    def test_missing_or_unknown_params_are_422(self) -> None:
        self.assertEqual(self.local.post("/action/obs.fit_raid_clip").status_code, 422)
        self.assertEqual(self.local.post("/action/hello.greet", json={"nope": 1}).status_code, 422)

    def test_body_without_content_type_is_read_as_json(self) -> None:
        # SAMMI's HTTP Request sends no headers unless given a header object
        r = self.local.post("/action/obs.fit_raid_clip", content=b'{"video_path": "raid_clip.mp4"}')
        self.assertEqual(r.json()["result"], "raid_clip.mp4")

    def test_body_is_read_as_json_whatever_the_content_type(self) -> None:
        r = self.local.post("/action/obs.fit_raid_clip", content=b'{"video_path": "raid_clip.mp4"}',
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(r.json()["result"], "raid_clip.mp4")

    def test_body_that_is_not_a_json_object_is_422(self) -> None:
        self.assertEqual(self.local.post("/action/hello.greet", content=b"[1, 2]").status_code, 422)
        self.assertEqual(self.local.post("/action/hello.greet", content=b"name=x").status_code, 422)


if __name__ == "__main__":
    unittest.main()
