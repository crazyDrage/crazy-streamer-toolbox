from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from streamer_toolbox.core.media.media_buffer import BOX_PLACE, ROUTE, SHARED_PLACE, MediaBuffer


def build_media_router(buffer: MediaBuffer) -> APIRouter:
    """Files the media buffer keeps (box "Keep media locally"), for overlays and OBS (his 11-15: a box's own
    address): GET /toolbox/media/flows/box/<flow>/<box id>/<file> and /toolbox/media/shared/<folder>/<file>;
    <file> = latest.png gives the newest. Only files of a folder's index; nothing is downloaded on a request.
    The file is only shown, never run (sandbox, nosniff), and an overlay may keep it a day (latest: never)."""
    router = APIRouter()

    def answer(path: Path | None, file: str) -> FileResponse:
        if path is None:
            raise HTTPException(status_code=404, detail="the toolbox keeps no such file")
        cache = "no-cache" if file.startswith("latest") else "max-age=86400"
        return FileResponse(path, headers={"Cache-Control": cache, "X-Content-Type-Options": "nosniff",
                                           "Content-Security-Policy": "sandbox"})

    @router.get(f"{ROUTE}/{BOX_PLACE}/{{flow}}/{{box}}/{{file}}")
    def of_box(flow: str, box: str, file: str) -> FileResponse:
        return answer(buffer.find_for_box(flow, box, file), file)

    @router.get(f"{ROUTE}/{SHARED_PLACE}/{{folder}}/{{file}}")
    def shared(folder: str, file: str) -> FileResponse:
        return answer(buffer.find_shared(folder, file), file)

    return router
