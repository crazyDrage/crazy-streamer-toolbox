import logging
from collections.abc import Callable

from streamer_toolbox.gui.services.tray_picture import tray_picture

log = logging.getLogger(__name__)


class StarterTray:
    """The starter's icon next to the clock (his round 84: "put it in the system tray"). Its menu: show the
    starter, open the toolbox, restart, stop the toolbox, quit. pystray draws it on Windows and Linux (Linux needs
    a desktop with a tray); without one the starter simply has no tray. Every choice goes through `call`, so the
    window's work happens on Tk's thread."""

    def __init__(self, call: Callable[[Callable[[], None]], None], show: Callable[[], None],
                 open_toolbox: Callable[[], None], restart: Callable[[], None], stop: Callable[[], None],
                 quit_all: Callable[[], None]) -> None:
        self._icon = None
        self._call = call
        self._actions = (("Show the starter", show, True), ("Open the toolbox", open_toolbox, False),
                         ("Restart the toolbox", restart, False), ("Stop the toolbox", stop, False),
                         ("Quit (stops the toolbox)", quit_all, False))

    def start(self) -> bool:
        """True if the icon is there."""
        try:
            import pystray
            menu = pystray.Menu(*(pystray.MenuItem(text, self._on(action), default=default)
                                  for text, action, default in self._actions))
            self._icon = pystray.Icon("streamer-toolbox", tray_picture(), "streamer-toolbox", menu)
            self._icon.run_detached()
        except Exception as e:  # no tray on this desktop, or pystray missing: the window alone still works
            log.warning("no tray icon: %s", e)
            self._icon = None
        return self._icon is not None

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    def _on(self, action: Callable[[], None]) -> Callable[..., None]:
        return lambda *args: self._call(action)

