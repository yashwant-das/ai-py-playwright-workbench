# v2 Phase 3: Providers and Samples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 1.0 router and its `.env` with one small client for LM Studio and Ollama, a Demo provider that replays recorded answers, provider detection, settings saved in the workspace, and two bundled heal samples, so that S1 and S2 pass at pipeline level.

**Architecture:** Pipelines already depend only on `ChatModel` (Phase 2). This phase adds three implementations behind it: `OpenAICompatibleModel` (LM Studio and Ollama through the OpenAI API), `DemoModel` (answers from `samples/recordings/`), and `build_model(settings)` to pick one. `detect_provider()` probes LM Studio and then Ollama. `workspace/settings.json` holds the user's saved choice. `samples/` gains a checkout page, two sample specs with a `{{BASE_URL}}` placeholder, and the recordings. The router, model registry, retry policies, `python-dotenv` and `.env.example` are deleted.

**Tech Stack:** Python 3.13, Pydantic 2, `openai` 2.14.0 (OpenAI-compatible client), `httpx` 0.28.1 (model listing and test transports), Playwright 1.63.0, pytest.

**Spec:** [docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md](../specs/2026-10-03-v2-showcase-simplification-design.md). The relevant sections are §5.1 (Heal samples, Model selection), §6.1 (`settings.py`, `llm/client.py`, `llm/providers.py`, `llm/demo.py`, `samples/`), §6.6 (Providers and settings), §11 Phase 3, and success criteria S1, S2 and S4.

## Global Constraints

- Python `>=3.13`; Playwright exactly `1.63.0` (Python and npm); Node 24.
- **No environment variables are required.** Two optional ones exist for tests and CI only: `WORKBENCH_PORT` and `WORKBENCH_WORKSPACE` (spec §6.6). After this phase no module reads `LLM_PROVIDER`, `LM_STUDIO_*` or `OLLAMA_*`, and nothing imports `dotenv`.
- **Defaults:** LM Studio `http://localhost:1234/v1`, Ollama `http://localhost:11434/v1`, Demo (in-process).
- **First launch:** probe LM Studio, then Ollama. Use the first that answers, with its first listed model. If neither answers, there is no choice, and the UI (Phase 4) offers Demo.
- **Saved choice:** provider, server URL and model are written to `workspace/settings.json` and reused next time.
- **Demo:** answers come from `samples/recordings/`, matched by sample and prompt kind. A prompt that matches no recording gets a clear "Demo only covers the bundled samples" error. Demo answers carry provider `demo` in their provenance, so every report labels them.
- **Samples:** two bundled samples against the sample site: *Selector drift* (heals) and *App bug* (stops without editing). Sample specs contain a `{{BASE_URL}}` placeholder that is filled in when they are copied into the workspace.
- **Schema output:** `chat()` sends `response_format` with the JSON schema. If the provider rejects it (HTTP 400), the request is retried once without it. Pydantic validation always runs.
- **Errors:** pipelines still return a report with a status for every expected failure. A model failure is a `ModelError` whose message names the provider and server.
- **Code rules:**
  - All model output is parsed through Pydantic, and so is any JSON the code reads (`model_validate_json`).
  - New data shapes go in `workbench/models/`.
  - Paths come from `workbench.config`.
  - Unit tests make no network calls; HTTP is mocked with `httpx.MockTransport`.
- **Spec files** use kebab-case names (`contact-form.spec.ts`).
- **Commits:** Conventional Commits, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Docs timing (plan decision):** the `AGENTS.md` layout is updated once, in Task 5, when the router leaves. `ROADMAP.md` and `CHANGELOG.md` are updated in Task 7.

## Review Focus

1. **LM Studio lists an embedding model first.** Detection must not pick a model that cannot chat. Expected: ids containing `embed` are skipped. Pinned by `test_list_models_skips_embedding_models` (Task 2) and the fake server's model list (Task 6).
2. **A hand-edited, corrupt or outdated `settings.json`.** Expected: the app starts as if nothing were saved, and logs a warning. Pinned by `test_unusable_file_is_ignored` and `test_undecodable_file_is_ignored` (Task 4).
3. **A server URL typed without `/v1` or with a trailing slash** (`http://localhost:11434`, `http://localhost:1234/v1/`). Expected: normalised to `…/v1` with no trailing slash. Pinned by `test_bare_host_gets_the_openai_path` (Task 2).
4. **Demo used on the user's own spec or scenario.** Expected: the heal ends with status `error`, the message says Demo only covers the bundled samples, and the test file is unchanged. Pinned by `test_heal_with_demo_on_an_unknown_spec_is_a_clear_error` (Task 3).
5. **Running a sample again after it healed.** Expected: the sample starts broken again, never from the healed copy. Pinned by `test_reinstalling_restores_the_broken_spec` (Task 1).

---

## File map

| Action | Path | Responsibility |
| --- | --- | --- |
| Modify | `src/workbench/config.py` | `SAMPLES_DIR`, `SAMPLE_SITE_DIR`, `SAMPLE_SPECS_DIR`, `RECORDINGS_DIR` |
| Modify | `samples/site/index.html` | Contact page (drift sample) with shared nav and styles |
| Create | `samples/site/checkout.html`, `samples/site/style.css` | Checkout page whose order call always fails (app-bug sample) |
| Create | `samples/specs/contact-form.spec.ts`, `samples/specs/checkout.spec.ts` | Sample specs with `{{BASE_URL}}` |
| Create | `samples/recordings/*.json` | Demo answers: two heals, one generation |
| Create | `src/workbench/models/samples.py` | `Sample`, `Recording` |
| Create | `src/workbench/samples.py` | `SAMPLES`, `GENERATE_SCENARIO`, `install_sample()` |
| Create | `src/workbench/models/settings.py` | `ProviderName`, labels, default URLs, `normalise_base_url()`, `ModelSettings`, `ConnectionStatus` |
| Rewrite | `src/workbench/llm/client.py` | `OpenAICompatibleModel`, `list_models()` |
| Create | `src/workbench/llm/demo.py` | `DemoModel`, `load_recordings()`, `prompt_sections()` |
| Create | `src/workbench/llm/providers.py` | `detect_provider()`, `check_connection()`, `build_model()` |
| Create | `src/workbench/settings.py` | `load_settings()`, `save_settings()`, `resolve_settings()` |
| Modify | `src/workbench/llm/chat.py`, `src/workbench/llm/__init__.py` | Interface only; package exports |
| Delete | `src/workbench/llm/router.py`, `registry.py`, `policies.py`, `.env.example`, `tests/unit/test_llm.py` | The 1.0 router and its configuration |
| Modify | `pyproject.toml`, `uv.lock` | Add `httpx==0.28.1`; remove `python-dotenv` |
| Create | `tests/unit/test_samples.py`, `test_model_settings.py`, `test_client.py`, `test_demo.py`, `test_providers.py`, `test_settings.py` | Unit tests |
| Modify | `tests/unit/test_chat.py`, `tests/unit/test_layout.py` | Interface test; guards against the router and `dotenv` |
| Modify | `tests/integration/conftest.py`, `fake_llm.py`, `test_pipeline.py`, `test_heal_guarantees.py` | Sample site path; `/v1/models`; the new client; S4 moves to the sample |
| Create | `tests/integration/test_samples.py` | S1, S2, S4 at pipeline level |
| Modify | `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` | Guides |

---

### Task 1: The sample site, sample specs and `install_sample()`

**Files:**

- Modify: `src/workbench/config.py`, `samples/site/index.html`, `tests/integration/conftest.py`
- Create: `samples/site/checkout.html`, `samples/site/style.css`, `samples/specs/contact-form.spec.ts`, `samples/specs/checkout.spec.ts`, `src/workbench/models/samples.py`, `src/workbench/samples.py`, `tests/unit/test_samples.py`

**Interfaces:**

