import logging
import webbrowser
from collections.abc import Callable

from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.gui.services.tray_picture import tray_picture

log = logging.getLogger(__name__)


class ToolboxTray:
    """The toolbox's icon next to the clock, so people see it is open (feedback someone gave him, 11-08; OPEN 130).
    Shown by the launcher for every start (start.bat, a browser tab, headless), so it stays through a restart;
    the starter has its own (StarterTray). Its menu: open the toolbox in the browser (also a double click),
    restart, stop. pystray draws it on Windows and Linux (Linux needs a desktop with a tray); without one the
    toolbox simply has no tray. The choices run on pystray's thread: restart and stop only close the child's
    stdin (ToolboxLauncher)."""

    def __init__(self, url: str, restart: Callable[[], None], stop: Callable[[], None],
                 open_page: Callable[[str], object] = webbrowser.open) -> None:
        self._icon = None
        self._url = url
        self._items = (("Open the toolbox", lambda: open_page(url), True),
                       ("Restart the toolbox", restart, False),
                       ("Stop the toolbox", stop, False))

    def items(self) -> tuple[tuple[str, Callable[[], object], bool], ...]:
        """The menu: (text, what it does, whether it is the double click's)."""
        return self._items

    def start(self) -> bool:
        """True if the icon is there."""
        try:
            import pystray
            menu = pystray.Menu(*(pystray.MenuItem(text, self._on(action), default=default)
                                  for text, action, default in self._items))
            self._icon = pystray.Icon("streamer-toolbox-running", tray_picture(), f"{APP_NAME}: {self._url}", menu)
            self._icon.run_detached()
        except Exception as e:  # no tray on this desktop, or pystray missing: the toolbox still runs
            log.warning("no tray icon: %s", e)
            self._icon = None
        return self._icon is not None

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
            self._icon = None

    @staticmethod
    def _on(action: Callable[[], object]) -> Callable[..., None]:
        return lambda *args: action()
