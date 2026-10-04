"""The bundled samples: specs against the sample site, copied into the workspace.

Sample specs hold a ``{{BASE_URL}}`` placeholder, so they work wherever the
sample site is served: by the app (Phase 4) or by a test server.
"""

from pathlib import Path

from workbench.config import SAMPLE_SPECS_DIR, specs_dir
from workbench.models.samples import Sample
from workbench.validation import ValidationError, validate_url

BASE_URL_PLACEHOLDER = "{{BASE_URL}}"

# The scenario the Demo provider can generate a test for.
GENERATE_SCENARIO = "A user can send the contact form"

SAMPLES: dict[str, Sample] = {
    sample.name: sample
    for sample in (
        Sample(
            name="selector-drift",
            title="Selector drift",
            description=(
                "The submit button lost its id. The healer finds it by role and "
                "the test passes again."
            ),
            spec_file="contact-form.spec.ts",
            expected_status="healed",
        ),
        Sample(
            name="app-bug",
            title="App bug",
            description=(
                "Checkout fails on the server. The healer reports a likely app "
                "bug and leaves the test alone."
            ),
            spec_file="checkout.spec.ts",
            expected_status="app_defect_suspected",
        ),
    )
}


def install_sample(name: str, base_url: str) -> Path:
    """Copy sample ``name`` into the workspace with ``base_url`` filled in.

    Every call writes a fresh copy, so a sample healed earlier starts broken
    again. Raises ``ValueError`` for an unknown sample and ``ValidationError``
    for a URL that is not http(s).
    """
    sample = SAMPLES.get(name)
    if sample is None:
        known = ", ".join(SAMPLES)
        raise ValueError(f"Unknown sample {name!r}; choose one of: {known}")
    url = base_url.strip()
    if not validate_url(url):
        raise ValidationError(f"Invalid sample site URL: {base_url}")
    if not url.endswith("/"):
        url += "/"
    source = (SAMPLE_SPECS_DIR / sample.spec_file).read_text(encoding="utf-8")
    target_dir = specs_dir() / "samples"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / sample.spec_file
    target.write_text(source.replace(BASE_URL_PLACEHOLDER, url), encoding="utf-8")
    return target