- Consumes: `workbench.config.specs_dir()`, `workbench.validation.validate_url()` and `ValidationError`.
- Produces:
  - `workbench.config.SAMPLES_DIR`, `SAMPLE_SITE_DIR`, `SAMPLE_SPECS_DIR`, `RECORDINGS_DIR` (`Path`)
  - `workbench.models.samples.Sample(name, title, description, spec_file, expected_status)`
  - `workbench.samples.SAMPLES: dict[str, Sample]` with keys `"selector-drift"` and `"app-bug"`
  - `workbench.samples.GENERATE_SCENARIO = "A user can send the contact form"`
  - `workbench.samples.BASE_URL_PLACEHOLDER = "{{BASE_URL}}"`
  - `workbench.samples.install_sample(name: str, base_url: str) -> Path`, which writes `specs_dir() / "samples" / <spec_file>`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_samples.py`:

```python
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
        source = (config.SAMPLE_SPECS_DIR / sample.spec_file).read_text(encoding="utf-8")
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
    assert "page.goto('http://127.0.0.1:7860/sample-site/checkout.html')" in path.read_text(
        encoding="utf-8"
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_samples.py -q -o addopts=`
Expected: collection error `No module named 'workbench.samples'`.

- [ ] **Step 3: Add the paths to `config.py`**

In `src/workbench/config.py`, after `WORKSPACE_ENV = "WORKBENCH_WORKSPACE"`, add:

```python

SAMPLES_DIR = PROJECT_ROOT / "samples"
SAMPLE_SITE_DIR = SAMPLES_DIR / "site"
SAMPLE_SPECS_DIR = SAMPLES_DIR / "specs"
RECORDINGS_DIR = SAMPLES_DIR / "recordings"
```

- [ ] **Step 4: Write the sample site**

Replace `samples/site/index.html` with the following. The form, the button and the status keep their roles and names, because the integration tests rely on them.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Sample shop · Contact</title>
    <link rel="stylesheet" href="style.css" />
  </head>
  <body>
    <nav aria-label="Sample shop">
      <a href="./" aria-current="page">Contact</a>
      <a href="checkout.html">Checkout</a>
    </nav>
    <main>
      <h1>Contact form</h1>
      <form id="contact">
        <label for="name">Name</label>
        <input id="name" name="name" type="text" />
        <button type="submit" data-testid="submit">Submit</button>
      </form>
      <p id="result" role="status"></p>
    </main>
    <script>
      document.getElementById('contact').addEventListener('submit', (event) => {
        event.preventDefault();
        document.getElementById('result').textContent = 'Submitted';
      });
    </script>
  </body>
</html>
```

Create `samples/site/checkout.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Sample shop · Checkout</title>
    <link rel="stylesheet" href="style.css" />
  </head>
  <body>
    <nav aria-label="Sample shop">
      <a href="./">Contact</a>
      <a href="checkout.html" aria-current="page">Checkout</a>
    </nav>
    <main>
      <h1>Checkout</h1>
      <form id="checkout">
        <label for="email">Email</label>
        <input id="email" name="email" type="email" />
        <label for="quantity">Quantity</label>
        <input id="quantity" name="quantity" type="number" value="1" min="1" />
        <button type="submit">Place order</button>
      </form>
      <p id="result" role="status"></p>
    </main>
    <script>
      // Orders go to api/orders, which the sample site does not serve, so every
      // order fails on the server side.
      document.getElementById('checkout').addEventListener('submit', async (event) => {
        event.preventDefault();
        const result = document.getElementById('result');
        try {
          const response = await fetch('api/orders', { method: 'POST' });
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          result.textContent = 'Order placed';
        } catch (error) {
          console.error(`Order failed: ${error.message}`);
          result.textContent = 'Something went wrong. Please try again.';
        }
      });
    </script>
  </body>
</html>
```

Create `samples/site/style.css`:

```css
body {
  margin: 0;
  font-family: system-ui, sans-serif;
  color: #1f2328;
}

nav {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #d0d7de;
}

nav a[aria-current='page'] {
  font-weight: 600;
}

main {
  max-width: 28rem;
  padding: 1.5rem;
}

form {
  display: grid;
  gap: 0.5rem;
}

button {
  justify-self: start;
  padding: 0.4rem 1rem;
}
```

- [ ] **Step 5: Write the sample specs**

Create `samples/specs/contact-form.spec.ts`. The drifted `#submit-btn` selector is the bug the sample heals. The 3-second timeout keeps the failing run short.

```typescript
import { test, expect } from '@playwright/test';

test('Contact form sends a message', async ({ page }) => {
  await page.goto('{{BASE_URL}}');
  await page.getByLabel('Name').fill('Ada Lovelace');
  await page.locator('#submit-btn').click({ timeout: 3000 });
  await expect(page.getByRole('status')).toHaveText('Submitted');
});
```

Create `samples/specs/checkout.spec.ts`. This test is correct; the page is what's broken.

```typescript
import { test, expect } from '@playwright/test';

test('Checkout places an order', async ({ page }) => {
  await page.goto('{{BASE_URL}}checkout.html');
  await page.getByLabel('Email').fill('ada@example.com');
  await page.getByRole('button', { name: 'Place order' }).click();
  await expect(page.getByRole('status')).toHaveText('Order placed', { timeout: 3000 });
});
```

- [ ] **Step 6: Write the sample model and `install_sample()`**

Create `src/workbench/models/samples.py`:

```python
"""The bundled samples the app offers on the Heal page."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Sample(BaseModel):
    """A bundled spec that shows one heal outcome against the sample site."""

    model_config = ConfigDict(frozen=True)

    name: str
    title: str
    description: str
    spec_file: str
    expected_status: Literal["healed", "app_defect_suspected"]
```

Create `src/workbench/samples.py`:

```python
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
```

- [ ] **Step 7: Point the integration site fixture at the config path**

In `tests/integration/conftest.py`, replace `SITE_DIR = config.PROJECT_ROOT / "samples" / "site"` with `SITE_DIR = config.SAMPLE_SITE_DIR`.

- [ ] **Step 8: Run the tests**

Run: `uv run python -m pytest tests/unit/test_samples.py -q -o addopts=`
Expected: 7 passed.

Run: `uv run python -m pytest -q -o addopts= && uv run python -m pytest tests/integration -q -o addopts=`
Expected: all pass. `test_sample_site_context` still finds `button "Submit"`, and there are no console or network errors, because `style.css` exists.

Run: `npm run lint`
Expected: clean (ESLint also checks `samples/specs/*.spec.ts`).

- [ ] **Step 9: Commit**

```bash
git add src/workbench/config.py src/workbench/models/samples.py src/workbench/samples.py samples/site samples/specs tests/unit/test_samples.py tests/integration/conftest.py
git commit -m "feat: add the selector-drift and app-bug samples" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Settings contracts and the LM Studio / Ollama client

**Files:**

- Create: `src/workbench/models/settings.py`, `tests/unit/test_model_settings.py`, `tests/unit/test_client.py`
- Rewrite: `src/workbench/llm/client.py`
- Modify: `pyproject.toml`, `uv.lock` (through `uv add`)

**Interfaces:**

- Consumes: `workbench.llm.chat.ChatReply`, `Message`, `ModelError`, `response_format_for` (Phase 2).
- Produces:
  - `workbench.models.settings`:
    - `ProviderName = Literal["lm_studio", "ollama", "demo"]`
    - `PROVIDER_LABELS: dict[ProviderName, str]`
    - `DEFAULT_URLS: dict[ProviderName, str]`, with keys `lm_studio` and `ollama`
    - `DEMO_MODEL = "recorded-answers"`
    - `normalise_base_url(url: str) -> str`
    - `ModelSettings(provider, base_url="", model)`, frozen, with property `label`
    - `ConnectionStatus(provider, base_url="", reachable, models=[], error="")`
  - `workbench.llm.client`:
    - `MODEL_TIMEOUT_S = 300.0`, `LIST_TIMEOUT_S = 2.0`
    - `list_models(base_url: str, *, timeout_s: float = LIST_TIMEOUT_S, http_client: httpx.Client | None = None) -> list[str]`
    - `OpenAICompatibleModel(*, provider, base_url, model, timeout_s=MODEL_TIMEOUT_S, http_client=None)`, which implements `ChatModel` and exposes the attributes `provider`, `base_url` and `model`

The old `ProviderConfig` and `LLMClientFactory` in `client.py` are used only by the router, which is deleted in Task 5. Replacing `client.py` now breaks the router's import, so Step 6 keeps the router importable by moving those two classes into `router.py`, where they live until Task 5 deletes it.

- [ ] **Step 1: Add `httpx` as a direct dependency**

The client imports `httpx` itself, so it must not rely on it arriving through `openai`. Pin it to the version already in the lockfile:

Run: `uv add "httpx==0.28.1"`
Expected: `pyproject.toml` lists `"httpx==0.28.1"`, and `uv.lock` is otherwise unchanged.

- [ ] **Step 2: Write the failing settings-contract tests**

Create `tests/unit/test_model_settings.py`:

```python
"""The saved model choice and how server URLs are cleaned up."""

import pytest
from pydantic import ValidationError

from workbench.models.settings import DEMO_MODEL, ModelSettings, normalise_base_url


def test_bare_host_gets_the_openai_path() -> None:
    assert normalise_base_url("http://localhost:11434") == "http://localhost:11434/v1"
    assert normalise_base_url(" http://localhost:1234/v1/ ") == "http://localhost:1234/v1"
    assert normalise_base_url("http://gpu-box:8080/openai/v1") == "http://gpu-box:8080/openai/v1"


@pytest.mark.parametrize("url", ["localhost:1234", "ftp://host/v1", "http://", ""])
def test_bad_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="http:// or https://"):
        normalise_base_url(url)


def test_server_providers_need_a_url() -> None:
    with pytest.raises(ValidationError, match="Ollama needs a server URL"):
        ModelSettings(provider="ollama", model="qwen3:8b")


