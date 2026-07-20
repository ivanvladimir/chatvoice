from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...api.dependencies import get_current_user

router = APIRouter(tags=["default"])

templates = Jinja2Templates(directory="chatvoice/api/templates")


@router.post("/default_protected_load")
async def protected_default_load(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> HTMLResponse:

    return templates.TemplateResponse(
        request=request,
        name="public/default_protected_load.html",
    )
