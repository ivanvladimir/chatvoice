import asyncio
import io
import math
import re
import unicodedata
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db, local_session
from ...core.dependencies.paths import RuntimeContext, get_default_context
from ...crud.projects import crud_projects
from ...models.project import Project, ProjectMember
from ...models.user import User
from ...schemas.project import (
    ProjectCreate,
    ProjectCreateInternal,
    ProjectImportInternal,
    ProjectListItem,
    ProjectUpdate,
    ProjectUpdateInternal,
)
from ...schemas.user import UserBrief
from ...utils.markdown import render_markdown
from ...utils.project import (
    GitImportError,
    clone_project_directory,
    create_project_directory,
    derive_project_name_from_git_url,
    list_project_files,
    project_directory_exists,
    validate_git_url,
)
from ..dependencies import get_current_editor, get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory="chatvoice/api/templates")

ALLOWED_EXTENSIONS = {".yaml", ".yml", ".html", ".md", ".txt", ".toml"}
README_FILENAMES = ("README.md", "readme.md", "Readme.md", "README")


# ─── PYDANTIC MODEL FOR CREATE FILE ───
class CreateFileRequest(BaseModel):
    path: str


# ─── DEPENDENCY INJECTION ───
async def get_project_base(
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
) -> tuple[Path, dict]:
    """DRY helper: Fetches project and resolves base path."""
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    base_path = (
        Path("conversations") / current_user["username"] / project["project_name"]
    ).resolve()

    return base_path, project


# ─── HELPERS ───
def _validate_file_path(base_path: Path, file_path_str: str) -> Path:
    """
    Validate a file path is securely inside base_path.
    Uses relative_to() which is mathematically safe against traversal bypasses.
    """
    target = (base_path / file_path_str).resolve()
    try:
        target.relative_to(base_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied.")
    return target


def _create_zip_sync(
    base_path: Path, allowed_extensions: set
) -> tuple[io.BytesIO, int]:
    """Synchronous ZIP creation to be run in a thread."""
    zip_buffer = io.BytesIO()
    file_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
                arcname = file_path.relative_to(base_path)
                zipf.write(file_path, arcname)
                file_count += 1

    zip_buffer.seek(0)
    return zip_buffer, file_count


def normalize_project_name(name: str, max_length: int = 100) -> str:
    """
    Normalize a project name into a GitHub-style slug.
    """
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty")

    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")

    if len(name) > max_length:
        name = name[:max_length].rstrip("-")

    if not name:
        raise ValueError("Project name normalizes to an empty string")

    return name


# ─── ENDPOINTS ───
@router.post("/api/{project_uuid}/files/upload")
async def upload_files(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
    files: list[UploadFile] = FileForm(...),
    directory: str = Form(""),
):
    base_path, project = await get_project_base(project_uuid, db, current_user)

    if not base_path.is_dir():
        raise HTTPException(
            status_code=404, detail="Project directory not found on server."
        )

    # Resolve target directory
    dir_clean = directory.strip().strip("/")
    if dir_clean:
        target_dir = _validate_file_path(base_path, dir_clean)
        await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
    else:
        target_dir = base_path

    uploaded = 0
    skipped = []

    for file in files:
        filename = Path(file.filename).name  # strip any path components
        if not filename:
            continue

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            skipped.append(f"{filename} (extensión no permitida)")
            continue

        dest = _validate_file_path(target_dir, filename)

        if dest.exists():
            skipped.append(f"{filename} (ya existe)")
            continue

        try:
            content = await file.read()  # Async read
            await asyncio.to_thread(dest.write_bytes, content)  # Sync write offloaded
            uploaded += 1
        except Exception as e:
            skipped.append(f"{filename} (error: {e})")

    return {
        "uploaded_count": uploaded,
        "skipped": skipped,
    }


@router.delete("/api/{project_uuid}/files")
async def delete_file(
    request: Request,
    project_uuid: UUID,
    body: CreateFileRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
):
    base_path, project = await get_project_base(project_uuid, db, current_user)
    target_file = _validate_file_path(base_path, body.path.strip())

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not target_file.is_file():
        raise HTTPException(status_code=400, detail="Not a file.")
    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    try:
        await asyncio.to_thread(target_file.unlink)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not delete file: {e}")

    # Clean up empty parent directories (up to the project root)
    parent = target_file.parent
    while parent != base_path and parent.is_dir():
        try:
            await asyncio.to_thread(parent.rmdir)  # only removes if empty
            parent = parent.parent
        except OSError:
            break  # directory not empty, stop

    return {"message": "File deleted", "path": body.path}


@router.get("/{project_uuid}/files/{file_path:path}/download")
async def download_file(
    request: Request,
    project_uuid: UUID,
    file_path: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
):
    base_path, project = await get_project_base(project_uuid, db, current_user)
    target_file = _validate_file_path(base_path, file_path)

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    return FileResponse(
        path=str(target_file),
        filename=target_file.name,
        media_type="application/octet-stream",
    )


@router.get("/{project_uuid}/download")
async def download_project(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
):
    base_path, project = await get_project_base(project_uuid, db, current_user)

    if not base_path.is_dir():
        raise HTTPException(
            status_code=404, detail="Project directory not found on server."
        )

    # Offload blocking ZIP creation to a thread
    zip_buffer, file_count = await asyncio.to_thread(
        _create_zip_sync, base_path, ALLOWED_EXTENSIONS
    )

    if file_count == 0:
        raise HTTPException(
            status_code=404, detail="No supported files found in project."
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{project['project_name']}_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )


@router.post("/api/{project_uuid}/files")
async def create_file(
    request: Request,
    project_uuid: UUID,
    body: CreateFileRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
):
    base_path, project = await get_project_base(project_uuid, db, current_user)
    file_path_str = body.path.strip()

    if not file_path_str:
        raise HTTPException(status_code=400, detail="Path is required.")

    target_file = _validate_file_path(base_path, file_path_str)

    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension not allowed. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if target_file.exists():
        raise HTTPException(status_code=409, detail="File already exists.")

    try:
        await asyncio.to_thread(target_file.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target_file.touch)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not create file: {e}")

    return {"message": "File created", "path": file_path_str}


@router.post("/{project_uuid}/files", response_class=HTMLResponse)
async def list_project_files_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
):
    # Kept using utility functions as in original, but removed duplicate DB fetch
    project = await crud_projects.get(db, uuid=project_uuid)
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


