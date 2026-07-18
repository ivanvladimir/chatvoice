
from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException, status
from fastapi.responses import HTMLResponse

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.exceptions.http_exceptions import (
    UnauthorizedException,
    DuplicateValueException,
    ForbiddenException,
    NotFoundException,
    CustomException,
)
from fastapi.templating import Jinja2Templates

from typing import Annotated, Optional

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


