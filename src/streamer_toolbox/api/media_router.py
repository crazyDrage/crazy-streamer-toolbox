from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from streamer_toolbox.core.media.media_buffer import ROUTE, MediaBuffer


def build_media_router(buffer: MediaBuffer) -> APIRouter:
    """GET /media/kept/<folder>/<file>: a file the media buffer keeps (box "Keep media locally"), for overlays
    and OBS. Only files of that folder's index; nothing is downloaded on a request. The file is only shown,
    never run (sandbox, nosniff), and an overlay may keep it a day."""
    router = APIRouter()

    @router.get(ROUTE + "/{folder}/{file}")
    def kept(folder: str, file: str) -> FileResponse:
        path = buffer.find(folder, file)
        if path is None:
            raise HTTPException(status_code=404, detail="the toolbox keeps no such file")
        return FileResponse(path, headers={"Cache-Control": "max-age=86400", "X-Content-Type-Options": "nosniff",
                                           "Content-Security-Policy": "sandbox"})

    return router
