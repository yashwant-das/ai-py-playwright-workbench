"""
Fake OpenAI-compatible LLM server for the end-to-end suite.

Serves ``POST /v1/chat/completions`` with scripted answers so the real
LLMRouter → OpenAI client → HTTP path runs in CI without a model:

  - generator prompts (``USER STORY:``) get a Playwright spec that targets the
    ``TARGET URL`` from the prompt;
  - healer prompts (``BROKEN CODE:``) get a HealingAnalysis that swaps the
    drifted ``#submit-btn`` selector for ``[data-testid="submit"]``.

Every request body is kept in ``FakeLLM.requests`` so tests can assert on the
context the pipeline actually sent.
"""

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GENERATED_SPEC = """```typescript
import {{ test, expect }} from "@playwright/test";

test("User can submit the contact form", async ({{ page }}) => {{
  await page.goto("{url}");
  await page.getByLabel("Name").fill("Ada");
  await page.getByRole("button", {{ name: "Submit" }}).click();
  await expect(page.getByRole("status")).toHaveText("Submitted");
}});
```"""

HEALING_ANALYSIS = {
    "failure_type": "LOCATOR_DRIFT",
    "failure_summary": "#submit-btn no longer exists on the page",
    "hypothesis": "The submit button is now identified by data-testid='submit'.",
    "confidence_score": 0.9,
    "confidence_rationale": "The DOM context shows a single submit button with a test id.",
    "reasoning_steps": [
        "The click on #submit-btn timed out.",
        "The DOM has <button data-testid='submit'> and no #submit-btn.",
    ],
    "root_cause_evidence": ['button[data-testid="submit"] present in DOM'],
    "action_taken": {
        "original_code": 'page.locator("#submit-btn")',
        "fixed_code": "page.locator('[data-testid=\"submit\"]')",
        "description": "Replace the drifted #submit-btn selector with the test id.",
        "repair_strategy": "selector_replace",
    },
}


def _answer(messages: list[dict]) -> str:
    user = next((m["content"] for m in messages if m["role"] == "user"), "")
    if "BROKEN CODE:" in user:
        return json.dumps(HEALING_ANALYSIS)
    match = re.search(r"TARGET URL:\s*(\S+)", user)
    if match:
        return GENERATED_SPEC.format(url=match.group(1))
    return "Unrecognised prompt"


class FakeLLM:
    """Threaded fake LLM server; use as a context manager."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        fake = self
        self.requests: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 (http.server API)
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                fake.requests.append(body)
                content = _answer(body.get("messages", []))
                payload = json.dumps(
                    {
                        "id": f"chatcmpl-fake-{len(fake.requests)}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": body.get("model", "fake-model"),
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": content},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 50,
                            "total_tokens": 150,
                        },
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args) -> None:
                pass

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/v1"

    def prompts_containing(self, marker: str) -> list[str]:
        """Return the user prompts of recorded requests that contain ``marker``."""
        prompts = []
        for body in self.requests:
            for message in body.get("messages", []):
                if message["role"] == "user" and marker in message["content"]:
                    prompts.append(message["content"])
        return prompts

    def __enter__(self) -> "FakeLLM":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