def test_saved_url_is_normalised() -> None:
    choice = ModelSettings(provider="ollama", base_url="http://localhost:11434/", model="m")
    assert choice.base_url == "http://localhost:11434/v1"
    assert choice.label == "Ollama"


def test_demo_needs_no_url() -> None:
    choice = ModelSettings(provider="demo", model=DEMO_MODEL)
    assert choice.base_url == ""
    assert choice.label == "Demo"


def test_unknown_provider_and_empty_model_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelSettings(provider="openai", base_url="http://x/v1", model="m")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ModelSettings(provider="demo", model="")
```

- [ ] **Step 3: Write the failing client tests**

Create `tests/unit/test_client.py`:

```python
"""OpenAICompatibleModel and list_models against a mocked HTTP server."""

import json
import time
from collections.abc import Callable

import httpx
import pytest

from workbench.llm.chat import ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.models.settings import ProviderName

BASE = "http://127.0.0.1:1234/v1"
SCHEMA = {"title": "HealingAnalysis", "type": "object"}
MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]

Handler = Callable[[httpx.Request], httpx.Response]


def _completion(content: str | None = "ok", model: str = "m-1") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "c1",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        },
    )


def _model(handler: Handler, provider: ProviderName = "lm_studio") -> OpenAICompatibleModel:
    return OpenAICompatibleModel(
        provider=provider,
        base_url=BASE,
        model="m-1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _recorder(answer: Handler) -> tuple[list[dict], Handler]:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return answer(request)

    return bodies, handler


def test_reply_carries_provenance() -> None:
    reply = _model(lambda _: _completion("hello")).chat(MESSAGES)
    assert reply.content == "hello"
    assert (reply.provider, reply.model) == ("lm_studio", "m-1")
    assert (reply.input_tokens, reply.output_tokens) == (3, 4)
    assert reply.latency_ms >= 0


def test_schema_is_sent_as_response_format() -> None:
    bodies, handler = _recorder(lambda _: _completion())
    _model(handler).chat(MESSAGES, json_schema=SCHEMA)
    assert bodies[0]["model"] == "m-1"
    assert bodies[0]["messages"] == MESSAGES
    assert bodies[0]["response_format"]["type"] == "json_schema"
    assert bodies[0]["response_format"]["json_schema"]["schema"] == SCHEMA


def test_no_schema_sends_no_response_format() -> None:
    bodies, handler = _recorder(lambda _: _completion())
    _model(handler).chat(MESSAGES)
    assert "response_format" not in bodies[0]


def test_rejected_schema_is_retried_once_without_it() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if "response_format" in json.loads(request.content):
            return httpx.Response(400, json={"error": {"message": "response_format unsupported"}})
        return _completion("plain")

    bodies, handler = _recorder(answer)
    reply = _model(handler).chat(MESSAGES, json_schema=SCHEMA)
    assert reply.content == "plain"
    assert ["response_format" in body for body in bodies] == [True, False]


def test_a_bad_request_without_a_schema_is_not_retried() -> None:
    bodies, handler = _recorder(
        lambda _: httpx.Response(400, json={"error": {"message": "context length exceeded"}})
    )
    with pytest.raises(ModelError, match="HTTP 400: context length exceeded"):
        _model(handler).chat(MESSAGES)
    assert len(bodies) == 1


def test_failure_after_the_retry_is_a_model_error() -> None:
    bodies, handler = _recorder(
        lambda _: httpx.Response(400, json={"error": {"message": "still bad"}})
    )
    with pytest.raises(ModelError, match="still bad"):
        _model(handler).chat(MESSAGES, json_schema=SCHEMA)
    assert len(bodies) == 2


def test_unreachable_server_names_the_provider() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ModelError, match=r"Could not reach Ollama at http://127\.0\.0\.1:1234/v1"):
        _model(refuse, provider="ollama").chat(MESSAGES)


def test_timeout_is_reported_as_such() -> None:
    def stall(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ModelError, match="did not answer within 300 seconds"):
        _model(stall).chat(MESSAGES)


def test_unknown_model_says_so() -> None:
    with pytest.raises(ModelError, match="has no model named 'm-1'"):
        _model(lambda _: httpx.Response(404, json={"error": {"message": "not found"}})).chat(
            MESSAGES
        )


def test_empty_content_becomes_an_empty_reply() -> None:
    assert _model(lambda _: _completion(None)).chat(MESSAGES).content == ""


def _listing(handler: Handler) -> list[str]:
    return list_models(BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_list_models_skips_embedding_models() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{BASE}/models"
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": "text-embedding-nomic-embed-text-v1.5"},
                    {"id": "qwen3-8b"},
                    {"id": "gemma-3-4b"},
                ],
            },
        )

    assert _listing(answer) == ["qwen3-8b", "gemma-3-4b"]


def test_list_models_reports_an_unreachable_server() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ModelError, match="No answer from"):
        _listing(refuse)


def test_list_models_reports_http_errors() -> None:
    with pytest.raises(ModelError, match="No answer from"):
        _listing(lambda _: httpx.Response(500, text="boom"))


def test_list_models_rejects_an_answer_that_is_not_a_model_list() -> None:
    with pytest.raises(ModelError, match="did not return a model list"):
        _listing(lambda _: httpx.Response(200, json={"hello": "world"}))
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_model_settings.py tests/unit/test_client.py -q -o addopts=`
Expected: collection errors `No module named 'workbench.models.settings'` and `cannot import name 'OpenAICompatibleModel'`.

- [ ] **Step 5: Write the settings contracts**

Create `src/workbench/models/settings.py`:

```python
"""Which model the workbench talks to, and how to reach it."""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProviderName = Literal["lm_studio", "ollama", "demo"]

PROVIDER_LABELS: dict[ProviderName, str] = {
    "lm_studio": "LM Studio",
    "ollama": "Ollama",
    "demo": "Demo",
}
DEFAULT_URLS: dict[ProviderName, str] = {
    "lm_studio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
}
DEMO_MODEL = "recorded-answers"


def normalise_base_url(url: str) -> str:
    """Clean a typed server URL: no trailing slash, and ``/v1`` when no path is given.

    Raises ``ValueError`` unless the URL is http(s) and names a host.
    """
    cleaned = url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"Server URL must start with http:// or https:// and name a host: {url!r}"
        )
    return cleaned if parsed.path else f"{cleaned}/v1"


class ModelSettings(BaseModel):
    """The model choice saved in ``workspace/settings.json``."""

    model_config = ConfigDict(frozen=True)

    provider: ProviderName
    base_url: str = ""
    model: str = Field(min_length=1)

    @field_validator("base_url")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return normalise_base_url(value) if value.strip() else ""

    @model_validator(mode="after")
    def _servers_need_a_url(self) -> "ModelSettings":
        if self.provider != "demo" and not self.base_url:
            raise ValueError(f"{PROVIDER_LABELS[self.provider]} needs a server URL.")
        return self

    @property
    def label(self) -> str:
        return PROVIDER_LABELS[self.provider]


class ConnectionStatus(BaseModel):
    """What the model menu shows about the chosen server."""

    provider: ProviderName
    base_url: str = ""
    reachable: bool
    models: list[str] = Field(default_factory=list)
    error: str = ""
```

- [ ] **Step 6: Keep the router importable until Task 5**

Copy the `ProviderConfig` and `LLMClientFactory` classes from the current `src/workbench/llm/client.py` into `src/workbench/llm/router.py`, keeping their `import os` and `from openai import OpenAI` and placing them above `class LLMRequest`. In `router.py`, delete the line `from workbench.llm.client import LLMClientFactory, ProviderConfig`. In `src/workbench/llm/__init__.py`, change `from workbench.llm.client import LLMClientFactory, ProviderConfig` to `from workbench.llm.router import LLMClientFactory, ProviderConfig`. In `tests/unit/test_llm.py`, change every `workbench.llm.client` import or patch target to `workbench.llm.router`. All of these files are deleted in Task 5.

- [ ] **Step 7: Write the client**

Replace `src/workbench/llm/client.py` with:

```python
"""Talks to LM Studio and Ollama through their OpenAI-compatible API.

``OpenAICompatibleModel`` implements ``ChatModel``. ``list_models`` asks a
server which models it can run; provider detection and the model menu use it.
"""

import logging
import time
from typing import Any, cast

import httpx
import openai
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from workbench.llm.chat import ChatReply, Message, ModelError, response_format_for
from workbench.models.settings import PROVIDER_LABELS, ProviderName

logger = logging.getLogger(__name__)

MODEL_TIMEOUT_S = 300.0  # a local model on modest hardware can take minutes
LIST_TIMEOUT_S = 2.0
# Local servers ignore the key, but the OpenAI client requires one.
_API_KEYS: dict[ProviderName, str] = {"lm_studio": "lm-studio", "ollama": "ollama"}


