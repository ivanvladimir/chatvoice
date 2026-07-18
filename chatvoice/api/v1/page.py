from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...api.dependencies import get_current_user
from ...core.dependencies.paths import RuntimeContext, get_runtime_context
from typing import Annotated
from ...utils.markdown import render_markdown_page

router = APIRouter(tags=["content"])

@router.get("/page/{view}")
async def get_current_user_info(
    request: Request,
    view: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    ctx: RuntimeContext = Depends(get_runtime_context) # Single injection
) -> HTMLResponse:
    """Get current authenticated user info."""
    return render_markdown_page(view, "public/page.html", request, ctx)



