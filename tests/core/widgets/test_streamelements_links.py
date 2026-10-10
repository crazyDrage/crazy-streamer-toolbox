import unittest

from streamer_toolbox.core.widgets.streamelements_links import for_widget, without_streamelements_links


class TestStreamElementsLinks(unittest.TestCase):
    def test_every_streamelements_address_points_at_the_toolbox(self) -> None:
        code = ('fetch("https://api.streamelements.com/kappa/v2/channels/" + name);\n'
                'fetch(`https://API.StreamElements.com/kappa/v2/channels/${id}/emotes`);\n'
                '<img src="//cdn.streamelements.com/static/a.png">\n'
                'const home = "http://streamelements.com/dashboard", base = "https://api.streamelements.com";\n'
                'new WebSocket("wss://realtime.streamelements.com:443/socket");')
        converted, count = without_streamelements_links(code)
        self.assertEqual(count, 6)
        self.assertEqual(converted, (
            'fetch("/overlay/streamelements/api/kappa/v2/channels/" + name);\n'
            'fetch(`/overlay/streamelements/api/kappa/v2/channels/${id}/emotes`);\n'
            '<img src="/overlay/streamelements/cdn/static/a.png">\n'
            'const home = "/overlay/streamelements/www/dashboard", base = "/overlay/streamelements/api";\n'
            'new WebSocket("/overlay/streamelements/realtime/socket");'))
        self.assertEqual(without_streamelements_links(converted), (converted, 0))  # a second time changes nothing

    def test_on_its_page_the_addresses_are_the_widgets_own(self) -> None:
        code = ('fetch("https://api.streamelements.com/kappa/v2/channels/x"); '  # as written for StreamElements
                'fetch("/overlay/streamelements/cdn/a.png"); const base = "/overlay/streamelements/api";')
        self.assertEqual(for_widget(code, "chat"),
                         'fetch("/overlay/widget/chat/streamelements/api/kappa/v2/channels/x"); '
                         'fetch("/overlay/widget/chat/streamelements/cdn/a.png"); '
                         'const base = "/overlay/widget/chat/streamelements/api";')

    def test_other_addresses_and_plain_words_stay(self) -> None:
        code = ('// made for StreamElements, see https://notstreamelements.com and //streamelements.community/x\n'
                'fetch("https://unpkg.com/x.js"); fetch("https://example.org/streamelements.com/x");')
        self.assertEqual(without_streamelements_links(code), (code, 0))


if __name__ == "__main__":
    unittest.main()
