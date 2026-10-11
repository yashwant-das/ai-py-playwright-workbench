"""Starts the app for the UI suite (tests/ui/*.spec.ts).

Unlike ``uv run workbench`` it opens no browser tab and never looks for a model
server on this machine, so the suite behaves the same on every computer. It can
also prepare the workspace before the app starts:

    WORKBENCH_WORKSPACE=/tmp/ui uv run python -m tests.ui.serve --port 7901 --seed
"""

import argparse
import json
from contextlib import ExitStack
from dataclasses import replace

from tests.integration.fake_llm import FakeLLM
from tests.unit.report_fixtures import write_all
from workbench import config
from workbench.__main__ import build_server
from workbench.app import create_app
from workbench.models.generate import GenerateReport
from workbench.models.settings import DEMO_MODEL, ModelSettings
from workbench.reports import load_report, save_report
from workbench.samples import BASE_URL_PLACEHOLDER
from workbench.settings import save_settings
from workbench.web.services import Services

# Nothing listens on the discard port, so this server is always down.
DOWN_URL = "http://127.0.0.1:9/v1"
SEEDED_FILE = "seeded.json"


def seed_reports(port: int) -> None:
    """Save one report per result state and list their ids in ``seeded.json``."""
    ids = write_all()
    # "Heal this test" needs the failed spec on disk, broken the way Demo can heal.
    failed = load_report(ids["generate_failed"])
    assert isinstance(failed, GenerateReport)
    source = (config.SAMPLE_SPECS_DIR / "contact-form.spec.ts").read_text(
        encoding="utf-8"
    )
    code = source.replace(BASE_URL_PLACEHOLDER, f"{config.base_url(port)}/sample-site/")
    (config.specs_dir() / failed.spec_name).write_text(code, encoding="utf-8")
    save_report(failed.model_copy(update={"code": code}))
    (config.workspace_dir() / SEEDED_FILE).write_text(json.dumps(ids), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the app for the UI suite.")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--model", choices=["none", "demo", "unreachable", "fake"], default="demo"
    )
    parser.add_argument("--no-browsers", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()

    services = replace(Services(), detect=lambda: None)
    if args.no_browsers:
        services = replace(services, browsers_ready=lambda: False)
    with ExitStack() as stack:
        if args.model == "demo":
            save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))
        elif args.model == "unreachable":
            save_settings(
                ModelSettings(
                    provider="ollama", base_url=DOWN_URL, model="missing-model"
                )
            )
        elif args.model == "fake":
            llm = stack.enter_context(FakeLLM())
            save_settings(
                ModelSettings(
                    provider="lm_studio", base_url=llm.base_url, model="fake-model"
                )
            )
        if args.seed:
            seed_reports(args.port)
        build_server(create_app(services, port=args.port), args.port).run()


if __name__ == "__main__":
    main()
