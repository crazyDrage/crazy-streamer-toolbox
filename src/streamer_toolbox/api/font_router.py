from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from streamer_toolbox.core.fonts.font_library import CSS, ROUTE, FontLibrary

MEDIA = {".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2"}
# a widget's page has no identity of its own (WidgetSafety sandbox): its font requests count as from another
# site, which a browser only allows with this header
ANY_PAGE = {"Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff"}


def build_font_router(library: FontLibrary) -> APIRouter:
    """The fonts the toolbox hosts (his 11-18: "every font loads it from the endpoint"): GET /toolbox/fonts/fonts.css
    (@font-face for each) and the files at /toolbox/fonts/file/<name>, for OBS, the phone and the toolbox's own
    pages alike. Fonts of this machine only aren't here: the browser on this PC finds them by name."""
    router = APIRouter()

    @router.get(CSS)
    def css() -> Response:
        return Response(library.css(), media_type="text/css", headers={**ANY_PAGE, "Cache-Control": "no-cache"})

    @router.get(f"{ROUTE}/file/{{name}}")
    def file(name: str) -> FileResponse:
        path = library.file(name)
        if path is None:
            raise HTTPException(status_code=404, detail="the toolbox hosts no such font")
        return FileResponse(path, media_type=MEDIA[path.suffix.casefold()],
                            headers={**ANY_PAGE, "Cache-Control": "max-age=86400"})

    return router