class _ModelEntry(BaseModel):
    id: str


class _ModelList(BaseModel):
    data: list[_ModelEntry]


def list_models(
    base_url: str,
    *,
    timeout_s: float = LIST_TIMEOUT_S,
    http_client: httpx.Client | None = None,
) -> list[str]:
    """Ids of the chat models the server at ``base_url`` offers, in its order.

    Embedding models are left out: they cannot answer a chat request.
    Raises ``ModelError`` when the server does not answer or answers nonsense.
    """
    client = http_client or httpx.Client(timeout=timeout_s)
    try:
        response = client.get(f"{base_url}/models", timeout=timeout_s)
        response.raise_for_status()
        listing = _ModelList.model_validate_json(response.content)
    except httpx.HTTPError as exc:
        raise ModelError(f"No answer from {base_url}: {exc}") from exc
    except ValidationError as exc:
        raise ModelError(f"{base_url}/models did not return a model list.") from exc
    finally:
        if http_client is None:
            client.close()
    return [entry.id for entry in listing.data if "embed" not in entry.id.lower()]


def _provider_message(exc: openai.APIStatusError) -> str:
    """The server's own error text, whichever shape its error body has."""
    body: Any = exc.body
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, str):
            return error
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return str(error["message"])
    return exc.message


class OpenAICompatibleModel:
    """A model served by LM Studio or Ollama."""

    def __init__(
        self,
        *,
        provider: ProviderName,
        base_url: str,
        model: str,
        timeout_s: float = MODEL_TIMEOUT_S,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.provider = provider
        self.base_url = base_url
        self.model = model
        self._label = PROVIDER_LABELS[provider]
        self._timeout_s = timeout_s
        self._client = openai.OpenAI(
            base_url=base_url,
            api_key=_API_KEYS.get(provider, "local"),
            timeout=timeout_s,
            # A local server that failed once will fail again; say so at once.
            max_retries=0,
            http_client=http_client,
        )

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        response_format = response_format_for(json_schema) if json_schema else None
        started = time.monotonic()
        try:
            completion = self._complete(messages, temperature, response_format)
        except openai.BadRequestError as exc:
            if response_format is None:
                raise self._error(exc) from exc
            logger.info(
                "%s rejected the JSON schema (%s); asking without it.",
                self._label,
                _provider_message(exc),
            )
            try:
                completion = self._complete(messages, temperature, None)
            except openai.OpenAIError as retry_exc:
                raise self._error(retry_exc) from retry_exc
        except openai.OpenAIError as exc:
            raise self._error(exc) from exc
        usage = completion.usage
        content = completion.choices[0].message.content if completion.choices else None
        return ChatReply(
            content=content or "",
            model=completion.model or self.model,
            provider=self.provider,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    def _complete(
        self,
        messages: list[Message],
        temperature: float,
        response_format: dict[str, Any] | None,
    ) -> ChatCompletion:
        extra: dict[str, Any] = (
            {"response_format": response_format} if response_format else {}
        )
        return self._client.chat.completions.create(
            model=self.model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            temperature=temperature,
            **extra,
        )

    def _error(self, exc: openai.OpenAIError) -> ModelError:
        where = f"{self._label} at {self.base_url}"
        if isinstance(exc, openai.APITimeoutError):
            return ModelError(
                f"{where} did not answer within {self._timeout_s:.0f} seconds."
            )
        if isinstance(exc, openai.APIConnectionError):
            return ModelError(f"Could not reach {where}. Is it running?")
        if isinstance(exc, openai.NotFoundError):
            return ModelError(
                f"{where} has no model named {self.model!r}. Load it or pick another model."
            )
        if isinstance(exc, openai.APIStatusError):
            return ModelError(
                f"{where} answered HTTP {exc.status_code}: {_provider_message(exc)}"
            )
        return ModelError(f"{where} failed: {exc}")
```

- [ ] **Step 8: Run the tests**

Run: `uv run python -m pytest tests/unit/test_model_settings.py tests/unit/test_client.py -q -o addopts=`
Expected: 23 passed (9 settings tests, counting the parametrized cases, and 14 client tests).

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass. The router tests still pass with their imports pointed at `router.py`.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock src/workbench/models/settings.py src/workbench/llm/client.py src/workbench/llm/router.py src/workbench/llm/__init__.py tests/unit/test_model_settings.py tests/unit/test_client.py tests/unit/test_llm.py
git commit -m "feat: add the LM Studio and Ollama client with schema output and clear errors" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The Demo provider and its recordings

**Files:**

- Create: `src/workbench/llm/demo.py`, `samples/recordings/selector-drift.heal.json`, `samples/recordings/app-bug.heal.json`, `samples/recordings/contact-form.generate.json`, `tests/unit/test_demo.py`
- Modify: `src/workbench/models/samples.py` (adds `Recording`)

**Interfaces:**

- Consumes:
  - `RECORDINGS_DIR`, `SAMPLE_SPECS_DIR`, `SAMPLES` and `GENERATE_SCENARIO` (Task 1)
  - `DEMO_MODEL` (Task 2)
  - from Phase 2: `ChatReply`, `ModelError`, `render_prompt()`, `heal()`, `HealRequest`, `parse_llm_response()`, `extract_code_block()`
- Produces:
  - `workbench.models.samples.Recording(kind: Literal["heal", "generate"], sample: str, match: str, reply: str | dict[str, Any])`
  - `workbench.llm.demo.NOT_COVERED` (message template)
  - `workbench.llm.demo.load_recordings(directory: Path = RECORDINGS_DIR) -> list[Recording]`
  - `workbench.llm.demo.prompt_sections(prompt: str) -> dict[str, str]`
  - `workbench.llm.demo.DemoModel(recordings: list[Recording] | None = None)`, which implements `ChatModel`; replies carry `provider="demo"` and `model=DEMO_MODEL`

**How Demo matches a prompt:**

- **Heal prompts** contain a `## Test file` section. A heal recording matches when its `match` text (the sample's test title) appears in that section.
- **Generate prompts** contain a `## Scenario` section. A generate recording matches when its `match` equals the scenario, ignoring case and spacing. Its reply's `{{URL}}` is replaced with the `## Target URL` section.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_demo.py`:

```python
"""The Demo provider replays recorded answers for the bundled samples only."""

from pathlib import Path

import pytest

from workbench import config
from workbench.heal import HealRequest, heal
from workbench.llm.chat import ModelError
from workbench.llm.demo import DemoModel, load_recordings, prompt_sections
from workbench.llm.parsing import extract_code_block, parse_llm_response
from workbench.llm.prompts import render_prompt
from workbench.models.artifacts import ContextSnapshot
from workbench.models.heal import HealingAnalysis
from workbench.models.settings import DEMO_MODEL
from workbench.models.shared import FailureType, RunResult
from workbench.samples import GENERATE_SCENARIO, SAMPLES

LIMITS = {
    "Test file": 20_000,
    "Error": 4_000,
    "Target URL": 500,
    "Scenario": 1_000,
    "Page snapshot": 12_000,
}


def _messages(user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": "system prompt"}, {"role": "user", "content": user}]


def _heal_prompt(test_file: str) -> str:
    return render_prompt([("Test file", test_file), ("Error", "TimeoutError")], LIMITS)[0]


def _generate_prompt(url: str, scenario: str) -> str:
    sections = [("Target URL", url), ("Scenario", scenario), ("Page snapshot", "- button")]
    return render_prompt(sections, LIMITS)[0]


def _sample_spec(name: str) -> str:
    return (config.SAMPLE_SPECS_DIR / SAMPLES[name].spec_file).read_text(encoding="utf-8")


def test_prompt_sections_round_trip() -> None:
    prompt, _ = render_prompt([("A", "one\ntwo"), ("B", "three")], {"A": 100, "B": 100})
    assert prompt_sections(prompt) == {"A": "one\ntwo", "B": "three"}


def test_drift_sample_gets_a_fix_that_matches_its_source() -> None:
    spec = _sample_spec("selector-drift")
    reply = DemoModel().chat(_messages(_heal_prompt(spec)))
    analysis = parse_llm_response(reply.content, HealingAnalysis)
    assert analysis.failure_type == FailureType.LOCATOR_DRIFT
    assert analysis.action_taken.original_code in spec
    assert (reply.provider, reply.model) == ("demo", DEMO_MODEL)


def test_app_bug_sample_gets_a_confident_app_defect_diagnosis() -> None:
    reply = DemoModel().chat(_messages(_heal_prompt(_sample_spec("app-bug"))))
    analysis = parse_llm_response(reply.content, HealingAnalysis)
    assert analysis.failure_type == FailureType.POTENTIAL_APP_DEFECT
    assert analysis.confidence_score >= 0.7


def test_sample_scenario_is_generated_for_the_given_url() -> None:
    prompt = _generate_prompt("http://127.0.0.1:4173/", "  a user can SEND the contact form ")
    code = extract_code_block(DemoModel().chat(_messages(prompt)).content)
    assert "page.goto('http://127.0.0.1:4173/')" in code
    assert "{{URL}}" not in code


def test_unknown_spec_is_not_covered() -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages(_heal_prompt("test('mine', async () => {});")))


def test_unknown_scenario_is_not_covered() -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages(_generate_prompt("http://x.test/", "Buy a hat")))


def test_unrecognised_prompt_is_not_covered() -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages("hello"))


def test_every_sample_has_a_heal_recording() -> None:
    assert {r.sample for r in load_recordings() if r.kind == "heal"} == set(SAMPLES)


def test_the_generate_recording_is_the_sample_scenario() -> None:
    assert [r.match for r in load_recordings() if r.kind == "generate"] == [GENERATE_SCENARIO]


def test_heal_with_demo_on_an_unknown_spec_is_a_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    code = (
        "import { test } from '@playwright/test';\n"
        "test('mine', async ({ page }) => {\n"
        "  await page.goto('http://example.test/');\n"
        "});\n"
    )
    spec = tmp_path / "mine.spec.ts"
    spec.write_text(code, encoding="utf-8")

    report = heal(
        HealRequest(spec_path=spec, max_attempts=1),
        model=DemoModel(),
        run=lambda *_, **__: RunResult(status="failed", error_message="Error: boom"),
        collect=lambda url: ContextSnapshot(url=url),
        browsers_ready=lambda: True,
    )

    assert report.status == "error"
    assert "Demo only covers the bundled samples" in report.error_message
    assert spec.read_text(encoding="utf-8") == code
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_demo.py -q -o addopts=`
Expected: collection error `No module named 'workbench.llm.demo'`.

- [ ] **Step 3: Add the `Recording` model**

Append to `src/workbench/models/samples.py`, and add `from typing import Any` and `Field` to its imports:

```python


class Recording(BaseModel):
    """One recorded model answer that the Demo provider replays."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["heal", "generate"]
    sample: str
    match: str = Field(min_length=1)
    reply: str | dict[str, Any]
```

- [ ] **Step 4: Write the recordings**

Create `samples/recordings/selector-drift.heal.json`:

```json
{
  "kind": "heal",
  "sample": "selector-drift",
  "match": "Contact form sends a message",
  "reply": {
    "failure_type": "LOCATOR_DRIFT",
    "failure_summary": "The click on #submit-btn timed out: no element has that id any more.",
    "hypothesis": "The submit button is still on the page and still named Submit; only its id is gone. Finding it by role and name matches what the user sees.",
    "confidence_score": 0.9,
    "confidence_rationale": "The page snapshot at the failure shows exactly one button named Submit, and the error names the missing selector.",
    "reasoning_steps": [
      "The error is a timeout waiting for locator('#submit-btn').",
      "The page snapshot at the failure shows the form with the name filled in and a button named \"Submit\".",
      "Nothing in the snapshot carries the id submit-btn, so the selector drifted.",
      "getByRole('button', { name: 'Submit' }) finds the same button by what the user sees."
    ],
    "root_cause_evidence": [
      "button \"Submit\" in the page snapshot at the failure",
      "TimeoutError waiting for locator('#submit-btn')"
    ],
    "action_taken": {
      "original_code": "page.locator('#submit-btn')",
      "fixed_code": "page.getByRole('button', { name: 'Submit' })",
      "description": "Find the submit button by its role and name instead of the removed id.",
      "repair_strategy": "selector_replace"
    }
  }
}
```

Create `samples/recordings/app-bug.heal.json`:

```json
{
  "kind": "heal",
  "sample": "app-bug",
  "match": "Checkout places an order",
  "reply": {
    "failure_type": "POTENTIAL_APP_DEFECT",
    "failure_summary": "After Place order, the page says \"Something went wrong\" instead of \"Order placed\".",
    "hypothesis": "The test does what a customer does and expects the right outcome. The order request fails, so the app is broken, not the test.",
    "confidence_score": 0.9,
    "confidence_rationale": "Every step of the test succeeded; only the outcome differs, and the page itself reports an error.",
    "reasoning_steps": [
      "The email was filled in and the Place order button was clicked without errors.",
      "The status then reads \"Something went wrong. Please try again.\"",
      "That is an error message from the app, not a changed label or a slow page.",
      "Changing the assertion would hide a broken checkout, so the test should stay as it is."
    ],
    "root_cause_evidence": [
      "status \"Something went wrong. Please try again.\" in the page snapshot at the failure",
      "Expected \"Order placed\""
    ],
    "action_taken": {
      "original_code": "",
      "fixed_code": "",
      "description": "No change: the test is right and the checkout is broken.",
      "repair_strategy": "string_replace"
    }
  }
}
```

Create `samples/recordings/contact-form.generate.json`:

```json
{
  "kind": "generate",
  "sample": "contact-form",
  "match": "A user can send the contact form",
  "reply": "```typescript\nimport { test, expect } from '@playwright/test';\n\ntest('A user can send the contact form', async ({ page }) => {\n  await page.goto('{{URL}}');\n  await page.getByLabel('Name').fill('Ada Lovelace');\n  await page.getByRole('button', { name: 'Submit' }).click();\n  await expect(page.getByRole('status')).toHaveText('Submitted');\n});\n```"
}
```

- [ ] **Step 5: Write the Demo provider**

Create `src/workbench/llm/demo.py`:

```python
"""The Demo provider: replays recorded answers for the bundled samples.

It lets anyone try the workbench without a model server. A prompt that
matches no recording gets a clear error instead of a made-up answer.
"""

import json
import re
from pathlib import Path
from typing import Any

from workbench.config import RECORDINGS_DIR
from workbench.llm.chat import ChatReply, Message, ModelError
from workbench.models.samples import Recording
from workbench.models.settings import DEMO_MODEL

NOT_COVERED = (
    "Demo only covers the bundled samples. Choose LM Studio or Ollama in the "
    "model menu to {action}."
)
_SECTION = re.compile(r"^## (.+)$", re.MULTILINE)


def load_recordings(directory: Path = RECORDINGS_DIR) -> list[Recording]:
    """Every recording in ``directory`` (``*.json``), in file-name order."""
    return [
        Recording.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    ]


def prompt_sections(prompt: str) -> dict[str, str]:
    """Split a prompt made by ``render_prompt`` back into its named sections."""
    headers = list(_SECTION.finditer(prompt))
    sections: dict[str, str] = {}
    for header, following in zip(headers, [*headers[1:], None], strict=True):
        end = following.start() if following else len(prompt)
        sections[header.group(1).strip()] = prompt[header.end() : end].strip()
    return sections


def _same_text(a: str, b: str) -> bool:
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


def _as_text(reply: str | dict[str, Any]) -> str:
    return reply if isinstance(reply, str) else json.dumps(reply)


class DemoModel:
    """``ChatModel`` that answers from ``samples/recordings``."""

    def __init__(self, recordings: list[Recording] | None = None) -> None:
        self._recordings = load_recordings() if recordings is None else recordings

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        sections = prompt_sections(user)
        if "Test file" in sections:
            content = self._heal_reply(sections["Test file"])
        elif "Scenario" in sections:
            content = self._generate_reply(
                sections["Scenario"], sections.get("Target URL", "")
            )
        else:
            raise ModelError(NOT_COVERED.format(action="run this request"))
        return ChatReply(content=content, model=DEMO_MODEL, provider="demo")

    def _heal_reply(self, test_file: str) -> str:
        for recording in self._recordings:
            if recording.kind == "heal" and recording.match in test_file:
                return _as_text(recording.reply)
        raise ModelError(NOT_COVERED.format(action="heal other tests"))

    def _generate_reply(self, scenario: str, url: str) -> str:
        for recording in self._recordings:
            if recording.kind == "generate" and _same_text(recording.match, scenario):
                return _as_text(recording.reply).replace("{{URL}}", url.strip())
        raise ModelError(NOT_COVERED.format(action="generate other tests"))
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_demo.py -q -o addopts=`
Expected: 10 passed.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/workbench/llm/demo.py src/workbench/models/samples.py samples/recordings tests/unit/test_demo.py
git commit -m "feat: add the Demo provider with recorded answers for the samples" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Provider detection, connection checks and saved settings

**Files:**

- Create: `src/workbench/llm/providers.py`, `src/workbench/settings.py`, `tests/unit/test_providers.py`, `tests/unit/test_settings.py`

**Interfaces:**

- Consumes:
  - `list_models`, `OpenAICompatibleModel` (Task 2)
  - `DemoModel` (Task 3)
  - `ModelSettings`, `ConnectionStatus`, `DEFAULT_URLS`, `DEMO_MODEL`, `ProviderName` (Task 2)
  - `workspace_dir()` (Phase 2)
- Produces:
  - `workbench.llm.providers`:
    - `ListModels = Callable[[str], list[str]]`
    - `DETECTION_ORDER = ("lm_studio", "ollama")`
    - `detect_provider(*, order=DETECTION_ORDER, urls=DEFAULT_URLS, list_models=list_models) -> ModelSettings | None`
    - `check_connection(settings, *, list_models=list_models) -> ConnectionStatus`
    - `build_model(settings: ModelSettings) -> ChatModel`
  - `workbench.settings`:
    - `SETTINGS_FILE = "settings.json"`
    - `settings_path() -> Path`
    - `load_settings() -> ModelSettings | None`
    - `save_settings(settings: ModelSettings) -> Path`
    - `resolve_settings(*, detect=detect_provider) -> ModelSettings | None`

**Plan decisions:**

- **Detected servers are not saved.** A server that detection finds is used, but only an explicit choice in the UI is saved. Until then, every start detects again, so starting Ollama instead of LM Studio needs no change.
- **A saved server that is down is still returned.** The UI shows it as not connected. It never switches provider silently.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_providers.py`:

```python
"""Detection order, connection checks and which ChatModel a choice builds."""

from collections.abc import Callable

from workbench.llm.chat import ModelError
from workbench.llm.client import OpenAICompatibleModel
from workbench.llm.demo import DemoModel
from workbench.llm.providers import build_model, check_connection, detect_provider
from workbench.models.settings import DEFAULT_URLS, DEMO_MODEL, ConnectionStatus, ModelSettings

LM = DEFAULT_URLS["lm_studio"]
OLLAMA = DEFAULT_URLS["ollama"]


def _servers(answers: dict[str, list[str]]) -> Callable[[str], list[str]]:
    """A fake ``list_models``: URLs in ``answers`` respond, the rest are down."""

    def fake(base_url: str) -> list[str]:
        if base_url not in answers:
            raise ModelError(f"No answer from {base_url}: refused")
        return answers[base_url]

    return fake


def _never(base_url: str) -> list[str]:
    raise AssertionError(f"Demo must not contact {base_url}")


def test_lm_studio_wins_when_both_answer() -> None:
    choice = detect_provider(list_models=_servers({LM: ["qwen3-8b"], OLLAMA: ["gemma3:4b"]}))
    assert choice == ModelSettings(provider="lm_studio", base_url=LM, model="qwen3-8b")


def test_ollama_is_used_when_lm_studio_is_down() -> None:
    choice = detect_provider(list_models=_servers({OLLAMA: ["gemma3:4b", "qwen3:8b"]}))
    assert choice == ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b")


def test_a_server_with_no_models_is_skipped() -> None:
    choice = detect_provider(list_models=_servers({LM: [], OLLAMA: ["gemma3:4b"]}))
    assert choice is not None and choice.provider == "ollama"


def test_no_server_means_no_choice() -> None:
    assert detect_provider(list_models=_servers({})) is None


def test_connection_lists_the_models() -> None:
    choice = ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b")
    status = check_connection(choice, list_models=_servers({OLLAMA: ["gemma3:4b", "qwen3:8b"]}))
    assert status == ConnectionStatus(
        provider="ollama", base_url=OLLAMA, reachable=True, models=["gemma3:4b", "qwen3:8b"]
    )


def test_connection_reports_an_unreachable_server() -> None:
    choice = ModelSettings(provider="lm_studio", base_url=LM, model="qwen3-8b")
    status = check_connection(choice, list_models=_servers({}))
    assert not status.reachable
    assert status.models == []
    assert "No answer from" in status.error


def test_demo_is_always_connected() -> None:
    status = check_connection(ModelSettings(provider="demo", model=DEMO_MODEL), list_models=_never)
    assert status.reachable and status.models == [DEMO_MODEL]


def test_build_model_picks_the_implementation() -> None:
    assert isinstance(build_model(ModelSettings(provider="demo", model=DEMO_MODEL)), DemoModel)
    model = build_model(ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b"))
    assert isinstance(model, OpenAICompatibleModel)
    assert (model.provider, model.base_url, model.model) == ("ollama", OLLAMA, "gemma3:4b")
```

Create `tests/unit/test_settings.py`:

```python
"""The saved model choice in workspace/settings.json."""

from pathlib import Path

import pytest

from workbench import config
from workbench.models.settings import DEFAULT_URLS, DEMO_MODEL, ModelSettings
from workbench.settings import load_settings, resolve_settings, save_settings, settings_path


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))


def test_nothing_saved_means_no_choice() -> None:
    assert load_settings() is None


def test_saved_choice_round_trips() -> None:
    choice = ModelSettings(provider="ollama", base_url=DEFAULT_URLS["ollama"], model="qwen3:8b")
    path = save_settings(choice)
    assert path == settings_path() == config.workspace_dir() / "settings.json"
    assert load_settings() == choice
    assert not path.with_suffix(".tmp").exists()


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        '{"provider": "openai", "model": "gpt"}',
        '{"provider": "ollama", "model": "qwen3:8b"}',
        '{"provider": "lm_studio", "base_url": "localhost:1234", "model": "m"}',
    ],
)
def test_unusable_file_is_ignored(content: str) -> None:
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_text(content, encoding="utf-8")
    assert load_settings() is None


