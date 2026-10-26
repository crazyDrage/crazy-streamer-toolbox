from typing import Any

import httpx

from streamer_toolbox.connections.twitch.boxes.twitch_clip_box import BEST, QUALITIES, QUALITY_PICKER, TwitchClipBox
from streamer_toolbox.connections.twitch.twitch_clip_files import clip_id
from streamer_toolbox.core.data.box_value import to_bool


class ClipVideoAddress(TwitchClipBox):
    name = "clip_address"
    label = "Clip video address"
    help = "Where a clip's video is, so Play video once can play it straight from Twitch: no download, and no " \
           "content warning page. Ask right before playing (the address is good for some hours). Uses the way " \
           "Twitch's own player asks, which Twitch may change"
    group = "Stream"
    options = {"quality": QUALITY_PICKER}
    labels = {"finder": "Question finder", "fail_on_error": "Fail when there is none"}
    hints = {"clip": "a clip's id (Get clips gives it) or its link",
             "quality": "the best there is at or below this",
             "finder": "only used when Twitch refuses the ways the toolbox knows: it then reads from Twitch's own "
                       "clip player how to ask now (slower that one time: a few MB; kept for a week). Off: the box "
                       "fails instead",
             "fail_on_error": "Off: when Twitch gives no address, the box gives found = false (and why in problem) "
                              "instead of failing, so an If can take another way, e.g. Download clip"}
    outputs = {"address": "text", "quality": "number", "id": "text", "found": "yes/no", "problem": "text"}

    async def run(self, clip: str, quality: str = BEST, finder: bool = True,
                  fail_on_error: bool = True) -> dict[str, Any]:
        try:
            files = await self._files.files(clip, to_bool(finder))
        except (RuntimeError, httpx.HTTPError, OSError) as e:
            if to_bool(fail_on_error):
                raise
            return {"address": "", "quality": 0, "id": clip_id(clip), "found": False, "problem": str(e)}
        wanted = str(quality).strip().casefold().removesuffix("p")
        if wanted not in ("", BEST):
            if not wanted.isdigit():
                raise ValueError(f"quality is {', '.join(QUALITIES)}, not {quality!r}")
            # the best at or below what was asked for; a clip that only has better ones gives its smallest
            files = [one for one in files if one["quality"] <= int(wanted)] or files[-1:]
        return {"address": files[0]["address"], "quality": files[0]["quality"], "id": clip_id(clip),
                "found": True, "problem": ""}
