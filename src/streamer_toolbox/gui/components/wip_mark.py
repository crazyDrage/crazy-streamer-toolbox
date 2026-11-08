from nicegui import ui

WIP = "Work in progress: still being built and tested. Keep a backup of your config folder before you import."


class WipMark:
    """A small orange "WIP" chip next to a title, for a part that is still being built (his round 88: "make sure
    you mark the import/export page with WIP")."""

    @staticmethod
    def build() -> None:
        ui.badge("WIP", color="orange").props("outline").classes("text-xs shrink-0").tooltip(WIP)
