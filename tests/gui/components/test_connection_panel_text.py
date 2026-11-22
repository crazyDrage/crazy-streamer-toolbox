import unittest

from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.gui.components.connection_panel import text_to_show

DOWN = ConnectionStatus(ConnectionState.ERROR, "can't reach OBS (connection refused)")


class TestConnectionPanelText(unittest.TestCase):
    """A retry keeps the text on the tab, so the tab keeps its size while a program isn't running."""

    def test_a_plain_retry_keeps_the_error_text(self) -> None:
        for detail in ("", "connecting"):
            with self.subTest(detail=detail):
                self.assertIs(DOWN, text_to_show(DOWN, ConnectionStatus(ConnectionState.CONNECTING, detail)))

    def test_a_retry_that_says_something_shows_it(self) -> None:
        asking = ConnectionStatus(ConnectionState.CONNECTING, "Click Allow in VTube Studio")
        self.assertEqual(asking, text_to_show(DOWN, asking))

    def test_the_next_error_and_connected_are_shown(self) -> None:
        later = ConnectionStatus(ConnectionState.ERROR, "OBS closed the connection")
        self.assertEqual(later, text_to_show(DOWN, later))
        connected = ConnectionStatus(ConnectionState.CONNECTED, "", (("Version", "31"),))
        self.assertEqual(connected, text_to_show(DOWN, connected))

    def test_a_countdown_shows_without_its_seconds_so_the_text_stays_the_same(self) -> None:
        tries = [ConnectionStatus(ConnectionState.ERROR, f"refused; trying again in {s} s") for s in (2, 4, 60)]
        shown = [text_to_show(DOWN, status) for status in tries]
        self.assertEqual({"refused; trying again"}, {status.detail for status in shown})
        self.assertEqual(shown[0], shown[2])

    def test_the_first_connect_shows_connecting(self) -> None:
        first = ConnectionStatus(ConnectionState.CONNECTING, "connecting")
        self.assertEqual(first, text_to_show(ConnectionStatus(ConnectionState.OFF), first))


if __name__ == "__main__":
    unittest.main()
