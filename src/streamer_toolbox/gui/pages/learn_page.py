from urllib.parse import quote

from nicegui import ui

from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.learn.learn_library import LearnLibrary
from streamer_toolbox.core.learn.learn_topic import LearnTopic

EXAMPLES = "Examples"  # the folder "Add to my flows" puts a page's example flow in
SECTION_ICONS = {"First steps": "school", "Examples": "lightbulb"}


class LearnPage:
    """Learn (his round 66: "a tab only to help building flows ... to teach and understand how this toolbox
    works", between Plugins and Settings): the pages of LearnLibrary by section. /learn is the overview,
    /learn?show=<section> one section's pages, /learn?show=<page id> one page; the side list has the sections
    with their pages as sub rows. A page with an example flow has "Add to my flows": a copy in the folder
    Examples, switched off."""

    def __init__(self, library: LearnLibrary, default_flows: DefaultFlows) -> None:
        self._library = library
        self._default_flows = default_flows

    def side_items(self) -> list[tuple[str, str, str] | tuple[str, str, str, bool]]:
        items: list[tuple[str, str, str] | tuple[str, str, str, bool]] = []
        topics = self._library.topics()
        for section in self._library.sections():
            items.append((section, f"/learn?show={quote(section, safe='')}", SECTION_ICONS.get(section, "menu_book")))
            items += [(t.title, f"/learn?show={t.id}", "article", True) for t in topics if t.section == section]
        return items

    def build(self) -> None:
        show = ui.context.client.request.query_params.get("show", "")
        topic = self._library.get(show) if show else None
        if topic is not None:
            self._topic(topic)
        elif show in self._library.sections():
            self._sections([show])
        else:
            ui.label("How the toolbox works, step by step, and examples you can copy into your flows.") \
                .classes("text-sm opacity-80")
            self._sections(self._library.sections())

    def _sections(self, sections: list[str]) -> None:
        topics = self._library.topics()
        for section in sections:
            with ui.row().classes("items-center gap-2 mt-2"):
                ui.icon(SECTION_ICONS.get(section, "menu_book")).classes("text-xl text-primary")
                ui.label(section).classes("text-lg font-semibold")
            with ui.element("div").classes("grid gap-3 w-full sm:grid-cols-2 xl:grid-cols-3 items-stretch"):
                for topic in (t for t in topics if t.section == section):
                    with ui.link(target=f"/learn?show={topic.id}").classes("no-underline text-inherit"), \
                            ui.card().classes("w-full h-full gap-1 cursor-pointer hover:bg-gray-500/10"):
                        with ui.row().classes("items-center no-wrap gap-2 w-full"):
                            ui.label(topic.title).classes("font-semibold flex-1")
                            if topic.flows is not None:
                                ui.icon("account_tree").classes("opacity-60").tooltip("Has an example flow")
                        ui.label(self._first_line(topic)).classes("text-xs opacity-70")

    def _topic(self, topic: LearnTopic) -> None:
        ui.link(f"← {topic.section}", f"/learn?show={quote(topic.section, safe='')}").classes("text-sm")
        with ui.card().classes("w-full max-w-3xl gap-2"):
            ui.label(topic.title).classes("text-lg font-semibold")
            ui.markdown(topic.text, extras=["tables", "fenced-code-blocks"]).classes("tb-learn w-full")
            if topic.flows is not None:
                self._add_button(topic)

    def _add_button(self, topic: LearnTopic) -> None:
        labels = [f.label for f in FlowPack.from_text(topic.flows.read_text(encoding="utf-8")).flows]

        def add() -> None:
            added, _there = self._default_flows.add(topic.flows, EXAMPLES)
            if added:
                ui.notify(f'Added to "{EXAMPLES}" (off): ' + ", ".join(added), type="positive")
            else:
                ui.notify(f'It is in "{EXAMPLES}" already', type="info")
            link.set_visibility(True)

        ui.separator()
        with ui.row().classes("items-center gap-3"):
            ui.button("Add to my flows", icon="playlist_add", on_click=add).props("no-caps unelevated")
            link = ui.link(f"Open {EXAMPLES}", f"/flows?show={quote(EXAMPLES, safe='')}").classes("text-sm")
            link.set_visibility(False)
        ui.label(f'A copy of "{", ".join(labels)}" in the folder {EXAMPLES}, switched off: change it, then switch '
                 "it on.").classes("text-xs opacity-60")

    @staticmethod
    def _first_line(topic: LearnTopic) -> str:
        """The page's first sentence, for its card."""
        line = topic.text.split("\n\n", 1)[0].replace("\n", " ").replace("**", "").replace("`", "")
        line = line.removeprefix("What it does: ")
        return line[:1].upper() + line[1:]
