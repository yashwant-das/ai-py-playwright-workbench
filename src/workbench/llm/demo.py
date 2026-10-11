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
    for index, header in enumerate(headers):
        following = headers[index + 1 :][:1]
        end = following[0].start() if following else len(prompt)
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
