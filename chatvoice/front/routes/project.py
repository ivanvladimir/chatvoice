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



@router.get("/{project_id}/files/{filename}", response_class=HTMLResponse)
async def view_edit_file(
        request: Request, 
        project_id: int, 
        filename: str,
        ctx: RuntimeContext = Depends(get_runtime_context),  # Single injection
):
    # Mock project
    project = type('Obj', (object,), {'directory_path': './sample_project_dir', 'name': 'My Project'})()
    base_path = get_project_base_path(project)

    # SECURITY: Resolve paths to prevent directory traversal (e.g. ../../etc/passwd)
    safe_base = base_path.resolve()
    target_file = (base_path / filename).resolve()

    if not str(target_file).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied.")
    
    if not target_file.exists() or target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=404, detail="File not found or unsupported type.")

    # Read file content
    try:
        content = target_file.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    return ctx.templates_engine.TemplateResponse("projects/file_editor.html", {
        "request": request,
        "project": project,
        "filename": filename,
        "content": content
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

