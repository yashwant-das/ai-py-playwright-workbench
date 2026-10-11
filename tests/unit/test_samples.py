"""The bundled samples and the copies the workbench runs."""

from pathlib import Path

import pytest

from workbench import config
from workbench.samples import BASE_URL_PLACEHOLDER, SAMPLES, install_sample
from workbench.validation import ValidationError


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))


def test_every_sample_spec_exists_and_has_the_placeholder() -> None:
    assert set(SAMPLES) == {"selector-drift", "app-bug"}
    for sample in SAMPLES.values():
        source = (config.SAMPLE_SPECS_DIR / sample.spec_file).read_text(
            encoding="utf-8"
        )
        assert BASE_URL_PLACEHOLDER in source


def test_sample_site_pages_exist() -> None:
    for page in ("index.html", "checkout.html", "style.css"):
        assert (config.SAMPLE_SITE_DIR / page).is_file()


def test_install_fills_in_the_base_url() -> None:
    path = install_sample("selector-drift", "http://127.0.0.1:4173")
    code = path.read_text(encoding="utf-8")
    assert path == config.specs_dir() / "samples" / "contact-form.spec.ts"
    assert "page.goto('http://127.0.0.1:4173/')" in code
    assert BASE_URL_PLACEHOLDER not in code


def test_install_keeps_a_base_url_path() -> None:
    path = install_sample("app-bug", "http://127.0.0.1:7860/sample-site/")
    assert (
        "page.goto('http://127.0.0.1:7860/sample-site/checkout.html')"
        in path.read_text(encoding="utf-8")
    )


def test_reinstalling_restores_the_broken_spec() -> None:
    path = install_sample("selector-drift", "http://127.0.0.1:4173/")
    path.write_text("healed already", encoding="utf-8")
    again = install_sample("selector-drift", "http://127.0.0.1:4173/")
    assert again == path
    assert "#submit-btn" in again.read_text(encoding="utf-8")


def test_unknown_sample_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown sample 'nope'"):
        install_sample("nope", "http://127.0.0.1:4173/")


def test_bad_base_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        install_sample("selector-drift", "file:///etc/")
