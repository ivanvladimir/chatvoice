from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.dependencies.paths import RuntimeContext, get_project_context
from ...utils.markdown import markdown_page, render_markdown_page

router = APIRouter(tags=["main"])

@router.get("/", response_class=HTMLResponse)
async def main(
    request: Request,
    ctx: RuntimeContext = Depends(get_project_context),  # Single injection
) -> HTMLResponse:
    """Principal"""
    md, notlogged_content = markdown_page("main_notlogged", ctx)

    context = {
        "notlogged_content": notlogged_content,
        "metadata": md.Meta,
        "active_page": md.Meta.get("active_page", [None])[0],
        "active_menu": md.Meta.get("active_menu", [None])[0],
    }

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/main.html",
        context=context,
    )




@router.get("/chat/{script}", response_class=HTMLResponse)
@router.get("/chat/{username}/{script}", response_class=HTMLResponse)
async def chat(
    request: Request,
    script: str,
    ctx: RuntimeContext = Depends(get_project_context),  # Single injection
    username: str = None,
) -> HTMLResponse:
    """Chat interface"""

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/chatbot.html",
        context={
            "script": script,
            "username": username,
            "active_page": "main",
            "active_menu": None,
            'url_start': 
            request.url_for('establish_ws_session', script=script, username=username) if username else request.url_for('establish_ws_session_', script=script), 
            'url_ws':
            request.url_for('websocket_endpoint', script=script, username=username) if username else request.url_for('websocket_endpoint_', script=script) 
        }
    )


