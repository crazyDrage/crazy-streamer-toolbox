from nicegui import ui

from streamer_toolbox.core.fonts.font_library import CSS as FONTS_CSS

THEMES = {"auto": None, "dark": True, "light": False}
PRIMARY = "#3fbfae"


class Look:
    """The look every page starts with (the "Console" look he picked on 2026-10-12): dark or light as set,
    Quasar's colours, and static/look.css on top (fonts, flat parts, the frame). The hosted fonts (Settings →
    Fonts) load first, so the Live page on a phone has them too.
    static/context_menu.js: the toolbox's own right click menu instead of the browser's, on every page."""

    @staticmethod
    def apply(theme: str) -> None:
        ui.dark_mode(THEMES.get(theme))
        ui.colors(primary=PRIMARY, positive="#58c26a", negative="#e2685f", warning="#e0a244",
                  dark="#1b2027", dark_page="#171b21")
        ui.add_head_html(f'<link rel="stylesheet" href="{FONTS_CSS}"><link rel="stylesheet" href="/static/look.css">'
                         '<script src="/static/context_menu.js"></script>')
