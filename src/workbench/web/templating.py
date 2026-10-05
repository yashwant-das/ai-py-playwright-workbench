"""The Jinja environment every page and fragment is rendered with."""

from fastapi.templating import Jinja2Templates

from workbench.config import TEMPLATES_DIR
from workbench.web.icons import ICON_PATHS

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["ICON_PATHS"] = ICON_PATHS
