from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates

from ..dependencies import get_current_user

from ...core.db.database import async_get_db
from ...models.user import User
from ...schemas.project import ProjectCreate
from ...crud.projects import crud_projects

router = APIRouter(prefix="/projects", tags=["projects"])

templates = Jinja2Templates(directory="chatvoice/api/templates")

@router.get("/htmx/create-form", response_class=HTMLResponse)
async def get_create_form(request: Request):
    """Return empty form for the create modal."""
    return templates.TemplateResponse(
        "projects/partials/create_project_form.html",
        {"request": request, "errors": [], "name": "", "directory_path": "", "description": ""},
    )

@router.post("/htmx/list", response_class=HTMLResponse)
async def projects_list_htmx(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    items_per_page: int = Query(12, ge=1, le=50),
    search: str | None = Query(None),
    sort_by: str = Query("created_at", regex="^(name|created_at|is_active)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    """HTMX endpoint: returns paginated project list HTML fragment."""
    
    sort_columns = {"name": "name", "created_at": "created_at", "is_active": "is_active"}

    projects_result = await crud_projects.get_multi(
        db,
        owner_id=current_user['id'],
        is_deleted=False,
        #page=page,
        #items_per_page=items_per_page,
        #search_columns=["name", "description"],
        #search_string=search,
        #sort_columns=[sort_columns[sort_by]],
        #sort_orders=[sort_order],
    )
    
    projects = projects_result.get("data", [])
    total_count = projects_result.get("total_count", 0)
    total_pages = projects_result.get("total_pages", 0)
    
    return templates.TemplateResponse(
        request=request,
        name="projects/partials/project_list.html",
        context={
            "request": request,
            "projects": projects,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "items_per_page": items_per_page,
            "search": search or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    )


@router.post("/htmx/create", response_class=HTMLResponse)
async def create_project_htmx(
    request: Request,
    name: Annotated[str, Form()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    directory_path: Annotated[str, Form()],
    current_user: User = Depends(get_current_user),
    description: Annotated[str | None, Form()] = None,
):
    """HTMX endpoint: create a new project and return updated list or errors."""
    
    # --- Validation ---
    errors: list[str] = []
    
    name = name.strip()
    directory_path = directory_path.strip()
    description = description.strip() if description else None
    
    if not name:
        errors.append("El nombre del proyecto es obligatorio")
    elif len(name) > 100:
        errors.append("El nombre no puede superar los 100 caracteres")
    
    if not directory_path:
        errors.append("La ruta del directorio es obligatoria")
    elif len(directory_path) > 500:
        errors.append("La ruta no puede superar los 500 caracteres")
    
    if errors:
        return templates.TemplateResponse(
            "projects/partials/create_project_form.html",
            {
                "request": request,
                "errors": errors,
                "name": name,
                "directory_path": directory_path,
                "description": description,
            },
        )
    
    # --- Create ---
    project_data = ProjectCreate(
        name=name,
        directory_path=directory_path,
        description=description,
    )
    
    try:
        await crud_projects.create(
            db,
            object_to_create=project_data,
            owner_id=current_user.id,
        )
        
        # Close modal and reload list
        response = templates.TemplateResponse(
            "projects/partials/create_success.html",
            {"request": request, "project_name": name},
        )
        response.headers["HX-Trigger"] = "projectCreated"
        return response
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "unique" in error_msg and "directory_path" in error_msg:
            errors.append("Ya existe un proyecto con esa ruta de directorio")
        else:
            errors.append(f"Error al crear el proyecto: {e}")
        
        return templates.TemplateResponse(
            "projects/partials/create_project_form.html",
            {
                "request": request,
                "errors": errors,
                "name": name,
                "directory_path": directory_path,
                "description": description,
            },
        )


@router.delete("/htmx/{project_id}", response_class=Response)
async def delete_project_htmx(
    project_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
):
    """HTMX endpoint: soft-delete a project."""
    
    project = await crud_projects.get(db, id=project_id, is_deleted=False)
    
    if not project or project.owner_id != current_user.id:
        return HTMLResponse(
            content='<div class="alert alert-error"><span>Proyecto no encontrado</span></div>',
            status_code=404,
        )
    
    await crud_projects.update(
        db,
        object_to_update={
            "is_deleted": True,
            "deleted_at": datetime.now(UTC),
        },
        id=project_id,
    )
    
    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "projectDeleted"
    return response


@router.patch("/htmx/{project_id}/toggle-active", response_class=Response)
async def toggle_project_active_htmx(
    project_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
):
    """HTMX endpoint: toggle project active status."""
    
    project = await crud_projects.get(db, id=project_id, is_deleted=False)
    
    if not project or project.owner_id != current_user.id:
        return HTMLResponse(
            content='<div class="alert alert-error"><span>Proyecto no encontrado</span></div>',
            status_code=404,
        )
    
    await crud_projects.update(
        db,
        object_to_update={"is_active": not project.is_active},
        id=project_id,
    )
    
    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "projectUpdated"
    return response
