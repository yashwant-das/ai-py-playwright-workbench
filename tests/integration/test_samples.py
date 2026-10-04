"""S1, S2 and S4 at pipeline level, against a real Chromium.

S1  a fresh workspace with no model server heals the sample through Demo
S2  a running OpenAI-compatible server is found and used with no configuration
S4  the app-bug sample stops the heal without editing the test
"""

from tests.integration.fake_llm import FakeLLM
from workbench.generate import GenerateRequest, generate
from workbench.heal import HealRequest, heal
from workbench.llm import DemoModel, build_model, check_connection, detect_provider
from workbench.models.settings import DEMO_MODEL, ModelSettings
from workbench.reports import load_report
from workbench.samples import GENERATE_SCENARIO, SAMPLES, install_sample
from workbench.settings import load_settings, resolve_settings, save_settings

UNREACHABLE = "http://127.0.0.1:9/v1"  # nothing listens on the discard port
NO_SERVERS = {"lm_studio": UNREACHABLE, "ollama": UNREACHABLE}


def test_first_launch_without_a_server_heals_the_sample_with_demo(site: str) -> None:
    assert load_settings() is None
    assert resolve_settings(detect=lambda: detect_provider(urls=NO_SERVERS)) is None

    choice = ModelSettings(provider="demo", model=DEMO_MODEL)
    save_settings(choice)
    assert load_settings() == choice

    spec = install_sample("selector-drift", site)
    report = heal(HealRequest(spec_path=spec), model=build_model(choice))

    assert report.status == SAMPLES["selector-drift"].expected_status, (
        report.model_dump_json(indent=2)
    )
    exchange = report.attempts[0].exchange
    assert exchange is not None and exchange.provenance.provider == "demo"
    assert "#submit-btn" not in spec.read_text(encoding="utf-8")
    assert load_report(report.id).status == "healed"


def test_app_bug_sample_stops_without_editing_the_test(site: str) -> None:
    spec = install_sample("app-bug", site)
    original = spec.read_bytes()

    report = heal(HealRequest(spec_path=spec), model=DemoModel())

    assert report.status == SAMPLES["app-bug"].expected_status, report.model_dump_json(
        indent=2
    )
    assert [a.outcome for a in report.attempts] == ["app_defect"]
    assert report.attempts[0].rerun is None
    assert spec.read_bytes() == original


def test_demo_generates_a_passing_spec_for_the_sample_scenario(site: str) -> None:
    report = generate(
        GenerateRequest(url=site, scenario=GENERATE_SCENARIO), model=DemoModel()
    )

    assert report.status == "passed", report.model_dump_json(indent=2)
    assert site in report.code


def test_a_running_server_is_detected_and_used(site: str) -> None:
    with FakeLLM() as llm:
        choice = detect_provider(
            urls={"lm_studio": UNREACHABLE, "ollama": llm.base_url}
        )
        assert choice == ModelSettings(
            provider="ollama", base_url=llm.base_url, model="fake-model"
        )

        status = check_connection(choice)
        assert status.reachable and status.models == ["fake-model"]

        report = generate(
            GenerateRequest(url=site, scenario="A user can submit the contact form"),
            model=build_model(choice),
        )

    assert report.status == "passed", report.model_dump_json(indent=2)
    assert report.exchange is not None
    assert report.exchange.provenance.provider == "ollama"
