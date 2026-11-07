from nicegui import ui

NOT_TESTED = "Not tested yet: nobody has said it works. Tell us if it does (or doesn't)."


class NotTestedMark:
    """A small flask next to a connection or a box that has no yes under Works in the test record yet (his notes
    of 2026-11-07: "an `not tested` icon to every connection and box we didn't test yet", easier to see later)."""

    @staticmethod
    def build() -> None:
        ui.icon("science").classes("text-amber-600 text-base shrink-0").tooltip(NOT_TESTED)
