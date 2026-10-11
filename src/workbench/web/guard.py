"""Refuses requests that do not come from the app's own pages on this machine.

The app runs specs, and a spec is code. A page on another site must not be
able to post to the app, and another host name must not be able to read it
(DNS rebinding). Every request passes through here before any route.
"""

import re

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_OWN_HOST = re.compile(r"(?:127\.0\.0\.1|localhost)(?::[0-9]{1,5})?")
_READ_ONLY = frozenset({"GET", "HEAD", "OPTIONS"})
_OWN_FETCH_SITES = frozenset({"same-origin", "none"})


def _refusal(scope: Scope) -> PlainTextResponse | None:
    headers = Headers(scope=scope)
    hosts = headers.getlist("host")
    if len(hosts) != 1 or not _OWN_HOST.fullmatch(hosts[0]):
        return PlainTextResponse(
            "This app only answers requests addressed to 127.0.0.1 or localhost.",
            status_code=400,
        )
    if scope.get("method") in _READ_ONLY:  # a WebSocket has no method: checked
        return None
    origins = headers.getlist("origin")
    if origins:
        # Browsers send Origin on every cross-site request that is not a GET.
        allowed = origins == [f"http://{hosts[0]}"]
    else:
        # No Origin: a tool on this machine, unless the browser says otherwise.
        allowed = all(
            site in _OWN_FETCH_SITES for site in headers.getlist("sec-fetch-site")
        )
    if allowed:
        return None
    return PlainTextResponse(
        "This app does not accept requests from other sites.", status_code=403
    )


class RequestGuard:
    """ASGI middleware: 400 for another host name, 403 for another site's request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            refusal = _refusal(scope)
            if refusal is not None:
                await refusal(scope, receive, send)
                return
        await self.app(scope, receive, send)
