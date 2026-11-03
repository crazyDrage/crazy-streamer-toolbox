import logging
import tomllib
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.learn.learn_topic import LearnTopic

HEAD = "+++"  # a page starts with its settings between two such lines: title, section, order (TOML)
SECTIONS = ("First steps", "Examples")  # in this order; a section not named here comes after them, A-Z
TOPICS = Path(__file__).parent / "topics"  # the toolbox's own pages

log = logging.getLogger(__name__)


class LearnLibrary:
    """The Learn tab's pages (his round 66: "a tab only to help building flows, alerts and other stuff. To teach
    and understand how this toolbox works, and prepare simple flows for everyone to use"). Each page is a
    Markdown file `<id>.md` in a folder; its example flow, if it has one, is `<id>.flows.toml` next to it. Files
    are read every time, so a changed page shows on the next click."""

    def __init__(self, folders: list[Path] | None = None, more: Callable[[], list[Path]] = lambda: []) -> None:
        """more: folders asked for at every read (the plugins' that are on, ctx.add_learn_folder)."""
        self._folders = folders if folders is not None else [TOPICS]
        self._more = more

    @property
    def folders(self) -> list[Path]:
        return [*self._folders, *self._more()]

    def topics(self) -> list[LearnTopic]:
        """Every page, by section, then order, then title."""
        found = [t for folder in self.folders if folder.is_dir()
                 for t in (self._read(f) for f in sorted(folder.glob("*.md"))) if t is not None]
        return sorted(found, key=lambda t: (self.section_rank(t.section), t.order, t.title.casefold()))

    def sections(self) -> list[str]:
        return list(dict.fromkeys(t.section for t in self.topics()))

    def get(self, topic_id: str) -> LearnTopic | None:
        return next((t for t in self.topics() if t.id == topic_id), None)

    @staticmethod
    def section_rank(section: str) -> tuple[int, str]:
        return (SECTIONS.index(section), "") if section in SECTIONS else (len(SECTIONS), section.casefold())

    @staticmethod
    def _read(file: Path) -> LearnTopic | None:
        text = file.read_text(encoding="utf-8")
        head: dict = {}
        if text.startswith(HEAD):
            settings, _, text = text[len(HEAD):].partition(HEAD)
            try:
                head = tomllib.loads(settings)
            except tomllib.TOMLDecodeError as e:
                log.warning("Learn page %s: its settings can't be read (%s)", file.name, e)
                return None
        flows = file.with_name(f"{file.stem}.flows.toml")
        return LearnTopic(file.stem, str(head.get("title", file.stem.replace("_", " ").capitalize())),
                          str(head.get("section", "More")), text.strip(), int(head.get("order", 0)),
                          flows if flows.is_file() else None)
