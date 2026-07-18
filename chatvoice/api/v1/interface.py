from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...api.dependencies import get_current_user
from fastapi.templating import Jinja2Templates
from typing import Annotated

router = APIRouter(tags=["chatbot"])

templates = Jinja2Templates(directory="chatvoice/api/templates")


@router.post("/chatbot")
async def chatbot_interface(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> HTMLResponse:

    return templates.TemplateResponse(
        request=request,
        name="user/chatbot_interface.html",
    )
