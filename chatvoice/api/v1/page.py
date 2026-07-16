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

router = APIRouter(tags=["content"])

@router.get("/page/{view}")
async def get_current_user_info(
    view: str
    current_user: Annotated[dict, Depends(get_current_user)],
    ctx: RuntimeContext = Depends(get_runtime_context) # Single injection
) -> HTMLResponse:
    """Get current authenticated user info."""
    return render_markdown_page(view, "public/page.html", request, ctx)