@router.get("/{project_uuid}/readme", response_class=HTMLResponse)
async def get_project_readme_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
):
    """HTMX endpoint: renders the project's README (if any) as sanitized HTML."""
    base_path, project = await get_project_base(project_uuid, db, current_user)

    readme_path = None
    for filename in README_FILENAMES:
        candidate = base_path / filename
        if candidate.is_file():
            readme_path = candidate
            break

    if readme_path is None:
        return HTMLResponse(content="")

    content_text = await asyncio.to_thread(readme_path.read_text, encoding="utf-8")
    _, content_html = render_markdown(content_text)

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/readme_content.html",
        context={
            "request": request,
            "content": content_html,
            "filename": readme_path.name,
        },
    )


@router.post(
    "/{project_uuid}/files/{filename:path}/editor-htmx", response_class=HTMLResponse
)
async def get_file_editor_htmx(
    request: Request,
    project_uuid: UUID,
    filename: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
):
    """HTMX endpoint that reads the file and returns the partial HTML."""
    base_path, project = await get_project_base(project_uuid, db, current_user)
    target_file = _validate_file_path(base_path, filename)

    if not target_file.exists() or target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=404, detail="File not found or unsupported type."
        )

    try:
        content = await asyncio.to_thread(target_file.read_text, encoding="utf-8")
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


