from dataclasses import replace

from streamer_toolbox.core.widgets.streamelements_links import without_streamelements_links
from streamer_toolbox.core.widgets.streamelements_media import StreamElementsMedia
from streamer_toolbox.core.widgets.widget_helpers import WidgetHelpers
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class StreamElementsCleaner:
    """"Clean out StreamElements" for one widget, written into the widget itself (his round 64; on when a
    widget is imported, a button for one that is there already): every streamelements.com address in its code
    and in the values of its settings points at the toolbox, the files it loads from StreamElements' servers
    are copied into its media folder, and so are the helper scripts it loads from other servers. Afterwards
    the widget needs neither StreamElements nor the internet.

    It still runs in StreamElements' widget format (SE_API, onWidgetLoad, ...): the toolbox's own stand-in
    answers those, so no code of theirs is left. Whether he may copy the files is his to check (the GUI asks
    first: CopyFilesQuestion)."""

    def __init__(self, store: WidgetStore, media: StreamElementsMedia, helpers: WidgetHelpers) -> None:
        self._store = store
        self._media = media
        self._helpers = helpers

    async def clean(self, name: str) -> tuple[int, list[str]]:
        """Cleans the widget. Gives how many addresses were changed and the files that couldn't be fetched
        (those keep loading from where they are)."""
        widget = self._store.get(name)
        if widget is None:
            raise KeyError(f"there's no widget {name!r}")
        missed = (await self._media.keep(name))[1] + (await self._helpers.keep(name))[1]
        changed = 0
        parts: dict[str, str] = {}
        for part in ("html", "css", "js"):
            parts[part], count = without_streamelements_links(getattr(widget, part))
            changed += count
        values = {}
        for key, value in widget.values.items():
            if isinstance(value, str):
                value, count = without_streamelements_links(value)
                changed += count
            values[key] = value
        if changed:
            self._store.save(replace(widget, **parts, values=values))
        return changed, missed
