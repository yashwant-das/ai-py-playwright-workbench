"""The model menu: test a server, list its models, save the choice."""

from typing import Any, get_args

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    PROVIDER_LABELS,
    ConnectionStatus,
    ModelSettings,
    ProviderName,
)
from workbench.settings import save_settings
from workbench.web.model_state import ModelState
from workbench.web.templating import templates

router = APIRouter()


def _state(request: Request) -> ModelState:
    state: ModelState = request.app.state.model
    return state


def _url_for(provider: str, base_url: str) -> str:
    """The typed URL, unless it is empty or another provider's default."""
    if provider == "demo":
        return ""
    typed = base_url.strip().rstrip("/")
    if not typed or typed in DEFAULT_URLS.values():
        return DEFAULT_URLS[provider]  # type: ignore[index]
    return typed


def _menu(
    request: Request,
    *,
    provider: str,
    base_url: str,
    status: ConnectionStatus,
    selected: str = "",
    error: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    menu: dict[str, Any] = {
        "provider": provider,
        "base_url": base_url,
        "status": status,
        "selected": selected or (status.models[0] if status.models else ""),
        "error": error,
        "providers": list(PROVIDER_LABELS.items()),
    }
    return templates.TemplateResponse(
        request, "partials/model_popover.html", {"menu": menu}, status_code=status_code
    )


def _provider(raw: str) -> ProviderName | None:
    return raw if raw in get_args(ProviderName) else None  # type: ignore[return-value]


@router.get("/model", response_class=HTMLResponse)
def model_menu(request: Request) -> HTMLResponse:
    view = _state(request).view()
    status = view.connection or _state(request).probe(view.provider, view.base_url)
    selected = view.choice.model if view.choice else ""
    return _menu(
        request,
        provider=view.provider,
        base_url=view.base_url,
        status=status,
        selected=selected,
    )


@router.post("/model/test", response_class=HTMLResponse)
def test_model(
    request: Request, provider: str = Form("lm_studio"), base_url: str = Form("")
) -> HTMLResponse:
    chosen = _provider(provider) or "lm_studio"
    url = _url_for(chosen, base_url)
    status = _state(request).probe(chosen, url)
    current = _state(request).choice()
    selected = current.model if current and current.provider == chosen else ""
    return _menu(
        request, provider=chosen, base_url=url, status=status, selected=selected
    )


@router.post("/model", response_model=None)
def save_model(
    request: Request,
    provider: str = Form("lm_studio"),
    base_url: str = Form(""),
    model: str = Form(""),
) -> Response:
    chosen = _provider(provider)
    url = _url_for(chosen or "lm_studio", base_url)
    try:
        if chosen is None:
            raise ValueError(f"Unknown provider {provider!r}.")
        settings = (
            ModelSettings(provider="demo", model=DEMO_MODEL)
            if chosen == "demo"
            else ModelSettings(provider=chosen, base_url=url, model=model.strip())
        )
    except (ValidationError, ValueError) as exc:
        message = (
            exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
        )
        status = ConnectionStatus(
            provider=chosen or "lm_studio", base_url=url, reachable=False
        )
        return _menu(
            request,
            provider=chosen or "lm_studio",
            base_url=url,
            status=status,
            error=message.removeprefix("Value error, "),
            status_code=422,
        )
    save_settings(settings)
    return Response(status_code=200, headers={"HX-Refresh": "true"})
