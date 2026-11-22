import logging
from typing import Any

from streamer_toolbox.core.flows.current_box import current_box
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.media.media_buffer import MediaBuffer

log = logging.getLogger(__name__)


class KeepMediaLocally(Box):
    """A picture or video from the web, kept on this PC (MediaBuffer; his idea of 11-14), e.g. Twitch profile
    picture → this box → Send chat with its address. In a flow the address is the box's own (his 11-15):
    /toolbox/media/flows/box/<flow>/<box id>/<file>, and .../latest.png is the newest it kept. It downloads (it
    keeps its run wire, rule 22). When it can't
    keep the file, the web address goes on as it is (the overlay still shows it) and the log says why: one
    viewer's picture never stops a chat message."""

    name = "keep_locally"
    label = "Keep media locally"
    help = ("Downloads a picture or video once and keeps it on this PC; overlays then load it from the toolbox. "
            "If that doesn't work, the web address goes on as it is")
    outputs = {"address": "text", "file": "text", "kept": "yes_no"}
    group = "Media"
    labels = {"url": "Web address", "name": "File name", "folder": "Folder", "max_mb": "Folder size (MB)",
              "file_mb": "Biggest file (MB)", "days": "Keep for (days)"}
    hints = {"url": "A picture or video on the internet (http / https). Empty = nothing to keep, empty out",
             "name": "Optional, after the file's code: the chatter's login gives 3f2a…_kit.png. Letters, digits and -",
             "folder": "Empty = this box's own folder. Boxes with the same name share the files and the sizes "
                       "(a picture used in several flows is downloaded once)",
             "max_mb": "When the folder is fuller, the files unused the longest go",
             "file_mb": "A bigger file isn't kept (its web address goes on)",
             "days": "Then it is downloaded again the next time; one nobody asked for in that many days goes. "
                     "0 = as long as there is room"}

    def __init__(self, buffer: MediaBuffer) -> None:
        self._buffer = buffer

    async def run(self, url: str, name: str = "", folder: str = "", max_mb: float = 500, file_mb: float = 20,
                  days: float = 0) -> dict[str, Any]:
        url = str(url or "").strip()
        if not url:
            return {"address": "", "file": "", "kept": False}
        try:
            kept = await self._buffer.keep(url, folder, float(max_mb), float(file_mb), float(days), str(name or ""),
                                           current_box.get())
        except Exception as e:  # noqa: BLE001 - the web address still works
            log.warning("Keep media locally: %s not kept (%s)", url[:120], e)
            return {"address": url, "file": "", "kept": False}
        return {"address": kept.address, "file": str(kept.file), "kept": True}