def test_undecodable_file_is_ignored() -> None:
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_bytes(b"\xff\xfe\x00garbage")
    assert load_settings() is None


def test_resolve_prefers_the_saved_choice() -> None:
    save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))

    def detect() -> ModelSettings | None:
        raise AssertionError("detected despite a saved choice")

    choice = resolve_settings(detect=detect)
    assert choice is not None and choice.provider == "demo"


def test_resolve_detects_when_nothing_is_saved_and_does_not_save() -> None:
    found = ModelSettings(provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m")
    assert resolve_settings(detect=lambda: found) == found
    assert not settings_path().exists()


def test_resolve_with_no_server_and_nothing_saved_is_none() -> None:
    assert resolve_settings(detect=lambda: None) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_providers.py tests/unit/test_settings.py -q -o addopts=`
Expected: collection errors `No module named 'workbench.llm.providers'` and `No module named 'workbench.settings'`.

- [ ] **Step 3: Write the providers module**

Create `src/workbench/llm/providers.py`:

```python
"""LM Studio, Ollama and Demo: detection, connection checks and model creation."""

from collections.abc import Callable, Iterable, Mapping

from workbench.llm.chat import ChatModel, ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.llm.demo import DemoModel
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
    ProviderName,
)

ListModels = Callable[[str], list[str]]
DETECTION_ORDER: tuple[ProviderName, ...] = ("lm_studio", "ollama")


