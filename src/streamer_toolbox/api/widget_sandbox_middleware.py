import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

# what a widget's page asks the toolbox for while it runs: its own store, stand-in, media and field files
OWN_ROUTES = re.compile(r"/overlay/widget/[^/]+/(store|streamelements|media|file)/")
NOWHERE = "null"  # the Origin a sandboxed page sends: it has no identity of its own


class WidgetSandboxMiddleware(BaseHTTPMiddleware):
    """Lets a sandboxed widget page (WidgetSafety.sandbox) still reach its own routes, and nobody else's page
    reach them. A sandboxed page counts as "another site" for the browser, which then only hands it answers
    that say so (CORS): these routes answer with that permission for Origin "null". A request that comes from
    a real other site (a web page open in his browser that guesses the address) is refused. Requests without
    an Origin (OBS loading a picture, the toolbox's own pages) pass as before."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not OWN_ROUTES.match(request.url.path):
            return await call_next(request)
        origin = request.headers.get("origin")
        own = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin and origin not in (NOWHERE, own):
            return PlainTextResponse("a widget's routes are for its own page", status_code=403)
        allow = {"Access-Control-Allow-Origin": NOWHERE, "Vary": "Origin"} if origin == NOWHERE else {}
        if request.method == "OPTIONS" and origin == NOWHERE:  # the browser asks first before a PUT with JSON
            return Response(status_code=204, headers={**allow, "Access-Control-Allow-Methods": "GET, PUT",
                                                      "Access-Control-Allow-Headers": "content-type",
                                                      "Access-Control-Max-Age": "600"})
        response = await call_next(request)
        response.headers.update(allow)
        return response
