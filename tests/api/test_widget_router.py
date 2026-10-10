import tempfile

import httpx
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamer_toolbox.api.widget_router import build_widget_router
from streamer_toolbox.api.widget_sandbox_middleware import WidgetSandboxMiddleware
from streamer_toolbox.core.widgets.channel_lookup import ChannelLookup
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_page import WidgetPage, fill
from streamer_toolbox.core.widgets.widget_safety import WidgetSafety
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from tests.fakes.fake_helix import FakeHelix

FIELDS = {"title": {"type": "text", "label": "Title", "value": "Latest"},
          "color": {"type": "colorpicker", "label": "Colour", "value": "#ff0000"},
          "ding": {"type": "sound-input", "label": "Sound"}}


class TestWidgetRouter(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.store = WidgetStore(self.folder / "widgets")
        self.hub = WidgetHub()
        self.asked: list[str] = []

        def streamelements(request: httpx.Request) -> httpx.Response:
            self.asked.append(request.url.path)
            return httpx.Response(200, json={"from": "streamelements"})
        self.fallback = StreamElementsFallback({}, transport=httpx.MockTransport(streamelements))

        def emote_services(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/3/cached/users/twitch/42":
                return httpx.Response(200, json={"channelEmotes": [{"id": "b1", "code": "crazyLurk"}],
                                                 "sharedEmotes": []})
            return httpx.Response(404, json={"message": "not known here"})
        app = FastAPI()
        app.add_middleware(WidgetSandboxMiddleware)
        app.include_router(build_widget_router(self.store, self.hub, WidgetPage(
            self.hub.session, lambda: {"username": "dragon", "providerId": "42"}),
            ChannelLookup(FakeHelix({("GET", "users"): lambda params: {"data": [
                {"id": "42", "login": "dragon", "display_name": "Dragon", "profile_image_url": "https://pic/d.png"}
            ] if params.get("login") == "dragon" else []}})), self.fallback,
            EmoteLookup(httpx.MockTransport(emote_services))))
        self.client = TestClient(app)
        self.store.save(Widget("follow_box", '<div class="t">{{title}} {title} {other}</div>',
                               ".t { color: {{color}}; }",
                               'const {name} = {name: "x"}; const t = "{{title}}"; const s = "</script>";', FIELDS))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_page_has_the_parts_with_the_field_values_filled_in(self) -> None:
        page = self.client.get("/overlay/widget/follow_box/page")
        self.assertEqual((page.status_code, page.headers["cache-control"]), (200, "no-store"))
        self.assertIn('<div class="t">Latest Latest {other}</div>', page.text)  # a name that's no field stays
        self.assertIn(".t { color: #ff0000; }", page.text)
        self.assertIn('const {name} = {name: "x"}; const t = "Latest";', page.text)  # JS: only {{field}}
        self.assertIn('const s = "<\\/script>";', page.text)  # can't end our script tag early
        self.assertIn('"username": "dragon"', page.text)
        self.assertLess(page.text.index("/static/overlay/widget.js"), page.text.index("const t ="))
        # jQuery is there before his HTML and code, as on StreamElements: widgets use $ without loading it
        self.assertLess(page.text.index("/static/overlay/vendor/jquery.min.js"), page.text.index("<body>"))
        self.assertEqual(self.client.get("/overlay/widget/gone/page").status_code, 404)

    def test_who_a_channel_is_comes_from_twitch(self) -> None:
        answer = self.client.get("/overlay/widget/follow_box/streamelements/api/kappa/v2/channels/dragon")
        self.assertEqual((answer.status_code, answer.json()["avatar"], answer.json()["provider"]),
                         (200, "https://pic/d.png", "twitch"))
        missing = self.client.get("/overlay/widget/follow_box/streamelements/api/kappa/v2/channels/nobody")
        self.assertEqual((missing.status_code, missing.json()), (404, {  # as StreamElements says it
            "statusCode": 404, "error": "Not Found", "message": "channel nobody was not found"}))
        for who in ("dragon", "42"):  # by name (through Twitch) or by Twitch id
            emotes = self.client.get(f"/overlay/widget/follow_box/streamelements/api/kappa/v2/channels/{who}/emotes").json()
            self.assertEqual(emotes["bttvChannelEmotes"]["crazyLurk"]["urls"]["2"],
                             "https://cdn.betterttv.net/emote/b1/2x")
            self.assertEqual((emotes["ffzChannelEmotes"], emotes["bttvGlobalEmotes"]), ({}, {}))
        other = self.client.get("/overlay/widget/follow_box/streamelements/api/kappa/v2/store/products")
        self.assertEqual((other.status_code, other.json()["error"]), (404, "Not Found"))
        self.assertEqual(self.client.get("/overlay/widget/follow_box/streamelements/cdn/static/a.png").status_code, 404)
        self.assertEqual(self.asked, [])  # StreamElements is never asked while the switch is off
        # what was looked up is kept in the asking widget's own data folder, and goes in one go
        self.assertEqual(sorted(self.store.data_files("follow_box")), ["channels.json", "emotes.json"])
        self.assertEqual(self.client.get("/overlay/widget/gone/streamelements/api/kappa/v2/channels/dragon")
                         .status_code, 404)
        self.assertEqual(self.store.clear_data("follow_box"), 2)
        self.assertEqual(self.store.data_files("follow_box"), {})
        self.assertIsNotNone(self.store.get("follow_box"))

    def test_with_the_switch_on_streamelements_answers_what_the_toolbox_cant(self) -> None:
        self.fallback.set(True)
        self.assertEqual(self.client.get("/overlay/widget/follow_box/streamelements/api/kappa/v2/channels/dragon").json()["provider"], "twitch")
        for path in ("channels/nobody", "store/products"):
            self.assertEqual(self.client.get("/overlay/widget/follow_box/streamelements/api/kappa/v2/" + path).json(),
                             {"from": "streamelements"})
        file = self.client.get("/overlay/widget/follow_box/streamelements/cdn/static/a.png", follow_redirects=False)
        self.assertEqual((file.status_code, file.headers["location"]),
                         (307, "https://cdn.streamelements.com/static/a.png"))  # the page fetches their file
        self.assertEqual(self.asked, ["/kappa/v2/channels/nobody", "/kappa/v2/store/products"])

    def test_the_page_names_the_toolbox_where_the_code_names_streamelements_api(self) -> None:
        self.store.save(Widget("chat", '<script src="//api.streamelements.com/kappa/v2/x.js"></script>', "",
                               'fetch("https://api.streamelements.com/kappa/v2/channels/" + name);'))
        page = self.client.get("/overlay/widget/chat/page").text
        self.assertIn('fetch("/overlay/widget/chat/streamelements/api/kappa/v2/channels/" + name);', page)
        self.assertIn('<script src="/overlay/widget/chat/streamelements/api/kappa/v2/x.js">', page)
        self.assertNotIn("streamelements.com", page)
        self.assertIn("api.streamelements.com", self.store.get("chat").js)  # his file stays as written

    def test_what_his_code_gets_when_it_loads(self) -> None:
        widget = self.store.get("follow_box")
        page = WidgetPage(self.hub.session, lambda: {"username": "dragon", "providerId": "42", "id": "se1"})
        detail = page.load_detail(page.field_data(widget))
        self.assertEqual(detail["fieldData"], {"title": "Latest", "color": "#ff0000", "ding": ""})
        self.assertEqual(detail["session"]["data"]["follower-latest"]["name"], "")
        self.assertEqual((detail["channel"]["username"], detail["channel"]["providerId"], detail["channel"]["id"],
                          detail["currency"]["code"]), ("dragon", "42", "se1", "USD"))
        self.assertEqual(fill("{{ title }} {{on}}", {"title": "a", "on": True}, single=False), "a true")

    def test_a_viewers_name_cant_break_out_of_the_page(self) -> None:
        self.hub.session.add("follower-latest", {"type": "follower", "name": "</script><script>alert(1)</script>"})
        page = self.client.get("/overlay/widget/follow_box/page").text
        self.assertNotIn("</script><script>alert(1)", page)

    def test_the_page_comes_with_its_fences(self) -> None:
        self.store.save(Widget("chat", '<script src="https://unpkg.com/x.js"></script>'))
        policy = self.client.get("/overlay/widget/chat/page").headers["content-security-policy"]
        self.assertIn("sandbox allow-scripts", policy)
        self.assertIn("default-src http://testserver ws://testserver ", policy)
        self.assertIn(" unpkg.com *.unpkg.com ", policy)
        self.assertNotIn("streamelements.com", policy)
        self.fallback.set(True)  # asking StreamElements is switched on: its hosts are allowed too
        self.assertIn(" streamelements.com ", self.client.get("/overlay/widget/chat/page").headers["content-security-policy"])
        self.store.set_safety("chat", WidgetSafety(sandbox=False, hosts="off"))
        self.assertNotIn("content-security-policy", self.client.get("/overlay/widget/chat/page").headers)

    def test_what_the_browser_stopped_is_kept_for_the_widgets_window(self) -> None:
        for uri in ("https://evil.example.com/collect", "https://evil.example.com/again", "inline"):
            answer = self.client.post("/overlay/widget/follow_box/blocked", content=(
                '{"csp-report": {"blocked-uri": "%s", "violated-directive": "connect-src"}}' % uri),
                headers={"Content-Type": "application/csp-report"})
            self.assertEqual(answer.status_code, 200)
        self.client.post("/overlay/widget/follow_box/blocked", content="not json")
        self.assertEqual(self.store.blocked("follow_box"), {"evil.example.com": 2})
        self.assertEqual(self.client.post("/overlay/widget/nobody/blocked", content="{}").status_code, 404)

    def test_a_sandboxed_page_reaches_its_own_routes_and_other_sites_dont(self) -> None:
        store = "/overlay/widget/follow_box/store/count"
        asked = self.client.options(store, headers={"Origin": "null", "Access-Control-Request-Method": "PUT"})
        self.assertEqual((asked.status_code, asked.headers["access-control-allow-origin"],
                          asked.headers["access-control-allow-methods"]), (204, "null", "GET, PUT"))
        kept = self.client.put(store, json=3, headers={"Origin": "null"})
        self.assertEqual((kept.status_code, kept.headers["access-control-allow-origin"]), (200, "null"))
        self.assertEqual(self.client.get(store, headers={"Origin": "null"}).json(), 3)
        self.assertEqual(self.client.get(store, headers={"Origin": "https://evil.example.com"}).status_code, 403)
        self.assertEqual(self.client.put(store, json=9, headers={"Origin": "https://evil.example.com"}).status_code,
                         403)
        self.assertEqual(self.client.get(store).json(), 3)  # no Origin (OBS, the toolbox itself): as before
        self.assertEqual(self.client.get(store, headers={"Origin": "http://testserver"}).status_code, 200)
        # the page itself is not handed to other sites' code
        page = self.client.get("/overlay/widget/follow_box/page", headers={"Origin": "null"})
        self.assertNotIn("access-control-allow-origin", page.headers)

    def test_the_address_obs_opens_is_a_shell_that_keeps_the_widget_on_its_page(self) -> None:
        shell = self.client.get("/overlay/widget/follow_box?preview=1")
        self.assertEqual((shell.status_code, shell.headers["cache-control"]), (200, "no-store"))
        self.assertIn('<iframe src="/overlay/widget/follow_box/page?preview=1" sandbox="allow-scripts" '
                      'allow="autoplay *">', shell.text)
        self.assertNotIn("const t =", shell.text)  # none of the widget's code is on the shell
        policy = shell.headers["content-security-policy"]
        self.assertIn("frame-src http://testserver/overlay/widget/follow_box/page;", policy)  # nowhere else
        self.assertIn("default-src 'none'", policy)
        self.assertIn("report-uri /overlay/widget/follow_box/blocked", policy)
        # the widget's own fences switched off: the frame still can't leave
        self.store.set_safety("follow_box", WidgetSafety(sandbox=False, hosts="off"))
        shell = self.client.get("/overlay/widget/follow_box")
        self.assertIn('<iframe src="/overlay/widget/follow_box/page" sandbox="allow-scripts allow-same-origin"',
                      shell.text)
        self.assertIn("frame-src http://testserver/overlay/widget/follow_box/page;",
                      shell.headers["content-security-policy"])
        self.assertEqual(self.client.get("/overlay/widget/gone").status_code, 404)

    def test_the_widgets_page_is_only_served_into_a_frame(self) -> None:
        inside = self.client.get("/overlay/widget/follow_box/page", headers={"Sec-Fetch-Dest": "iframe"})
        self.assertEqual(inside.status_code, 200)
        opened = self.client.get("/overlay/widget/follow_box/page?preview=1", headers={"Sec-Fetch-Dest": "document"},
                                 follow_redirects=False)
        self.assertEqual((opened.status_code, opened.headers["location"]),
                         (307, "/overlay/widget/follow_box?preview=1"))

    def test_a_file_of_the_widgets_media_folder(self) -> None:
        self.store.save_media("follow_box", "ab12.png", b"png-bytes")
        self.assertEqual(self.client.get("/overlay/widget/follow_box/media/ab12.png").content, b"png-bytes")
        for path in ("follow_box/media/other.png", "follow_box/media/..%2Fvalues.json", "nobody/media/ab12.png"):
            self.assertEqual(self.client.get("/overlay/widget/" + path).status_code, 404)

    def test_a_media_field_serves_only_the_file_he_picked(self) -> None:
        sound = self.folder / "ding.ogg"
        sound.write_bytes(b"ogg-bytes")
        self.assertEqual(self.client.get("/overlay/widget/follow_box/file/ding").status_code, 404)  # none picked
        self.store.set_values("follow_box", {"ding": str(sound), "title": str(sound)})
        self.assertEqual(self.client.get("/overlay/widget/follow_box/file/ding").content, b"ogg-bytes")
        self.assertEqual(self.client.get("/overlay/widget/follow_box/file/title").status_code, 404)  # a text field
        self.assertIn("/overlay/widget/follow_box/file/ding", self.client.get("/overlay/widget/follow_box/page").text)
        self.assertNotIn(str(self.folder).replace("\\", "\\\\") + "\\\\ding", self.client.get(
            "/overlay/widget/follow_box/page").text.split("fieldData")[1].split("ding")[0])

    def test_the_code_can_keep_data(self) -> None:
        self.assertIsNone(self.client.get("/overlay/widget/follow_box/store/count").json())
        self.assertEqual(self.client.put("/overlay/widget/follow_box/store/count", json={"value": 3}).status_code, 200)
        self.assertEqual(self.client.get("/overlay/widget/follow_box/store/count").json(), {"value": 3})
        self.assertEqual(self.client.put("/overlay/widget/gone/store/count", json=1).status_code, 404)

    def test_a_page_listens_while_its_socket_is_open(self) -> None:
        with self.client.websocket_connect("/overlay/widget/follow_box/ws"):
            self.assertEqual(self.hub.pages("follow_box"), 1)
        with self.client.websocket_connect("/overlay/widget/follow_box/ws?preview=1"):
            self.assertEqual(self.hub.pages("follow_box"), 0)


if __name__ == "__main__":
    unittest.main()
