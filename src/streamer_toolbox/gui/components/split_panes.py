from nicegui import app, ui

WIDE = "lg:w-[37rem]"  # the right part's width next to the left one on a wide screen


class SplitPanes:
    """Two parts of an editor page side by side (one under the other on a phone): the left one (a preview) takes
    what is left over, the right one (settings and code) has its own width. His round 73: either can be hidden
    so the other gets the whole width ("would be good for working on something and have more space"). Never
    both: hiding one while the other is hidden shows the other again. Remembered per editor in
    app.storage.general under `key`.

        panes = SplitPanes("widget_panes", "Preview", "Settings and code")
        panes.toggles()          # the two buttons, where they should be
        with panes.left(): ...
        with panes.right(): ..."""

    def __init__(self, key: str, left_title: str, right_title: str) -> None:
        self._key = key
        self._titles = (left_title, right_title)
        self._buttons: list[ui.button] = []
        self._parts: list[ui.element] = []
        self._row: ui.element | None = None

    def shown(self) -> tuple[bool, bool]:
        kept = app.storage.general.get(self._key) or {}
        left, right = bool(kept.get("left", True)), bool(kept.get("right", True))
        return (left, right) if left or right else (True, True)

    def toggles(self) -> None:
        for side, title in enumerate(self._titles):
            self._buttons.append(ui.button(title, on_click=lambda s=side: self._toggle(s))
                                 .props("no-caps dense").tooltip(f"Show or hide: {title}"))
        self._paint()

    def left(self) -> ui.element:
        # w-full: on a phone (one under the other) a part is as wide as the screen, not as its content (a
        # preview's 1920 wide canvas made the page that wide)
        return self._part("w-full lg:w-auto lg:flex-1 min-w-0 gap-2")

    def right(self) -> ui.element:
        return self._part("min-w-0 shrink-0 gap-2")

    def _part(self, classes: str) -> ui.element:
        if self._row is None:
            # tb-split: look.css lets such a page use the whole window's width
            self._row = ui.element("div").classes("tb-split flex flex-col lg:flex-row w-full gap-4 lg:items-start")
        with self._row:
            part = ui.column().classes(classes)
        self._parts.append(part)
        self._paint()
        return part

    def _toggle(self, side: int) -> None:
        shown = list(self.shown())
        shown[side] = not shown[side]
        if not any(shown):
            shown[1 - side] = True
        app.storage.general[self._key] = {"left": shown[0], "right": shown[1]}
        self._paint()

    def _paint(self) -> None:
        shown = self.shown()
        for side, button in enumerate(self._buttons):
            button.props(remove="outline unelevated")
            button.props(f"icon={'visibility' if shown[side] else 'visibility_off'} "
                         f"{'unelevated' if shown[side] else 'outline'}")
        for side, part in enumerate(self._parts):
            part.set_visibility(shown[side])
        if len(self._parts) == 2:  # the right part is narrow only next to a shown left part
            right = self._parts[1]
            right.classes(remove=f"w-full {WIDE}")
            right.classes(f"w-full {WIDE}" if shown[0] else "w-full")
