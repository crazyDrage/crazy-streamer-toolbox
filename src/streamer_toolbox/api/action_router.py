
import inspect
import json
import logging
from collections.abc import Callable
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.action_description import describe_action
from streamer_toolbox.api.caller import Caller
from streamer_toolbox.api.caller_auth import CallerAuth


RunListener = Callable[[str, str, bool, Any], None]  # caller name, action, ok, result or error

log = logging.getLogger(__name__)


def build_action_router(actions: ActionRegistry, auth: CallerAuth,
                        on_run: Optional[RunListener] = None) -> APIRouter:
    """HTTP entry point for SAMMI and Kit: POST /action/<name> with optional JSON params.

    Every request needs a known caller (token in `Authorization: Bearer ...` or `X-Toolbox-Token`, or a
    local caller from this PC), and the caller only sees and runs the actions its allowlist names.
    """

    def caller(request: Request, authorization: Optional[str] = Header(default=None),
               x_toolbox_token: Optional[str] = Header(default=None),
               origin: Optional[str] = Header(default=None)) -> Caller:
        token = x_toolbox_token
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        if not token and origin:
            # a web page in the streamer's browser could otherwise use the local caller (CSRF);
            # SAMMI and Kit send no Origin, browsers always do on cross-site POSTs
            raise HTTPException(status_code=403, detail="browser requests need a token")
        found = auth.identify(token, request.client.host if request.client else None)
        if found is None:
            raise HTTPException(status_code=401, detail="unknown caller")
        return found

    router = APIRouter()

    @router.get("/actions")
    def list_actions(who: Caller = Depends(caller)) -> list[dict[str, Any]]:
        return [describe_action(a) for a in actions.all() if who.may_run(a.name)]

    @router.post("/action/{name}")
    async def run_action(name: str, request: Request, who: Caller = Depends(caller)) -> dict[str, Any]:
        # same answer for "unknown" and "not allowed", so callers can't probe for action names
        if name not in actions or not who.may_run(name):
            raise HTTPException(status_code=404, detail=f"unknown action {name}")
        params = _json_params(await request.body())
        try:
            inspect.signature(actions.get(name).handler).bind(**params)
        except TypeError as e:
            raise HTTPException(status_code=422, detail=f"bad parameters for {name}: {e}")
        try:
            result = await actions.run(name, **params)
        except Exception as e:
            # a clean answer instead of a server crash trace; SAMMI keeps the body in its result variable
            if on_run:
                on_run(who.name, name, False, e)
            log.warning("action %s from %s failed: %s", name, who.name, e)
            return JSONResponse(status_code=500, content={"action": name, "error": str(e)})
        if on_run:
            on_run(who.name, name, True, result)
        return {"action": name, "result": result}

    return router


def _json_params(body: bytes) -> dict[str, Any]:
    # read as JSON whatever the Content-Type says: SAMMI's HTTP Request doesn't let us choose it
    if not body.strip():
        return {}
    try:
        params = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=422, detail="body must be a JSON object")
    if not isinstance(params, dict):
        raise HTTPException(status_code=422, detail="body must be a JSON object")
    return params
