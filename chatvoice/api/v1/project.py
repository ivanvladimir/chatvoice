import io
import math
import re
import unicodedata
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi import File as FileForm
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.dependencies.paths import RuntimeContext, get_default_context
from ...crud.projects import crud_projects
from ...models.user import User
from ...schemas.project import (
    ProjectCreate,
    ProjectCreateInternal,
    ProjectListItem,
    ProjectUpdateInternal,
)
from ...schemas.user import UserBrief
from ...utils.project import (
    create_project_directory,
    list_project_files,
    project_directory_exists,
)
from ..dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory="chatvoice/api/templates")

ALLOWED_EXTENSIONS = {".yaml", ".yml", ".html", ".md", ".txt"}


# ─── PYDANTIC MODEL FOR CREATE FILE ───
class CreateFileRequest(BaseModel):
    path: str


def _get_project_base_path(current_user: dict, project: dict) -> Path:
    """Helper: build and resolve the project base path."""
    return (
        Path("conversations") / current_user["username"] / project["project_name"]
    ).resolve()


def _validate_file_path(base_path: Path, file_path_str: str) -> Path:
    """
    Validate a file path is inside base_path and has an allowed extension.
    Returns the resolved target Path.
    Raises HTTPException on violations.
    """
    target = (base_path / file_path_str).resolve()

    # Directory traversal check
    if not str(target).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="Access denied.")

    return target


@router.post("/api/{project_id}/files/upload")
async def upload_files(
    request: Request,
    project_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
    files: list[UploadFile] = FileForm(...),
    directory: str = Form(""),
):
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = _get_project_base_path(current_user, project)
    if not base_path.is_dir():
        raise HTTPException(
            status_code=404, detail="Project directory not found on server."
        )

    # Resolve target directory
    dir_clean = directory.strip().strip("/")
    if dir_clean:
        target_dir = (base_path / dir_clean).resolve()
        if not str(target_dir).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="Access denied.")
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = base_path

    uploaded = 0
    skipped = []

    for file in files:
        # Sanitize filename
        filename = Path(file.filename).name  # strip any path components
        if not filename:
            continue

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if f".{ext}" not in ALLOWED_EXTENSIONS:
            skipped.append(f"{filename} (extensión no permitida)")
            continue

        dest = (target_dir / filename).resolve()
        # Final traversal check per file
        if not str(dest).startswith(str(target_dir)):
            skipped.append(f"{filename} (acceso denegado)")
            continue

        if dest.exists():
            skipped.append(f"{filename} (ya existe)")
            continue

        try:
            content = await file.read()
            dest.write_bytes(content)
            uploaded += 1
        except Exception as e:
            skipped.append(f"{filename} (error: {e})")

    return {
        "uploaded_count": uploaded,
        "skipped": skipped,
    }


@router.delete("/api/{project_id}/files")
async def delete_file(
    request: Request,
    project_id: int,
    body: CreateFileRequest,  # reuse { "path": "..." }
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
):
    """Delete a single file from the project."""
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = _get_project_base_path(current_user, project)
    target_file = _validate_file_path(base_path, body.path.strip())

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not target_file.is_file():
        raise HTTPException(status_code=400, detail="Not a file.")
    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    try:
        target_file.unlink()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not delete file: {e}")

    # Clean up empty parent directories (up to the project root)
    parent = target_file.parent
    while parent != base_path and parent.is_dir():
        try:
            parent.rmdir()  # only removes if empty
            parent = parent.parent
        except OSError:
            break  # directory not empty, stop

    return {"message": "File deleted", "path": body.path}


@router.get("/{project_id}/files/{file_path:path}/download")
async def download_file(
    request: Request,
    project_id: int,
    file_path: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
):
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = _get_project_base_path(current_user, project)
    target_file = _validate_file_path(base_path, file_path)

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not target_file.is_file():
        raise HTTPException(status_code=400, detail="Not a file.")
    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    return FileResponse(
        path=str(target_file),
        filename=target_file.name,
        media_type="application/octet-stream",
    )