def detect_provider(
    *,
    order: Iterable[ProviderName] = DETECTION_ORDER,
    urls: Mapping[ProviderName, str] = DEFAULT_URLS,
    list_models: ListModels = list_models,
) -> ModelSettings | None:
    """The first local server that answers and offers a model, with its first model.

    None when neither LM Studio nor Ollama is usable; the UI then offers Demo.
    """
    for provider in order:
        base_url = urls[provider]
        try:
            models = list_models(base_url)
        except ModelError:
            continue
        if models:
            return ModelSettings(provider=provider, base_url=base_url, model=models[0])
    return None


def check_connection(
    settings: ModelSettings, *, list_models: ListModels = list_models
) -> ConnectionStatus:
    """Ask the chosen server for its models; Demo is always available."""
    if settings.provider == "demo":
        return ConnectionStatus(provider="demo", reachable=True, models=[DEMO_MODEL])
    try:
        models = list_models(settings.base_url)
    except ModelError as exc:
        return ConnectionStatus(
            provider=settings.provider,
            base_url=settings.base_url,
            reachable=False,
            error=str(exc),
        )
    return ConnectionStatus(
        provider=settings.provider,
        base_url=settings.base_url,
        reachable=True,
        models=models,
    )


def build_model(settings: ModelSettings) -> ChatModel:
    """The ``ChatModel`` for a model choice."""
    if settings.provider == "demo":
        return DemoModel()
    return OpenAICompatibleModel(
        provider=settings.provider, base_url=settings.base_url, model=settings.model
    )
```

- [ ] **Step 4: Write the settings module**

Create `src/workbench/settings.py`:

```python
"""The model choice saved in ``workspace/settings.json``.

The app has no ``.env``: the user picks a provider and model in the UI and
the choice is saved here. Until something is saved, the app detects a local
server on every start.
"""

import logging
import os
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from workbench.config import workspace_dir
from workbench.llm.providers import detect_provider
from workbench.models.settings import ModelSettings

logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"


def settings_path() -> Path:
    return workspace_dir() / SETTINGS_FILE


def load_settings() -> ModelSettings | None:
    """The saved choice, or None when nothing usable is saved.

    A missing, unreadable or invalid file counts as no choice, so a bad hand
    edit never stops the app from starting.
    """
    path = settings_path()
    try:
        return ModelSettings.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        logger.warning("Ignoring %s: %s", path, exc)
        return None


