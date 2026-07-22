from datetime import UTC, datetime
from typing import Annotated
import re
import unicodedata

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates

from ..dependencies import get_current_user

from ...core.db.database import async_get_db
from ...models.user import User
from ...schemas.project import ProjectCreate, ProjectCreateInternal
from ...crud.projects import crud_projects
from ...utils.project import create_project_directory

router = APIRouter(prefix="/projects", tags=["projects"])

templates = Jinja2Templates(directory="chatvoice/api/templates")

@router.get("/create-form", response_class=HTMLResponse)
async def get_create_form(request: Request):
    """Return empty form for the create modal."""
    return templates.TemplateResponse(
        request=request,
        name="projects/partials/create_project_form.html",
        context={"request": request, "errors": [], "name": "", "project_name": "", "description": ""},
    )

@router.post("/list", response_class=HTMLResponse)
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


def normalize_project_name(name: str, max_length: int = 100) -> str:
    """
    Normalize a project name into a GitHub-style slug.

    Example:
        "My Awesome Project!!" -> "my-awesome-project"
        "  Héllo   World_2024 " -> "hello-world-2024"
        "café___déjà-vu" -> "cafe-deja-vu"
    """
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty")

    # Transliterate accented characters to ASCII (é -> e, ñ -> n, etc.)
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    name = name.lower()

    # Replace any run of non-alphanumeric characters with a single hyphen
    name = re.sub(r"[^a-z0-9]+", "-", name)

    # Trim leading/trailing hyphens
    name = name.strip("-")

    # Enforce max length without cutting mid-hyphen
    if len(name) > max_length:
        name = name[:max_length].rstrip("-")

    if not name:
        raise ValueError("Project name normalizes to an empty string")

    return name

@router.post("/create", response_class=HTMLResponse)
async def create_project_htmx(
    request: Request,
    name: Annotated[str, Form()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    project_name: Annotated[str, Form()],
    current_user: User = Depends(get_current_user),
    description: Annotated[str | None, Form()] = None,
):
    """HTMX endpoint: create a new project and return updated list or errors."""
    
    # --- Validation ---
    errors: list[str] = []
    
    name = name.strip()
    project_name=normalize_project_name(project_name.strip())
    description = description.strip() if description else None
    
    if not name:
        errors.append("El nombre del proyecto es obligatorio")
    elif len(name) > 100:
        errors.append("El nombre no puede superar los 100 caracteres")
    if not project_name:
        errors.append("El nombre clave del proyecto es necessario")

    try:
        project_dir=create_project_directory(current_user['username'], project_name, "conversations/hello_world")
    except FileNotFoundError:
        errors.append("El directorio con el proyecto base no está disponible")
    except FileExistsError:
        errors.append("Un proyecto con el mismo nombre clave ya esxiste")


    if errors:
        return templates.TemplateResponse(
            request=request,
            name="projects/partials/create_project_form.html",
            context={
                "request": request,
                "errors": errors,
                "name": name,
                "project_name": project_name,
                "description": description,
            },
        )
    
    try:
        # --- Create ---
        project_in = ProjectCreate(
            name=name,
            project_name=str(project_name),
            description=description,
        )
        project_data = project_in.model_dump()
        project_data["owner_id"] = current_user['id']
        project_data = ProjectCreateInternal(**project_data)
    
        await crud_projects.create(
            db,
            project_data)

        # Close modal and reload list
        response = templates.TemplateResponse(
            request=request,
            name="projects/partials/create_success.html",
            context={"request": request, "project_name": name},
        )
        response.headers["HX-Trigger"] = "projectCreated"
        return response
        
    except Exception as e:
        error_msg = str(e).lower()
        print(">>>>>>> aaaaa",e)
        
        return templates.TemplateResponse(
            request=request,
            name="projects/partials/create_project_form.html",
            context={
                "request": request,
                "errors": errors,
                "name": name,
                "project_name": project_name,
                "description": description,
            },
        )


@router.delete("/{project_id}", response_class=Response)
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


@router.patch("/{project_id}/toggle-active", response_class=Response)
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
