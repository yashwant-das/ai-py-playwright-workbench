"""The Jinja environment every page and fragment is rendered with."""

from fastapi.templating import Jinja2Templates

from workbench.config import TEMPLATES_DIR
from workbench.models.heal import REPAIR_STRATEGY_LABELS
from workbench.web import views
from workbench.web.icons import ICON_PATHS

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["duration"] = views.format_duration
templates.env.filters["size"] = views.format_size
templates.env.globals.update(
    ICON_PATHS=ICON_PATHS,
    views=views,
    HEAL_BADGES=views.HEAL_BADGES,
    GENERATE_BADGES=views.GENERATE_BADGES,
    OUTCOME_BADGES=views.OUTCOME_BADGES,
    STRATEGY_LABELS={k.value: v for k, v in REPAIR_STRATEGY_LABELS.items()},
)
