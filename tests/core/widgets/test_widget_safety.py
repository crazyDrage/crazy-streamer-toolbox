import unittest

from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_safety import WidgetSafety, host_of

WIDGET = Widget("chat", '<script src="https://unpkg.com/twitch-js@1/x.js"></script>'
                        '<link href="//fonts.googleapis.com/css2?family=Teko" rel="stylesheet">',
                "@import url(https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css);",
                'fetch("https://api.streamelements.com/kappa/v2/channels/x"); new WebSocket("wss://Irc.Example.org");'
                ' let a = 1 // 2; let b = "{{hook}}";', values={"hook": "https://hooks.example.net/in"})
OWN = "http://127.0.0.1:8850"


class TestWidgetSafety(unittest.TestCase):
    def test_the_hosts_the_code_names(self) -> None:
        self.assertEqual(WidgetSafety.named(WIDGET), ["cdnjs.cloudflare.com", "fonts.googleapis.com",
                                                      "hooks.example.net", "irc.example.org", "unpkg.com"])

    def test_the_start_is_both_fences_up(self) -> None:
        headers = WidgetSafety().headers(WIDGET, OWN)
        policy = headers["Content-Security-Policy"]
        self.assertTrue(policy.startswith("sandbox allow-scripts; default-src http://127.0.0.1:8850 "
                                          "ws://127.0.0.1:8850 "))
        # gstatic: Google Fonts sends the page on to it; Twitch: always, chat libraries connect to it
        for source in ("unpkg.com", "*.unpkg.com", "wss://irc.example.org", "fonts.gstatic.com", "wss://*.twitch.tv"):
            self.assertIn(f" {source} ", policy)
        self.assertNotIn("streamelements", policy)
        self.assertTrue(policy.endswith("data: blob: 'unsafe-inline' 'unsafe-eval'; "
                                        "report-uri /overlay/widget/chat/blocked"))
        self.assertNotIn("allow-same-origin", policy)

    def test_a_host_he_switched_off_and_one_he_added(self) -> None:
        safety = WidgetSafety.from_dict({"blocked": ["UNPKG.com"], "extra": ["api.jebaited.net", "not a host"]})
        self.assertEqual(safety.to_dict(), {"sandbox": True, "hosts": "block", "blocked": ["unpkg.com"],
                                            "extra": ["api.jebaited.net"]})
        allowed = safety.allowed(WIDGET)
        self.assertIn("api.jebaited.net", allowed)
        self.assertNotIn("unpkg.com", allowed)
        self.assertIn(" streamelements.com ", safety.headers(WIDGET, OWN, ("streamelements.com",))
                      ["Content-Security-Policy"])  # with the fallback switched on

    def test_only_noting_and_off(self) -> None:
        noting = WidgetSafety(sandbox=False, hosts="report").headers(WIDGET, OWN)
        self.assertEqual(list(noting), ["Content-Security-Policy-Report-Only"])
        self.assertEqual(WidgetSafety(sandbox=False, hosts="off").headers(WIDGET, OWN), {})
        self.assertEqual(WidgetSafety(hosts="off").headers(WIDGET, OWN),
                         {"Content-Security-Policy": "sandbox allow-scripts"})
        self.assertEqual(WidgetSafety.from_dict({"hosts": "whatever"}).hosts, "block")

    def test_the_host_of_what_the_browser_reports(self) -> None:
        self.assertEqual(host_of("https://Evil.example.com/collect?x=1"), "evil.example.com")
        self.assertEqual(host_of("wss://evil.example.com"), "evil.example.com")
        self.assertEqual(host_of("evil.example.com"), "evil.example.com")
        for nothing in ("inline", "eval", "data", ""):
            self.assertEqual(host_of(nothing), "")


if __name__ == "__main__":
    unittest.main()
