"""The web app factory: tests build it with fake services, the launcher with real ones."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from workbench import config
from workbench.runs import RunRegistry
from workbench.web.model_state import ModelState
from workbench.web.routes import generate as generate_routes
from workbench.web.routes import heal as heal_routes
from workbench.web.routes import model as model_routes
from workbench.web.routes import reports as reports_routes
from workbench.web.routes import runs as run_routes
from workbench.web.services import Services


def create_app(services: Services | None = None, *, port: int | None = None) -> FastAPI:
    """Build the app; ``port`` only sets the sample-site address the app reports."""
    app = FastAPI(
        title="Playwright Workbench", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.services = services or Services()
    app.state.base_url = config.base_url(port)
    app.state.model = ModelState(app.state.services)
    app.state.runs = RunRegistry()
    app.include_router(model_routes.router)
    app.include_router(run_routes.router)
    app.include_router(heal_routes.router)
    app.include_router(generate_routes.router)
    app.include_router(reports_routes.router)
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
    app.mount(
        "/sample-site",
        StaticFiles(directory=config.SAMPLE_SITE_DIR, html=True),
        name="sample-site",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def home() -> RedirectResponse:
        return RedirectResponse("/heal", status_code=303)

    return app