def save_settings(settings: ModelSettings) -> Path:
    """Write the choice atomically, so a crash never leaves half a file."""
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, path)
    return path


def resolve_settings(
    *, detect: Callable[[], ModelSettings | None] = detect_provider
) -> ModelSettings | None:
    """The saved choice; otherwise the first local server that answers.

    A detected server is used but not saved. A saved server that is down is
    still returned: the UI shows it as not connected instead of switching.
    """
    return load_settings() or detect()
```

- [ ] **Step 5: Run the tests**

Run: `uv run python -m pytest tests/unit/test_providers.py tests/unit/test_settings.py -q -o addopts=`
Expected: 18 passed (8 provider tests and 10 settings tests, counting the parametrized cases).

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/workbench/llm/providers.py src/workbench/settings.py tests/unit/test_providers.py tests/unit/test_settings.py
git commit -m "feat: detect LM Studio or Ollama and save the model choice in the workspace" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Remove the router, the model registry and `.env`

**Files:**

- Delete: `src/workbench/llm/router.py`, `src/workbench/llm/registry.py`, `src/workbench/llm/policies.py`, `tests/unit/test_llm.py`, `.env.example`
- Modify: `src/workbench/llm/chat.py`, `src/workbench/llm/__init__.py`, `tests/unit/test_chat.py`, `tests/unit/test_layout.py`, `tests/integration/fake_llm.py`, `tests/integration/test_pipeline.py`, `pyproject.toml`, `uv.lock`, `AGENTS.md`

**Interfaces:**

- Consumes: everything from Tasks 2–4.
- Produces:
  - `workbench.llm` exports `ChatModel`, `ChatReply`, `ModelError`, `OpenAICompatibleModel`, `list_models`, `DemoModel`, `build_model`, `check_connection` and `detect_provider`.
  - `FakeLLM` (in `tests/integration/fake_llm.py`) also serves `GET /v1/models`, listing an embedding model and then `fake-model`.

- [ ] **Step 1: Write the failing guards**

In `tests/unit/test_layout.py`, extend `LEGACY_IMPORT` so the router and `dotenv` cannot come back:

```python
LEGACY_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(?:src|schemas|benchmarks|gradio|dotenv)\b"
    r"|[\"'](?:src|schemas)\.[a-z_]"
    r"|observability\.(?:tracer|writer)|get_tracer\("
    r"|workbench\.llm\.(?:router|registry|policies)\b|get_default_router\(",
    re.MULTILINE,
)
```

Then add `".env.example"`, `"src/workbench/llm/router.py"`, `"src/workbench/llm/registry.py"` and `"src/workbench/llm/policies.py"` to the `legacy` list in `test_legacy_top_level_folders_are_gone`.

Replace `tests/unit/test_chat.py` with:

```python
"""The ChatModel interface's shared helper."""

from workbench.llm.chat import response_format_for


def test_response_format_names_the_schema() -> None:
    schema = {"title": "HealingAnalysis", "type": "object"}
    assert response_format_for(schema) == {
        "type": "json_schema",
        "json_schema": {"name": "HealingAnalysis", "schema": schema},
    }
```

Run: `uv run python -m pytest tests/unit/test_layout.py -q -o addopts=`
Expected: FAIL. `test_no_module_uses_the_legacy_layout` lists the files that import the router (`src/workbench/llm/__init__.py`, `src/workbench/llm/chat.py`, `tests/unit/test_llm.py`, `tests/integration/test_pipeline.py`), and `test_legacy_top_level_folders_are_gone` lists `.env.example` and the three modules.

- [ ] **Step 2: Delete the router and its configuration**

```bash
git rm -q src/workbench/llm/router.py src/workbench/llm/registry.py src/workbench/llm/policies.py tests/unit/test_llm.py .env.example
uv remove python-dotenv
```

- [ ] **Step 3: Reduce `chat.py` to the interface**

In `src/workbench/llm/chat.py`:

- Replace the module docstring with:

  ```python
  """The one interface pipelines use to talk to a model.

  Pipelines depend on ``ChatModel``, never on a provider. The implementations
  are ``OpenAICompatibleModel`` (LM Studio, Ollama) in ``client.py`` and
  ``DemoModel`` in ``demo.py``; ``providers.build_model()`` picks one.
  """
  ```

- Delete `RouterChatModel`, `_rejected_by_provider`, and the imports only they used (`import openai`, the router import, and `logging`/`logger` if nothing else uses them).
- Keep `Message`, `ChatReply`, `ModelError`, `ChatModel` and `response_format_for` unchanged.
- Change the `ModelError` docstring to `"""The model could not be reached, refused the request or failed to answer."""`

- [ ] **Step 4: Rewrite the package exports**

Replace `src/workbench/llm/__init__.py` with:

```python
"""Talking to models.

ChatModel, ChatReply, ModelError   the interface pipelines use (chat.py)
OpenAICompatibleModel, list_models  LM Studio and Ollama (client.py)
DemoModel                           recorded answers for the bundled samples (demo.py)
detect_provider, check_connection, build_model
                                    choosing and reaching a provider (providers.py)
"""

from workbench.llm.chat import ChatModel, ChatReply, ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.llm.demo import DemoModel
from workbench.llm.providers import build_model, check_connection, detect_provider

__all__ = [
    "ChatModel",
    "ChatReply",
    "DemoModel",
    "ModelError",
    "OpenAICompatibleModel",
    "build_model",
    "check_connection",
    "detect_provider",
    "list_models",
]
```

- [ ] **Step 5: Serve a model list from the fake server and move the integration suite to the new client**

In `tests/integration/fake_llm.py`:

- In the module docstring, replace "LLMRouter → OpenAI client → HTTP path" with "OpenAICompatibleModel → HTTP path", and add one line: "``GET /v1/models`` lists an embedding model and ``fake-model``, so detection must skip the first."
- Add to the module:

  ```python
  MODEL_LIST = {
      "object": "list",
      "data": [
          {"id": "text-embedding-nomic-embed-text-v1.5", "object": "model"},
          {"id": "fake-model", "object": "model"},
      ],
  }
  ```

- Add a `do_GET` method to `Handler`, beside `do_POST`:

  ```python
            def do_GET(self) -> None:  # noqa: N802 (http.server API)
                if self.path.rstrip("/") != "/v1/models":
                    self.send_error(404)
                    return
                payload = json.dumps(MODEL_LIST).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
  ```

In `tests/integration/test_pipeline.py`:

- Delete `import os` and the two `workbench.llm` router imports.
- Add `from collections.abc import Iterator` and `from workbench.llm import OpenAICompatibleModel`.
- Replace the `fake_llm` fixture with:

  ```python
  @pytest.fixture(scope="module")
  def fake_llm() -> Iterator[FakeLLM]:
      with FakeLLM() as llm:
          yield llm


  def _model(llm: FakeLLM) -> OpenAICompatibleModel:
      return OpenAICompatibleModel(provider="lm_studio", base_url=llm.base_url, model="fake-model")
  ```

- In both tests, replace `model=RouterChatModel(get_default_router())` with `model=_model(fake_llm)`.
- In `test_heal_loop_repairs_a_drifted_selector`, add after the `prompts` assertion:

  ```python
      # E5 end to end: the healer asked for schema-constrained output.
      healer_calls = [r for r in fake_llm.requests if "response_format" in r]
      assert healer_calls[-1]["response_format"]["type"] == "json_schema"
  ```

- [ ] **Step 6: Update the `AGENTS.md` layout**

In `AGENTS.md`, replace the line

```text
├── llm/                chat.py (ChatModel), router (until Phase 3), parsing, prompts
```

with

```text
├── llm/                chat.py (ChatModel), client.py (LM Studio, Ollama), demo.py, providers.py, parsing, prompts
├── settings.py         the saved model choice: workspace/settings.json
├── samples.py          the bundled samples; install_sample()
```

Replace `samples/site/           sample web app used by tests` with

```text
samples/site/           sample web app the samples run against
samples/specs/          sample specs with a {{BASE_URL}} placeholder
samples/recordings/     the Demo provider's recorded answers
```

and change `workspace/              runtime output (git-ignored): specs/, runs/, reports/` to `workspace/              runtime output (git-ignored): specs/, runs/, reports/, settings.json`.

In the Rules section, change the last bullet to:

```markdown
- `tests/unit/test_layout.py` fails if anything imports the pre-v2 layout (`src.*`, `schemas.*`, benchmarks, Gradio, the tracer), the 1.0 router or `dotenv`.
```

and add:

```markdown
- No environment variables configure the app. The model choice lives in `workspace/settings.json`; `WORKBENCH_WORKSPACE` (and, from Phase 4, `WORKBENCH_PORT`) exist for tests and CI only.
```

- [ ] **Step 7: Run everything**

Run: `uv run python -m pytest -q -o addopts=`
Expected: all pass, including `test_layout.py`.

Run: `uv run python -m pytest tests/integration -q -o addopts=`
Expected: all pass. Both pipeline tests now go through `OpenAICompatibleModel` over HTTP.

Run: `git grep -n -E "dotenv|LM_STUDIO_|OLLAMA_|LLM_PROVIDER|get_default_router|RouterChatModel" -- ':!docs/superpowers' ':!CHANGELOG.md'`
Expected: no output.

Run: `uv run mypy && npm run lint && npm run type-check`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add -u
git add src/workbench/llm/__init__.py src/workbench/llm/chat.py tests/unit/test_chat.py tests/unit/test_layout.py tests/integration/fake_llm.py tests/integration/test_pipeline.py AGENTS.md pyproject.toml uv.lock
git status --short   # only the files above; nothing untracked is staged
git commit -m "refactor!: replace the 1.0 router and .env with the provider client" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: S1, S2 and S4 at pipeline level

**Files:**

- Create: `tests/integration/test_samples.py`
- Modify: `tests/integration/test_heal_guarantees.py` (S4 moves to the checkout sample)

**Interfaces:**

- Consumes:
  - `install_sample`, `SAMPLES`, `GENERATE_SCENARIO` (Task 1)
  - `DemoModel` (Task 3)
  - `detect_provider`, `check_connection`, `build_model`, `load_settings`, `save_settings`, `resolve_settings` (Task 4)
  - `FakeLLM` with `/v1/models` (Task 5)
  - `heal`, `generate`, `load_report` (Phase 2)
- Produces: the phase's proof:
  - S1: a fresh workspace with no server heals the sample through Demo.
  - S2: a running server is detected and used with no configuration.
  - S4: the checkout sample stops without editing the test.

- [ ] **Step 1: Write the tests**

Create `tests/integration/test_samples.py`:

```python
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

    assert report.status == SAMPLES["selector-drift"].expected_status, report.model_dump_json(
        indent=2
    )
    exchange = report.attempts[0].exchange
    assert exchange is not None and exchange.provenance.provider == "demo"
    assert "#submit-btn" not in spec.read_text(encoding="utf-8")
    assert load_report(report.id).status == "healed"