@router.get("/{project_id}/download")
async def download_project(
    request: Request,
    project_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
):
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = _get_project_base_path(current_user, project)

    if not base_path.is_dir():
        raise HTTPException(
            status_code=404, detail="Project directory not found on server."
        )

    # Build ZIP in memory – only allowed extensions
    zip_buffer = io.BytesIO()
    file_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                arcname = file_path.relative_to(base_path)
                zipf.write(file_path, arcname)
                file_count += 1

    if file_count == 0:
        raise HTTPException(
            status_code=404, detail="No supported files found in project."
        )

    zip_buffer.seek(0)

    # Clean filename: use project_name (already a slug) + timestamp
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{project['project_name']}_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )


@router.post("/api/{project_id}/files")
async def create_file(
    request: Request,
    project_id: int,
    body: CreateFileRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: User = Depends(get_current_user),
):
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    file_path_str = body.path.strip()
    if not file_path_str:
        raise HTTPException(status_code=400, detail="Path is required.")

    base_path = _get_project_base_path(current_user, project)
    target_file = _validate_file_path(base_path, file_path_str)

    # Validate extension
    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension not allowed. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Prevent overwriting
    if target_file.exists():
        raise HTTPException(status_code=409, detail="File already exists.")

    # Create parent directories and the empty file
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.touch()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not create file: {e}")

    return {"message": "File created", "path": file_path_str}


@router.post("/{project_id}/files", response_class=HTMLResponse)
async def list_project_files_htmx(
    request: Request,
    project_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    current_user: User = Depends(get_current_user),
):
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project_directory_exists(current_user["username"], project["project_name"]):
        raise HTTPException(
            status_code=404, detail="Project directory not found on server."
        )

    files = list_project_files(
        current_user["username"],
        project["project_name"],
        allowed_extensions=ALLOWED_EXTENSIONS,
    )

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/files_list_content.html",
        context={"request": request, "project": project, "files": files},
    )


@router.post(
    "/{project_id}/files/{filename:path}/editor-htmx", response_class=HTMLResponse
)
async def get_file_editor_htmx(
    request: Request,
    project_id: int,
    filename: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    current_user: User = Depends(get_current_user),
    base_path: str = "conversations",
):
    """HTMX endpoint that reads the file and returns the partial HTML."""
    # 1. Fetch your project (Replace with your actual dependency/DB call)
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = Path(base_path) / current_user["username"] / project["project_name"]

    # SECURITY: Resolve paths to prevent directory traversal
    safe_base = base_path.resolve()
    target_file = (base_path / filename).resolve()

    if not str(target_file).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not target_file.exists() or target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        # You could create an error partial here, for simplicity we raise 500
        raise HTTPException(
            status_code=404, detail="File not found or unsupported type."
        )

    try:
        content = target_file.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/file_editor_content.html",
        context={
            "request": request,
            "project": project,
            "filename": filename,
            "content": content,
        },
    )


@router.post("/{project_id}/files/{filename:path}")
async def save_file(
    request: Request,
    project_id: int,
    filename: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    content: str = Form(...),
    current_user: User = Depends(get_current_user),
    base_path: str = "conversations",
):
    """Saves the file. Called by standard JS fetch."""
    # project = await crud_projects.get(db, id=project_id)
    # if not project: raise HTTPException(404)
    project = await crud_projects.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = Path(base_path) / current_user["username"] / project["project_name"]

    # SECURITY CHECK AGAIN
    safe_base = base_path.resolve()
    target_file = (base_path / filename).resolve()

    if not str(target_file).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        target_file.write_text(content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@router.get("/create-form", response_class=HTMLResponse)
async def get_create_form(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    current_user: User = Depends(get_current_user),
):
    """Return empty form for the create modal."""
    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/create_project_form.html",
        context={
            "request": request,
            "errors": [],
            "name": "",
            "project_name": "",
            "description": "",
        },
    )


