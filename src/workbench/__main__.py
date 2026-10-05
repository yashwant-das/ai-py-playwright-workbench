"""Starts the workbench on 127.0.0.1 and opens it in the default browser."""

import logging
import threading
import webbrowser

import uvicorn

from workbench import config
from workbench.app import create_app


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
    uvicorn.run(create_app(port=port), host=config.HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