def test_app_bug_sample_stops_without_editing_the_test(site: str) -> None:
    spec = install_sample("app-bug", site)
    original = spec.read_bytes()

    report = heal(HealRequest(spec_path=spec), model=DemoModel())

    assert report.status == SAMPLES["app-bug"].expected_status, report.model_dump_json(indent=2)
    assert [a.outcome for a in report.attempts] == ["app_defect"]
    assert report.attempts[0].rerun is None
    assert spec.read_bytes() == original


def test_demo_generates_a_passing_spec_for_the_sample_scenario(site: str) -> None:
    report = generate(GenerateRequest(url=site, scenario=GENERATE_SCENARIO), model=DemoModel())

    assert report.status == "passed", report.model_dump_json(indent=2)
    assert site in report.code


def test_a_running_server_is_detected_and_used(site: str) -> None:
    with FakeLLM() as llm:
        choice = detect_provider(urls={"lm_studio": UNREACHABLE, "ollama": llm.base_url})
        assert choice == ModelSettings(provider="ollama", base_url=llm.base_url, model="fake-model")

        status = check_connection(choice)
        assert status.reachable and status.models == ["fake-model"]

        report = generate(
            GenerateRequest(url=site, scenario="A user can submit the contact form"),
            model=build_model(choice),
        )

    assert report.status == "passed", report.model_dump_json(indent=2)
    assert report.exchange is not None
    assert report.exchange.provenance.provider == "ollama"
```

- [ ] **Step 2: Run them**

Run: `uv run python -m pytest tests/integration/test_samples.py -v -o addopts=`
Expected: 4 passed.

These tests check behaviour that Tasks 1–5 built, so they may pass on the first run. Prove that each can fail before trusting it. Temporarily make each change below, run the tests, confirm the named test fails, then revert the change:

- Change `"confidence_score": 0.9` to `0.5` in `app-bug.heal.json`. `test_app_bug_sample_stops_without_editing_the_test` must fail.
- Change the `match` in `selector-drift.heal.json` to `"X"`. `test_first_launch_without_a_server_heals_the_sample_with_demo` must fail.
- Remove `"embed"` filtering in `list_models`. `test_a_running_server_is_detected_and_used` must fail.

Record each in the report.

- [ ] **Step 3: Move S4 to the checkout sample**

In `tests/integration/test_heal_guarantees.py`:

- Delete `WRONG_EXPECTATION` and `test_suspected_app_bug_leaves_the_test_alone`. S4 is now proven with the checkout sample in `test_samples.py`, as the spec's S4 row asks.
- Change the module docstring to `"""S3 against a real Chromium with a scripted in-process model (S4 lives in test_samples.py)."""`
- Delete any import that is now unused.

- [ ] **Step 4: Run the integration suite**

Run: `uv run python -m pytest tests/integration -q -o addopts=`
Expected: all pass. That is 12 from Phase 2, minus the moved S4 test, plus the 4 new tests: 15.

Run: `uv run ruff check . && npm run lint`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_samples.py tests/integration/test_heal_guarantees.py
git commit -m "test: prove S1, S2 and S4 with the samples, Demo and a detected server" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Roadmap and changelog

**Files:**

- Modify: `ROADMAP.md`, `CHANGELOG.md`

- [ ] **Step 1: Update `ROADMAP.md`**

- Move the two Phase 3 rows from `Now` to `Done`, with Phase `3` and Plan `[Phase 3](docs/superpowers/plans/2026-10-04-v2-phase-3-providers-and-samples.md)`.
- Move "FastAPI + HTMX web UI matching the Figma design" from `Next` to `Now`, with status `🔭 Planned`, Phase `4` and Plan `Phase 4 plan (to be written)`.
- In `Later`, change the item that ends "…so the Model I/O view shows it; revisit with Phase 3 providers." to end "…so the Model I/O view shows it."
- Add to `Later`:

  ```markdown
  - Cancel an in-flight model call; today a cancel takes effect when the model answers (calls time out after 5 minutes).
  - Warn when a prompt may not fit the model's context window; Ollama silently drops the start of a prompt that is too long.
  ```

- Add to `Removed`:

  ```markdown
  | LLM router with retries and a fallback provider, model registry, `.env` | One client talks to the provider chosen in the UI; the choice is saved in the workspace | 3 |
  ```

- [ ] **Step 2: Update `CHANGELOG.md`**

Under `## [Unreleased]`, add to `### Added`:

```markdown
- LM Studio and Ollama through one OpenAI-compatible client. The first server
  that answers is detected on start, and the model choice is saved in
  `workspace/settings.json`.
- A Demo provider that replays recorded answers, so the bundled samples work
  without a model server.
- Two bundled samples against the sample site: *Selector drift* heals, and
  *App bug* stops without editing the test.
```

to `### Changed`:

```markdown
- A failed model call names the provider and server and says what went wrong
  (not running, timed out, unknown model, or the server's own error).
```

and to `### Removed`:

```markdown
- The LLM router, model registry, retry policies, `python-dotenv` and
  `.env.example`. No environment variable configures the app.
```

- [ ] **Step 3: Lint and commit**

Run: `npm run lint`
Expected: clean (markdownlint included).

```bash
git add ROADMAP.md CHANGELOG.md
git commit -m "docs: record Phase 3 in the roadmap and changelog" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Verify the phase and hand over

**Files:** none change unless a check fails.

- [ ] **Step 1: Run every gate from a clean environment**

```bash
rm -rf .venv node_modules workspace
uv sync --group dev && npm ci && npx playwright install chromium
uv run python -m pytest -q -o addopts= --cov
uv run python -m pytest tests/integration -v -o addopts=
npm run lint && npm run type-check
```

Expected: everything passes, and coverage is reported. The coverage gate itself arrives in Phase 5.

- [ ] **Step 2: Confirm the phase's definition of done**

Run: `env -u LLM_PROVIDER -u LM_STUDIO_URL -u OLLAMA_URL uv run python -m pytest tests/integration/test_samples.py -v -o addopts=`
Expected: 4 passed. S1 and S2 hold with no model environment variables and no `.env`.

Run: `ls .env.example 2>/dev/null; ls workspace 2>/dev/null; git status --short`
Expected: no `.env.example`; no `workspace/` at the repository root after the test runs, because both suites redirect it; a clean tree.

- [ ] **Step 3: Manual check against a real server (optional)**

With LM Studio or Ollama running and a model loaded, run:

```bash
uv run python -c "from workbench.llm import detect_provider; print(detect_provider())"
```

It should print `provider='lm_studio'` or `provider='ollama'`, together with the server's first chat model. This is the manual half of S2; record the result in the report.

- [ ] **Step 4: Ask before pushing**

Show the user `git log --oneline` for the Phase 3 commits. Ask whether to push `v2`, and do not push without a yes.
