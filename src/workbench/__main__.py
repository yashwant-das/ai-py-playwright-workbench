"""Starts the workbench on 127.0.0.1 and opens it in the default browser."""

import contextlib
import logging
import socket
import threading
import webbrowser

import uvicorn
from fastapi import FastAPI

from workbench import config
from workbench.app import create_app
from workbench.runs import RunRegistry

# Ctrl+C must stop the app even if a connection never closes.
SHUTDOWN_TIMEOUT_S = 10


class Server(uvicorn.Server):
    """A server that cancels the active run as soon as it is told to stop.

    uvicorn calls the app's own shutdown hook only after every connection has
    closed, and a run's live stream stays open until the run ends. Without
    this, Ctrl+C during a run would wait for the whole timeout.
    """

    def __init__(self, config: uvicorn.Config, runs: RunRegistry) -> None:
        super().__init__(config)
        self._runs = runs

    async def shutdown(self, sockets: list[socket.socket] | None = None) -> None:
        self._runs.stop()
        await super().shutdown(sockets=sockets)


def build_server(app: FastAPI, port: int) -> Server:
    return Server(
        uvicorn.Config(
            app,
            host=config.HOST,
            port=port,
            log_level="warning",
            timeout_graceful_shutdown=SHUTDOWN_TIMEOUT_S,
        ),
        app.state.runs,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    try:
        port = config.port()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    url = f"{config.base_url(port)}/"
    print(f"Playwright Workbench is running at {url} (press Ctrl+C to stop)")
    threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    # After a clean stop uvicorn raises the Ctrl+C it caught: that is not an error.
    with contextlib.suppress(KeyboardInterrupt):
        build_server(create_app(port=port), port).run()


if __name__ == "__main__":
    main()