@router.post("/links", response_class=HTMLResponse)
async def project_links_htmx(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    current_user: User = Depends(get_current_user),
    # --- CHANGED Query TO Form HERE ---
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
    search: str | None = Form(None),
    sort_by: str = Form("created_at", pattern="^(name|created_at|is_active)$"),
    sort_order: str = Form("desc", pattern="^(asc|desc)$"),
):
    """HTMX endpoint: returns paginated project list HTML fragment."""
    sort_columns = {
        "name": "name",
        "created_at": "created_at",
        "is_active": "is_active",
    }

    # WARNING: Make sure to remove the hardcoded f"%mi%" in your actual code!
    # You probably want: name__ilike=f"%{search}%" if search else None
    projects_result = await crud_projects.get_multi_joined(
        db,
        offset=(page - 1) * items_per_page,
        limit=(page) * items_per_page,
        sort_columns=[sort_columns[sort_by]],
        sort_orders=[sort_order],
        schema_to_select=ProjectListItem,
        join_model=User,
        join_prefix="owner_",  # or see nested option below
        join_schema_to_select=UserBrief,
        is_deleted=False,
        is_active=True,
        _or={
            "name__ilike": f"%{search}%",
            "description__ilike": f"%{search}%",
        }
        if search
        else {},
    )

    projects = [p for p in projects_result.get("data", []) if not p["owner_is_deleted"]]
    total_count = projects_result.get("total_count", 0)

    # Fixed math to return an integer instead of a float (e.g., 5 instead of 5.0)
    total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/project_links.html",
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


@router.post("/list", response_class=HTMLResponse)
async def projects_list_htmx(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    current_user: User = Depends(get_current_user),
    # --- CHANGED Query TO Form HERE ---
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
    search: str | None = Form(None),
    sort_by: str = Form("created_at", pattern="^(name|created_at|is_active)$"),
    sort_order: str = Form("desc", pattern="^(asc|desc)$"),
):
    """HTMX endpoint: returns paginated project list HTML fragment."""
    sort_columns = {
        "name": "name",
        "created_at": "created_at",
        "is_active": "is_active",
    }

    # WARNING: Make sure to remove the hardcoded f"%mi%" in your actual code!
    # You probably want: name__ilike=f"%{search}%" if search else None
    projects_result = await crud_projects.get_multi(
        db,
        is_deleted=False,
        offset=(page - 1) * items_per_page,
        limit=(page) * items_per_page,
        sort_columns=[sort_columns[sort_by]],
        sort_orders=[sort_order],
        owner_id=current_user["id"],
        _or={
            "name__ilike": f"%{search}%",
            "description__ilike": f"%{search}%",
        }
        if search
        else {},
    )

    projects = projects_result.get("data", [])
    total_count = projects_result.get("total_count", 0)

    # Fixed math to return an integer instead of a float (e.g., 5 instead of 5.0)
    total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/project_list.html",
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
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
    current_user: User = Depends(get_current_user),
    description: Annotated[str | None, Form()] = None,
):
    """HTMX endpoint: create a new project and return updated list or errors."""

    # --- Validation ---
    errors: list[str] = []

    name = name.strip()
    project_name = normalize_project_name(project_name.strip())
    description = description.strip() if description else None

    if not name:
        errors.append("El nombre del proyecto es obligatorio")
    elif len(name) > 100:
        errors.append("El nombre no puede superar los 100 caracteres")
    if not project_name:
        errors.append("El nombre clave del proyecto es necessario")

    try:
        project_dir = create_project_directory(
            current_user["username"], project_name, "conversations/hello_world"
        )
    except FileNotFoundError:
        errors.append("El directorio con el proyecto base no está disponible")
    except FileExistsError:
        errors.append("Un proyecto con el mismo nombre clave ya esxiste")

    if errors:
        return ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/create_project_form.html",
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
        project_data["owner_id"] = current_user["id"]
        project_data = ProjectCreateInternal(**project_data)

        await crud_projects.create(db, project_data)

        # Close modal and reload list
        response = ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/create_success.html",
            context={"request": request, "project_name": name},
        )
        response.headers["HX-Trigger"] = "projectCreated"
        return response

    except Exception as e:
        error_msg = str(e).lower()

        return ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/create_project_form.html",
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
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: toggle project active status."""

    project = await crud_projects.get(db, id=project_id, is_deleted=False)

    if not project or project["owner_id"] != current_user["id"]:
        return HTMLResponse(
            content='<div class="alert alert-error"><span>Proyecto no encontrado</span></div>',
            status_code=404,
        )

    await crud_projects.update(
        db,
        object=ProjectUpdateInternal(
            **{"is_active": not project["is_active"], "id": project["id"]}
        ),
    )

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "projectUpdated"
    return response
