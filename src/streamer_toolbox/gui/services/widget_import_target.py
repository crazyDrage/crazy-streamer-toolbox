from dataclasses import replace

from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.interfaces.import_target import ImportTarget
from streamer_toolbox.core.widgets.widget import Widget, check_name
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class WidgetImportTarget(ImportTarget):
    """What the importers on Overlay → Import hand their widgets to: the widget store (Overlay → Widgets)."""

    def __init__(self, store: WidgetStore, users: EventUsers | None = None) -> None:
        self._store = store
        self._users = users

    def widget_names(self) -> list[str]:
        return self._store.names()

    def add_widget(self, widget: Widget, files: dict[str, bytes] | None = None) -> str:
        name = check_name(widget.name)
        taken = set(self._store.names())
        number = 2
        while name in taken:
            name, number = f"{check_name(widget.name)}_{number}", number + 1
        self._store.save(replace(widget, name=name))
        for file, content in (files or {}).items():
            self._store.save_media(name, file, content)
        if self._users is not None and widget.events is None:
            # the events its code listens for (follower-latest: follow), their flows made once (his round 78)
            self._users.give_events(name)
        return name
