from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.dependencies.paths import RuntimeContext, get_default_context
from ...crud.projects import crud_projects

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/{project_id}/files", response_class=HTMLResponse)
async def show_list_project_files(
    request: Request,
    project_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
):
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/files_list.html",
        context={"request": request, "project": project},
    )


@router.get("/{project_id}/files/{filename:path}", response_class=HTMLResponse)
async def view_project_files_page(
    request: Request,
    project_id: int,
    filename: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
):
    """Renders the base template with the skeleton loader."""
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="projects/file_editor.html",
        context={"request": request, "project": project, "filename": filename},
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
