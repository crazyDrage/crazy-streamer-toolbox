from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.widgets.element_design import ElementDesign


@dataclass(frozen=True)
class DesignPreset:
    """One thing in the widget editor's add list (his round 85: "the items to add should be on the left side in a
    list; we should try to support as much as possible there"): a kind of piece (ElementDesign.KINDS), set up
    for one job, e.g. a text that says the latest follower or a goal bar for subs. `where`: "" anywhere,
    "alert" only in an alert layer (its event's values)."""

    group: str
    title: str
    icon: str
    kind: str
    where: str = ""
    text: str = ""
    goal: dict[str, Any] = field(default_factory=dict)
    ticker: str = ""
    style: dict[str, Any] = field(default_factory=dict)
    size: tuple[float, ...] = ()  # width, height

    def fits(self, alert: bool) -> bool:
        return not self.where or alert

    def add_to(self, design: ElementDesign, layer: int) -> str:
        """The piece, in the middle of the canvas; its name: the preset's title, with 2, 3, ... when it is taken."""
        taken = set(design.pieces(layer))
        name = design.add(layer, self.kind)
        wanted, number = self.title, 2
        while wanted in taken:
            wanted, number = f"{self.title} {number}", number + 1
        if self.text:
            design.set_text(layer, name, self.text)
        if self.goal:
            design.set_goal(layer, name, **self.goal)
        if self.ticker:
            design.set_ticker(layer, name, kind=self.ticker)
        if self.size:
            design.resize(layer, name, self.size[0], height=self.size[1])
        if self.style:
            design.set_style(layer, name, **self.style)
        return design.rename(layer, name, wanted)


def _value(title: str, words: str, code: str) -> DesignPreset:
    return DesignPreset("Live values", title, "bolt", "text", "", f"{words}{{session.twitch.{code}}}")


def _goal(title: str, value: str) -> DesignPreset:
    return DesignPreset("Goal bars", title, "flag", "goal", goal={"value": value, "label": f"{title}: {{value}} / "
                                                                                         "{target}"})


PRESETS = (
    DesignPreset("Pieces", "Text", "title", "text"),
    DesignPreset("Pieces", "Picture or GIF", "image", "image"),
    DesignPreset("Pieces", "Video", "movie", "video"),
    DesignPreset("Pieces", "Sound", "volume_up", "audio", "alert"),
    DesignPreset("Pieces", "Shape", "crop_square", "shape"),
    DesignPreset("Pieces", "Circle", "circle", "shape", size=(200, 200), style={"borderRadius": "50%"}),
    DesignPreset("Pieces", "Line", "horizontal_rule", "shape", size=(600, 6), style={"borderRadius": "3px"}),
    DesignPreset("This alert", "Their name", "person", "text", "alert", "{event.data.username}"),
    DesignPreset("This alert", "Amount", "tag", "text", "alert", "{event.data.amount}"),
    DesignPreset("This alert", "Their message", "chat", "text", "alert", "{event.data.message}",
                 style={"fontSize": "32px", "fontWeight": "normal"}),
    _value("Latest follower", "Latest follower: ", "follower-latest.name"),
    _value("Latest sub", "Latest sub: ", "subscriber-latest.name"),
    DesignPreset("Live values", "Latest cheer", "bolt", "text", "",
                 "Latest cheer: {session.twitch.cheer-latest.name} ({session.twitch.cheer-latest.amount} bits)"),
    DesignPreset("Live values", "Latest raid", "bolt", "text", "",
                 "Latest raid: {session.twitch.raid-latest.name} ({session.twitch.raid-latest.amount})"),
    DesignPreset("Live values", "Latest tip", "bolt", "text", "",
                 "Latest tip: {session.twitch.tip-latest.name} ({session.twitch.tip-latest.amount})"),
    _value("Followers this stream", "Followers today: ", "follower-session.count"),
    _value("Subs this stream", "Subs today: ", "subscriber-session.count"),
    _value("Top cheerer", "Top cheerer: ", "cheer-session-top-donator.name"),
    _value("Followers in all", "Followers: ", "follower-total.count"),
    _goal("Follower goal", "follower-session.count"),
    _goal("Sub goal", "subscriber-session.count"),
    _goal("Bit goal", "cheer-session.amount"),
    _goal("Tip goal", "tip-session.amount"),
    _goal("Follower goal this month", "follower-month.count"),
    DesignPreset("Recent names", "Recent followers", "view_carousel", "latestTicker", ticker="follower"),
    DesignPreset("Recent names", "Recent subs", "view_carousel", "latestTicker", ticker="subscriber"),
    DesignPreset("Recent names", "Recent cheers", "view_carousel", "latestTicker", ticker="cheer"),
    DesignPreset("Recent names", "Recent raiders", "view_carousel", "latestTicker", ticker="raid"),
    DesignPreset("Recent names", "Recent tips", "view_carousel", "latestTicker", ticker="tip"),
)