@router.post("/{project_uuid}/files/{filename:path}")
async def save_file(
    request: Request,
    project_uuid: UUID,
    filename: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    content: str = Form(...),
    current_user: dict = Depends(get_current_editor),
):
    """Saves the file. Called by standard JS fetch."""
    base_path, project = await get_project_base(project_uuid, db, current_user)
    target_file = _validate_file_path(base_path, filename)

    if target_file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension not allowed. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    try:
        await asyncio.to_thread(target_file.write_text, content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@router.get("/create-form", response_class=HTMLResponse)
async def get_create_form(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
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


@router.get("/import-form", response_class=HTMLResponse)
async def get_import_form(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/import_project_form.html",
        context={
            "request": request,
            "errors": [],
            "name": "",
            "project_name": "",
            "git_url": "",
        },
    )


async def _run_git_import(
    project_uuid: UUID, username: str, project_name: str, git_url: str
) -> None:
    """Background task: clones the repo, then updates the project's status."""
    try:
        await clone_project_directory(username, project_name, git_url)
    except (GitImportError, FileExistsError, OSError) as e:
        async with local_session() as db:
            await crud_projects.update(
                db,
                object=ProjectUpdate(import_status="error", import_error=str(e)[:1000]),
                uuid=project_uuid,
            )
        return

    async with local_session() as db:
        await crud_projects.update(
            db,
            object=ProjectUpdate(import_status="ready"),
            uuid=project_uuid,
        )


@router.post("/import", response_class=HTMLResponse)
async def import_project_htmx(
    request: Request,
    background_tasks: BackgroundTasks,
    name: Annotated[str, Form()],
    git_url: Annotated[str, Form()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
    project_name: Annotated[str | None, Form()] = None,
):
    errors: list[str] = []

    name = name.strip()
    if not name:
        errors.append("El nombre del proyecto es obligatorio")
    elif len(name) > 100:
        errors.append("El nombre no puede superar los 100 caracteres")

    try:
        git_url = validate_git_url(git_url)
    except ValueError as e:
        errors.append(str(e))

    resolved_project_name = ""
    if not errors:
        try:
            resolved_project_name = normalize_project_name(
                (project_name or "").strip()
                or derive_project_name_from_git_url(git_url)
            )
        except ValueError:
            errors.append("No se pudo derivar el nombre clave del proyecto")
        else:
            if project_directory_exists(
                current_user["username"], resolved_project_name
            ):
                errors.append("Un proyecto con el mismo nombre clave ya existe")

    if errors:
        return ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/import_project_form.html",
            context={
                "request": request,
                "errors": errors,
                "name": name,
                "project_name": resolved_project_name,
                "git_url": git_url,
            },
        )

    try:
        project_in = ProjectImportInternal(
            name=name,
            project_name=resolved_project_name,
            owner_id=current_user["id"],
            source_url=git_url,
        )
        new_project = await crud_projects.create(
            db, project_in, schema_to_select=ProjectListItem
        )

        background_tasks.add_task(
            _run_git_import,
            new_project["uuid"],
            current_user["username"],
            resolved_project_name,
            git_url,
        )

        response = ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/create_success.html",
            context={"request": request, "project_name": name},
        )
        response.headers["HX-Trigger"] = "projectCreated"
        return response

    except Exception as e:
        errors.append(f"Error al crear en base de datos: {str(e)}")
        return ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/import_project_form.html",
            context={
                "request": request,
                "errors": errors,
                "name": name,
                "project_name": resolved_project_name,
                "git_url": git_url,
            },
        )


@router.post("/links", response_class=HTMLResponse)
async def project_links_htmx(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
    search: str | None = Form(None),
    sort_by: str = Form("created_at", pattern="^(name|created_at|is_active)$"),
    sort_order: str = Form("desc", pattern="^(asc|desc)$"),
):
    sort_columns = {
        "name": "name",
        "created_at": "created_at",
        "is_active": "is_active",
    }

    projects_result = await crud_projects.get_multi_joined(
        db,
        offset=(page - 1) * items_per_page,
        limit=items_per_page,  # FIXED: was (page) * items_per_page
        sort_columns=[sort_columns[sort_by]],
        sort_orders=[sort_order],
        schema_to_select=ProjectListItem,
        join_model=User,
        join_prefix="owner_",
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
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
    search: str | None = Form(None),
    sort_by: str = Form("created_at", pattern="^(name|created_at|is_active)$"),
    sort_order: str = Form("desc", pattern="^(asc|desc)$"),
):
    sort_columns = {
        "name": "name",
        "created_at": "created_at",
        "is_active": "is_active",
    }

    projects_result = await crud_projects.get_multi(
        db,
        is_deleted=False,
        offset=(page - 1) * items_per_page,
        limit=items_per_page,  # FIXED: was (page) * items_per_page
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
            "username": current_user["username"],
        },
    )


@router.get("/{project_uuid}/card", response_class=HTMLResponse)
async def get_project_card_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
):
    """HTMX endpoint: re-renders a single project card (used to poll import status)."""
    project = await crud_projects.get(
        db, uuid=project_uuid, owner_id=current_user["id"], is_deleted=False
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/project_card.html",
        context={
            "request": request,
            "project": project,
            "username": current_user["username"],
        },
    )


