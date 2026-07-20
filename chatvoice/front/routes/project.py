from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.dependencies.paths import RuntimeContext, get_runtime_context

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_class=HTMLResponse)
async def projects_page(
    request: Request,
    ctx: RuntimeContext = Depends(get_runtime_context),  # Single injection
):
    context = {
    }

    """Render the projects list page."""
    return ctx.templates_engine.TemplateResponse(
        request=request,
        name="projects/list.html",
        context=context,
    )

