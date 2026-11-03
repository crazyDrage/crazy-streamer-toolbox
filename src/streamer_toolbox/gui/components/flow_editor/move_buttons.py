from collections.abc import Callable

from nicegui import ui


def move_buttons(number: int, count: int, on_move: Callable[[int], None]) -> None:
    """↑ and ↓ for one line of a list (his round 59: the order of a box's values); the first has no ↑, the last
    no ↓, so the row keeps its width."""
    with ui.column().classes("gap-0 shrink-0"):
        for icon, step, there in (("arrow_upward", -1, number > 1), ("arrow_downward", 1, number < count)):
            button = ui.button(icon=icon, on_click=lambda s=step: on_move(s)).props("flat round dense size=xs")
            button.tooltip("Move up" if step < 0 else "Move down")
            if not there:
                button.classes("invisible")
