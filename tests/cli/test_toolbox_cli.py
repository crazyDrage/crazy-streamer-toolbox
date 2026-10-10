import json
import unittest

import httpx

from streamer_toolbox.cli.__main__ import read_params
from streamer_toolbox.cli.toolbox_cli import ToolboxCli

ACTIONS = [{"name": "hello.greet", "label": "Say hello", "description": "Counts greetings",
            "params": [{"name": "name", "required": False}]},
           {"name": "obs.set_scene", "label": "Switch scene", "description": "",
            "params": [{"name": "scene", "required": True}]}]


class TestToolboxCli(unittest.TestCase):
    def setUp(self) -> None:
        self.requests: list[httpx.Request] = []
        self.lines: list[str] = []

    def _cli(self, token: str = "") -> ToolboxCli:
        return ToolboxCli("http://toolbox.test/", token, self.lines.append, httpx.MockTransport(self._answer))

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/actions":
            return httpx.Response(200, json=ACTIONS)
        if request.url.path == "/action/hello.greet":
            name = json.loads(request.content or b"{}").get("name", "you")
            return httpx.Response(200, json={"action": "hello.greet", "result": f"hello {name} (#1)"})
        if request.url.path == "/action/obs.stats":
            return httpx.Response(200, json={"action": "obs.stats", "result": {"fps": 60.0}})
        if request.url.path == "/action/obs.set_scene":
            return httpx.Response(500, json={"action": "obs.set_scene", "error": "OBS is switched off"})
        return httpx.Response(404, json={"detail": f"unknown action {request.url.path[8:]}"})

    def test_list_shows_the_names_that_fit(self) -> None:
        self.assertEqual(self._cli().list(), 0)
        self.assertEqual(self.lines, ["hello.greet    Say hello", "obs.set_scene  Switch scene", "2 of 2 actions"])
        self.lines.clear()
        self._cli().list("obs.*")
        self.assertEqual(self.lines, ["obs.set_scene  Switch scene", "1 of 2 actions"])
        self.lines.clear()
        self._cli().list("scene")  # a word without * is searched in the names
        self.assertEqual(self.lines[-1], "1 of 2 actions")

    def test_info_names_the_parameters(self) -> None:
        self.assertEqual(self._cli().info("hello.greet"), 0)
        self.assertEqual(self.lines, ["hello.greet: Say hello", "Counts greetings", "  name  (optional)"])
        self.lines.clear()
        self._cli().info("obs.set_scene")
        self.assertEqual(self.lines, ["obs.set_scene: Switch scene", "  scene"])
        self.assertEqual(self._cli().info("no.such"), 1)

    def test_run_sends_the_parameters_and_prints_the_result(self) -> None:
        self.assertEqual(self._cli("secret").run("hello.greet", {"name": "chat"}), 0)
        self.assertEqual(self.lines, ["hello chat (#1)"])
        sent = self.requests[-1]
        self.assertEqual((sent.method, json.loads(sent.content)), ("POST", {"name": "chat"}))
        self.assertEqual(sent.headers["Authorization"], "Bearer secret")
        self.lines.clear()
        self._cli().run("obs.stats", {})
        self.assertEqual(self.requests[-1].content, b"")  # no parameters: an empty body
        self.assertNotIn("Authorization", self.requests[-1].headers)
        self.assertEqual(json.loads("".join(self.lines)), {"fps": 60.0})

    def test_a_failure_says_why_and_gives_exit_code_1(self) -> None:
        self.assertEqual(self._cli().run("obs.set_scene", {"scene": "x"}), 1)
        self.assertEqual(self.lines, ["failed (500): OBS is switched off"])
        self.lines.clear()
        self.assertEqual(self._cli().run("no.such", {}), 1)
        self.assertEqual(self.lines, ["failed (404): unknown action no.such"])

    def test_a_toolbox_that_is_not_running_is_said_so(self) -> None:
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        cli = ToolboxCli("http://toolbox.test", out=self.lines.append, transport=httpx.MockTransport(refuse))
        self.assertEqual(cli.list(), 1)
        self.assertIn("is it running?", self.lines[0])

    def test_parameters_from_the_command_line(self) -> None:
        self.assertEqual(read_params(["name=chat", "text=a=b"], ""), {"name": "chat", "text": "a=b"})
        self.assertEqual(read_params(["volume=007"], '{"volume": 0.5, "on": true}'), {"volume": "007", "on": True})
        with self.assertRaises(ValueError):
            read_params(["chat"], "")
        with self.assertRaises(ValueError):
            read_params([], "[1]")


if __name__ == "__main__":
    unittest.main()
