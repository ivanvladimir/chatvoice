from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.v1.conversations import HISTOGRAM_VIEWS, HistogramMetric
from ...core.db.database import async_get_db
from ...core.dependencies.paths import RuntimeContext, get_default_context
from ...crud.projects import crud_projects

router = APIRouter(prefix="/projects", tags=["projects"])


def _carried_filters(username_regex: str | None, min_turns: int | None) -> dict:
    """Stats filters passed between the stats views as query params."""
    filters: dict = {}
    if username_regex is not None:
        filters["username_regex"] = username_regex
    if min_turns is not None:
        filters["min_turns"] = min_turns
    return filters


@router.get("/{project_uuid}/files", response_class=HTMLResponse)
async def show_list_project_files(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
):
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/files_list.html",
        context={"request": request, "project": project},
    )


@router.get("/{project_uuid}/files/{filename:path}", response_class=HTMLResponse)
async def view_project_files_page(
    request: Request,
    project_uuid: UUID,
    filename: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
):
    """Renders the base template with the skeleton loader."""
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/file_editor.html",
        context={"request": request, "project": project, "filename": filename},
    )


@router.get("/{project_uuid}/conversations", response_class=HTMLResponse)
async def show_project_conversations(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
):
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/conversations.html",
        context={"request": request, "project": project},
    )


@router.get("/{project_uuid}/stats", response_class=HTMLResponse)
async def show_project_stats(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    username_regex: str | None = Query(None),
    min_turns: int | None = Query(None, ge=0),
):
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/stats.html",
        context={
            "request": request,
            "project": project,
            # Filters carried over from the sibling stats view, if any
            "filters": _carried_filters(username_regex, min_turns),
        },
    )


@router.get("/{project_uuid}/stats/{metric}", response_class=HTMLResponse)
async def show_project_histogram(
    request: Request,
    project_uuid: UUID,
    metric: HistogramMetric,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    username_regex: str | None = Query(None),
    min_turns: int | None = Query(None, ge=0),
):
    """Histogram page for one stats metric; content loads from the HTMX endpoint."""
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/stats_histogram.html",
        context={
            "request": request,
            "project": project,
            "metric": metric,
            "title": HISTOGRAM_VIEWS[metric]["title"],
            # Filters carried over from the sibling stats view, if any
            "filters": _carried_filters(username_regex, min_turns),
        },
    )


@router.get("/", response_class=HTMLResponse)
async def projects_page(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
):
    context = {}

    """Render the projects list page."""
    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/list.html",
        context=context,
    )
