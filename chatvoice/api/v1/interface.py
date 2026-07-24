from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...api.dependencies import get_current_user

router = APIRouter(tags=["chatbot"])

templates = Jinja2Templates(directory="chatvoice/api/templates")


@router.post("/chatbot/{script}", name="chatbot_interface_")
@router.post("/chatbot/{username}/{script}", name="chatbot_interface")
async def chatbot_interface(
    script: str,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    username: str = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="user/chatbot_interface.html",
        context={
            'url_start': 
            request.url_for('establish_ws_session', script=script, username=username) if username else request.url_for('establish_ws_session_', script=script), 
            'url_ws':
            request.url_for('websocket_endpoint', script=script, username=username) if username else request.url_for('websocket_endpoint_', script=script) 
        }
    )
