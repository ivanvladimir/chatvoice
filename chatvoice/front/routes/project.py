from datetime import UTC, datetime
from typing import Annotated

import os
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.dependencies.paths import RuntimeContext, get_runtime_context
from ...crud.projects import crud_projects

from ...core.db.database import async_get_db
from ...models.user import User
from ...utils.project import project_directory_exists, list_project_files

router = APIRouter(prefix="/projects", tags=["projects"])



@router.get("/{project_id}/files", response_class=HTMLResponse)
async def list_project_files(
        request: Request, 
        project_id: int,
        db: Annotated[AsyncSession, Depends(async_get_db)],
        ctx: RuntimeContext = Depends(get_runtime_context),  # Single injection
):
    project = await crud_projects.get(db, id=project_id)
    if not project: 
        raise HTTPException(status_code=404, detail="Project not found.")
 
    return ctx.templates_engine.TemplateResponse(
        request=request,
        name="projects/files_list.html",
        context={
        "request": request,
        "project": project
    })

@router.get("/{project_id}/files/{filename:path}", response_class=HTMLResponse)
async def view_project_files_page(
        request: Request,
        project_id: int, 
        filename: str,
        db: Annotated[AsyncSession, Depends(async_get_db)],
        ctx: RuntimeContext = Depends(get_runtime_context),  # Single injection
):
    """Renders the base template with the skeleton loader."""
    project = await crud_projects.get(db, id=project_id)
    if not project: 
        raise HTTPException(status_code=404, detail="Project not found.")
 
    return ctx.templates_engine.TemplateResponse(
        request=request,
        name="projects/file_editor.html",
        context={
        "request": request,
        "project": project,
        "filename": filename
    })



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

