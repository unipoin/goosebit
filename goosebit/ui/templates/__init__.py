from pathlib import Path
from typing import Any

import jinja2
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from goosebit.auth import check_permissions


def attach_permissions_comparison(_: Request) -> dict[str, Any]:
    return {"compare_permissions": check_permissions}


# Autoescaping must be enabled explicitly: a custom Environment does not inherit Starlette's default,
# and templates render values that are controlled by devices and users.
env = jinja2.Environment(
    loader=jinja2.ChoiceLoader([jinja2.FileSystemLoader(str(Path(__file__).resolve().parent))]),
    autoescape=True,
)
templates = Jinja2Templates(context_processors=[attach_permissions_comparison], env=env)


def add_template_handler(handler: Jinja2Templates) -> None:
    if hasattr(templates.env.loader, "loaders"):
        templates.env.loader.loaders.append(handler.env.loader)


templates.add_template_handler = add_template_handler  # type: ignore[attr-defined]
