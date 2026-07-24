from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...api.dependencies import get_current_user

router = APIRouter(tags=["chatbot"])

templates = Jinja2Templates(directory="chatvoice/api/templates")




@router.post("/chatbot/{script}")
@router.post("/chatbot/{username}/{script}")
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
            'url_start': request.url_for('establish_ws_session', script=script, username=username), 
            'url_ws': request.url_for('websocket_endpoint', script=script, username=username),
        }
    )
