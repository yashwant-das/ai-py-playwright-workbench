"""Everything the web app calls outside itself, in one place tests can replace."""

from collections.abc import Callable
from dataclasses import dataclass

from workbench.environment import chromium_installed
from workbench.generate import generate
from workbench.heal import heal
from workbench.llm import build_model, check_connection, detect_provider
from workbench.llm.chat import ChatModel
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport
from workbench.models.settings import ConnectionStatus, ModelSettings
from workbench.models.shared import RunResult
from workbench.runner import run_test


@dataclass(frozen=True)
class Services:
    """The pipelines, model client and checks the routes use."""

    heal: Callable[..., HealReport] = heal
    generate: Callable[..., GenerateReport] = generate
    run_test: Callable[..., RunResult] = run_test
    build_model: Callable[[ModelSettings], ChatModel] = build_model
    detect: Callable[[], ModelSettings | None] = detect_provider
    check_connection: Callable[..., ConnectionStatus] = check_connection
    browsers_ready: Callable[[], bool] = chromium_installed
