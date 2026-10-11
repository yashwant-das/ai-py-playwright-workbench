"""Talking to models.

ChatModel, ChatReply, ModelError   the interface pipelines use (chat.py)
cancellable, ModelCancelled         stop waiting for a model once a run is cancelled
OpenAICompatibleModel, list_models  LM Studio and Ollama (client.py)
DemoModel                           recorded answers for the bundled samples (demo.py)
detect_provider, check_connection, build_model
                                    choosing and reaching a provider (providers.py)
"""

from workbench.llm.cancellable import ModelCancelled, cancellable
from workbench.llm.chat import ChatModel, ChatReply, ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.llm.demo import DemoModel
from workbench.llm.providers import build_model, check_connection, detect_provider

__all__ = [
    "ChatModel",
    "ChatReply",
    "DemoModel",
    "ModelCancelled",
    "ModelError",
    "OpenAICompatibleModel",
    "build_model",
    "cancellable",
    "check_connection",
    "detect_provider",
    "list_models",
]
