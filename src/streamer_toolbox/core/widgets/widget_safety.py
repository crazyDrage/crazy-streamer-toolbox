import re
from dataclasses import dataclass
from typing import Any

from streamer_toolbox.core.widgets.widget import Widget

HOST = re.compile(r"(?:(?:https?|wss?):)?//([a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,})(?![\w.-])", re.IGNORECASE)
HOST_NAME = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}")
OWN = "streamelements.com"  # these addresses become the toolbox's own stand-in on the page (streamelements_links)
# a host a widget names → hosts that one sends the page on to
IMPLIED = {"fonts.googleapis.com": ("fonts.gstatic.com",)}
# Twitch itself: chat widgets read chat and load emotes and badges from it, often through a helper library, so
# the widget's own code doesn't name these (seen: twitch-js connecting to irc-ws.chat.twitch.tv)
ALWAYS = ("twitch.tv", "jtvnw.net")
MODES = {"block": "Block every other host", "report": "Only note other hosts", "off": "Allow every host"}


@dataclass(frozen=True)
class WidgetSafety:
    """What a widget's page may do, kept per widget (config/widgets/<name>/safety.json). A widget is someone
    else's code; two fences keep it to itself (docs/PLAN_widget_protection.md):

    - `sandbox`: the page has no identity of its own (as on StreamElements), so its code can't read the
      toolbox's own pages or other widgets; it still reaches its own routes. Browser storage (localStorage,
      cookies) isn't there for it.
    - `hosts`: where the page may load from and send to. "block" = only this toolbox and the allowed hosts,
      "report" = everything works but other hosts are noted, "off" = no list. Allowed = Twitch (ALWAYS), the
      hosts the widget's code names (those in `blocked` taken out) and the ones in `extra`, each with its
      subdomains. A host the
      code doesn't name (one a helper script made up later) is stopped, and noted so he can allow it."""

    sandbox: bool = True
    hosts: str = "block"
    blocked: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WidgetSafety":
        return cls(bool(data.get("sandbox", True)), data.get("hosts") if data.get("hosts") in MODES else "block",
                   _hosts(data.get("blocked")), _hosts(data.get("extra")))

    def to_dict(self) -> dict[str, Any]:
        return {"sandbox": self.sandbox, "hosts": self.hosts, "blocked": list(self.blocked),
                "extra": list(self.extra)}

    @staticmethod
    def named(widget: Widget) -> list[str]:
        """The hosts the widget's code names, sorted (StreamElements' aren't in it: the page has the toolbox's
        stand-in instead)."""
        code = "\n".join((widget.html, widget.css, widget.js, *(str(v) for v in widget.values.values())))
        found = {host.casefold() for host in HOST.findall(code)}
        return sorted(host for host in found if host != OWN and not host.endswith("." + OWN))

    def allowed(self, widget: Widget) -> list[str]:
        named = [host for host in self.named(widget) if host not in self.blocked]
        implied = [more for host in named for more in IMPLIED.get(host, ())]
        return sorted({*ALWAYS, *named, *implied, *self.extra})

    def headers(self, widget: Widget, own: str, also: tuple[str, ...] = ()) -> dict[str, str]:
        """The response headers that put the fences up. own: the toolbox's address as the page was asked for
        (http://127.0.0.1:8850); also: hosts allowed besides (StreamElements, with the fallback switched on)."""
        headers = {}
        if self.sandbox:
            headers["Content-Security-Policy"] = "sandbox allow-scripts"
        if self.hosts != "off":
            sources = [own, own.replace("http", "ws", 1)]
            for host in sorted({*self.allowed(widget), *also}):
                sources += [host, f"*.{host}", f"wss://{host}", f"wss://*.{host}"]
            policy = (f"default-src {' '.join(sources)} data: blob: 'unsafe-inline' 'unsafe-eval'; "
                      f"report-uri /overlay/widget/{widget.name}/blocked")
            if self.hosts == "report":
                headers["Content-Security-Policy-Report-Only"] = policy
            else:
                headers["Content-Security-Policy"] = "; ".join(filter(None, (
                    headers.get("Content-Security-Policy"), policy)))
        return headers

    def frame_sandbox(self) -> str:
        """The sandbox of the frame the shell page holds the widget in. Without the first fence the page keeps
        its identity; it still can't open windows or send the shell elsewhere."""
        return "allow-scripts" if self.sandbox else "allow-scripts allow-same-origin"

    @staticmethod
    def shell_headers(name: str, own: str) -> dict[str, str]:
        """The headers of the shell page (the address OBS opens; WidgetPage.shell). A browser's fences don't
        stop a page from sending itself to another site, but the page around a frame decides where that frame
        may go: only to this widget's own page. Always on, whatever the widget's own fences are set to; a try
        is told to .../blocked like the rest."""
        return {"Content-Security-Policy": f"default-src 'none'; style-src 'unsafe-inline'; "
                                           f"frame-src {own}/overlay/widget/{name}/page; "
                                           f"report-uri /overlay/widget/{name}/blocked"}


def host_of(address: str) -> str:
    """The host of an address a browser reported as blocked ("" for inline code and the like)."""
    found = HOST.match(address if "//" in address else "//" + address)
    return found.group(1).casefold() if found else ""


def _hosts(given: Any) -> tuple[str, ...]:
    names = {str(host).strip().casefold() for host in (given if isinstance(given, (list, tuple)) else [])}
    return tuple(sorted(host for host in names if HOST_NAME.fullmatch(host)))