@router.post("/create", response_class=HTMLResponse)
async def create_project_htmx(
    request: Request,
    name: Annotated[str, Form()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    project_name: Annotated[str, Form()],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor),
    description: Annotated[str | None, Form()] = None,
):
    errors: list[str] = []

    name = name.strip()
    project_name = normalize_project_name(project_name.strip())
    description = description.strip() if description else None

    if not name:
        errors.append("El nombre del proyecto es obligatorio")
    elif len(name) > 100:
        errors.append("El nombre no puede superar los 100 caracteres")
    if not project_name:
        errors.append("El nombre clave del proyecto es necesario")  # FIXED: typo

    try:
        project_dir = create_project_directory(
            current_user["username"], project_name, "conversations/hello_world"
        )
    except FileNotFoundError:
        errors.append("El directorio con el proyecto base no está disponible")
    except FileExistsError:
        errors.append("Un proyecto con el mismo nombre clave ya existe")  # FIXED: typo

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
        project_in = ProjectCreate(
            name=name,
            project_name=str(project_name),
            description=description,
        )
        project_data = project_in.model_dump()
        project_data["owner_id"] = current_user["id"]
        project_data = ProjectCreateInternal(**project_data)

        await crud_projects.create(db, project_data)

        response = ctx.templates_api.TemplateResponse(
            request=request,
            name="projects/create_success.html",
            context={"request": request, "project_name": name},
        )
        response.headers["HX-Trigger"] = "projectCreated"
        return response

    except Exception as e:
        # FIXED: Error was being swallowed silently
        errors.append(f"Error al crear en base de datos: {str(e)}")
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


@router.delete("/{project_uuid}", response_class=Response)
async def delete_project_htmx(
    project_uuid: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
):
    project = await crud_projects.get(db, uuid=project_uuid, is_deleted=False)

    # FIXED: Standardized dict access for current_user and project
    if not project or project["owner_id"] != current_user["id"]:
        return HTMLResponse(
            content='<div class="alert alert-error"><span>Proyecto no encontrado</span></div>',
            status_code=404,
        )

    await crud_projects.delete(
        db,
        uuid=project_uuid,
    )

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "projectDeleted"
    return response


@router.patch("/{project_uuid}/toggle-active", response_class=Response)
async def toggle_project_active_htmx(
    project_uuid: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_editor),
):
    project = await crud_projects.get(db, uuid=project_uuid, is_deleted=False)

    # FIXED: Standardized dict access for current_user and project
    if not project or project["owner_id"] != current_user["id"]:
        return HTMLResponse(
            content='<div class="alert alert-error"><span>Proyecto no encontrado</span></div>',
            status_code=404,
        )

    # FIXED: Pass id as kwarg, don't inject it into the schema object
    await crud_projects.update(
        db,
        object=ProjectUpdateInternal(is_active=not project["is_active"]),
        uuid=project_uuid,
    )

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "projectUpdated"
    return response


@router.get("/{project_uuid}/members/list", response_class=HTMLResponse)
async def get_members_list_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: Returns the HTML list of members for the modal."""
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project or project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    # Query members and join with User to get usernames
    stmt = (
        select(ProjectMember, User.username)
        .join(User, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project["id"])
    )
    result = await db.execute(stmt)
    members_data = result.all()

    # Format for template: list of dicts
    members = [
        {
            "id": m.ProjectMember.id,
            "user_id": m.ProjectMember.user_id,
            "username": m.username,
            "permission": m.ProjectMember.permission,
        }
        for m in members_data
    ]
    print(members)

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/members_list.html",
        context={
            "request": request,
            "project_uuid": project_uuid,
            "members": members,
            "owner_id": project["owner_id"],
        },
    )


@router.post("/{project_uuid}/members", response_class=HTMLResponse)
async def add_member_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
    identifier: str = Form(..., min_length=1),
    permission: str = Form(..., pattern="^(view|edit)$"),
):
    """HTMX endpoint: Adds a member and returns the updated list."""
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project or project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Fetch the actual ORM User object by username or email
    user_stmt = select(User).where(
        or_(User.username == identifier, User.email == identifier)
    )
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent adding the owner as a member
    if db_user.id == project["owner_id"]:
        raise HTTPException(
            status_code=400, detail="Cannot add the project owner as a member."
        )

    # Check if already a member
    existing_stmt = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project["id"],
            ProjectMember.user_id == db_user.id,
        )
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a member")

    # 2. Fetch the actual ORM Project object
    # (We do this because crud_projects.get returns a dict, not an ORM object)
    project_stmt = select(Project).where(Project.uuid == project_uuid)
    project_orm_result = await db.execute(project_stmt)
    db_project = project_orm_result.scalar_one_or_none()

    # 3. Instantiate by passing the ORM objects to the relationships
    new_member = ProjectMember(project=db_project, user=db_user, permission=permission)

    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    # Re-fetch the list to return updated HTML
    return await get_members_list_htmx(request, project_uuid, db, ctx, current_user)


@router.delete("/{project_uuid}/members/{user_id}", response_class=Response)
async def remove_member_htmx(
    request: Request,
    project_uuid: UUID,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: Removes a member."""
    project = await crud_projects.get(db, uuid=project_uuid)
    if not project or project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project["id"], ProjectMember.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if member:
        await db.delete(member)
        await db.commit()

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "memberUpdated"
    return response
