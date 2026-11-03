import json
import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.web.web_boxes import WebBoxes

JOKES = {"group": "Jokes", "boxes": [
    {"name": "of_type", "label": "Joke of a type", "help": "A joke",
     "target": {"url": "https://jokes.test/jokes/{type}/random"},
     "input": [{"name": "type", "kind": "choice", "choices": ["general", "dad"]},
               {"name": "count", "kind": "whole_number", "optional": True}],
     "output": {"setup": "0.setup", "punchline": "0.punchline", "missing": "0.nope"}},
    {"name": "post", "target": {"method": "post", "url": "https://jokes.test/add",
                                "headers": {"Authorization": "Bearer {key}"}},
     "input": [{"name": "key"}, {"name": "text"}, {"name": "level", "kind": "number", "send_as": "lvl"}]},
]}


class TestWebBoxes(unittest.IsolatedAsyncioTestCase):
    """His round 57: a box that talks to a web API, written as JSON only (target, input, output)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.sent: list[httpx.Request] = []
        self.answer = httpx.Response(200, json=[{"setup": "Why?", "punchline": "Because."}])

        def answer(request: httpx.Request) -> httpx.Response:
            self.sent.append(request)
            return self.answer

        self.transport = httpx.MockTransport(answer)
        self.actions = ActionRegistry()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _load(self, content: dict) -> None:
        (self.folder / "jokes.json").write_text(json.dumps(content), encoding="utf-8")
        WebBoxes(self.folder, transport=self.transport).add_to(self.actions, "jokes")

    async def test_a_get_fills_the_address_sends_the_rest_after_the_question_mark_and_picks_the_outputs(self) -> None:
        self._load(JOKES)
        box = self.actions.get("jokes.of_type")
        self.assertEqual((box.label, box.group, box.flow_only), ("Joke of a type", "Jokes", True))
        self.assertEqual(box.outputs, {"setup": "any", "punchline": "any", "missing": "any"})
        self.assertEqual(await box.options["type"](), ["general", "dad"])
        result = await self.actions.run("jokes.of_type", type="dad / mom", count=2)
        self.assertEqual(result, {"setup": "Why?", "punchline": "Because.", "missing": None})
        self.assertEqual(str(self.sent[0].url), "https://jokes.test/jokes/dad%20%2F%20mom/random?count=2")
        self.assertEqual(self.sent[0].method, "GET")

    async def test_a_post_sends_json_and_fills_a_header_and_gives_the_whole_answer_without_output(self) -> None:
        self._load(JOKES)
        self.answer = httpx.Response(201, json={"id": 7})
        result = await self.actions.run("jokes.post", key="abc", text="hi", level=2)
        self.assertEqual(result, {"answer": {"id": 7}})
        request = self.sent[0]
        self.assertEqual((request.method, request.headers["Authorization"]), ("POST", "Bearer abc"))
        self.assertEqual(json.loads(request.content), {"text": "hi", "lvl": 2})
        self.assertEqual(request.headers["Content-Type"], "application/json")

    async def test_an_error_answer_or_an_empty_field_fails_the_box(self) -> None:
        self._load(JOKES)
        with self.assertRaisesRegex(ValueError, "is empty"):
            await self.actions.run("jokes.post", key="abc", level=1)
        self.answer = httpx.Response(404, text="no such type")
        with self.assertRaisesRegex(RuntimeError, "answered 404: no such type"):
            await self.actions.run("jokes.of_type", type="x")

    async def test_a_key_is_typed_on_the_plugin_s_card_never_in_the_file_and_never_shown(self) -> None:
        asked: list[tuple[str, str, str]] = []

        def secret(name: str, label: str, hint: str) -> SecretFile:
            asked.append((name, label, hint))
            return SecretFile(self.folder / f"p_{name}.txt", label, field="its field on the plugin's card")

        (self.folder / "weather.json").write_text(json.dumps({
            "secrets": {"key": {"label": "API key", "hint": "On your account page"}},
            "boxes": [{"name": "now", "target": {"url": "https://weather.test/now?k={secret.key}&city={city}",
                                                 "headers": {"X-Token": "{secret.token}"}},
                       "input": [{"name": "city"}]}]}), encoding="utf-8")
        WebBoxes(self.folder, transport=self.transport, secret=secret).add_to(self.actions, "p")
        self.assertEqual(asked, [("key", "API key", "On your account page"), ("token", "Token", "")])
        with self.assertRaisesRegex(ValueError, "No API key yet: type the API key into its field on the plugin's"):
            await self.actions.run("p.now", city="Rome")
        (self.folder / "p_key.txt").write_text("s3cr/t", encoding="utf-8")
        (self.folder / "p_token.txt").write_text("tok", encoding="utf-8")
        await self.actions.run("p.now", city="{secret.key}")  # a value can't ask for a key
        self.assertEqual(str(self.sent[0].url), "https://weather.test/now?k=s3cr%2Ft&city=%7Bsecret.key%7D")
        self.assertEqual(self.sent[0].headers["X-Token"], "tok")
        self.answer = httpx.Response(401, text="bad key s3cr/t")
        with self.assertRaises(RuntimeError) as failed:
            await self.actions.run("p.now", city="Rome")
        self.assertEqual(str(failed.exception), "GET https://weather.test/now?k=<key>&city=Rome answered 401: "
                                                "bad key <key>")

    def test_a_key_without_a_plugin_to_keep_it_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\{secret.key\} needs a plugin to keep the key"):
            self._load({"boxes": [{"name": "a", "target": {"url": "https://x/?k={secret.key}"}}]})

    def test_a_wrong_file_says_which_box_and_what(self) -> None:
        wrong = [({"name": "a", "target": {"url": "ftp://x"}}, "http:// or https://"),
                 ({"name": "a", "target": {"url": "https://x", "method": "FETCH"}}, "method must be one of"),
                 ({"name": "a", "target": {"url": "https://x/{who}"}}, r"\{who\} in the target is no input"),
                 ({"name": "a", "url": "https://x"}, "needs \"name\" and \"target\""),
                 ({"name": "a", "target": {"url": "https://x"}, "output": ["x"]}, "output must be an object")]
        for box, message in wrong:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, f"jokes.json: .*{message}"):
                self._load({"boxes": [box]})


if __name__ == "__main__":
    unittest.main()
