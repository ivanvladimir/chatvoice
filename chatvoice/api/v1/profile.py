from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.dependencies.paths import RuntimeContext, get_default_context
from ...crud.users import crud_users
from ...schemas.user import UserProfileUpdate
from ..dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_class=HTMLResponse)
async def get_profile_htmx(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: renders the current user's profile view + edit form."""
    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/profile_content.html",
        context={
            "request": request,
            "user": current_user,
            "errors": [],
            "success": False,
        },
    )


@router.post("/update", response_class=HTMLResponse)
async def update_profile_htmx(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
    institution: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    profile_image_url: Annotated[str | None, Form()] = None,
):
    """HTMX endpoint: validates and saves the current user's 'normal' profile info."""
    errors: list[str] = []
    # Reflect whatever the user submitted back into the form on error, but
    # keep read-only fields (username, role, created_at, ...) from the DB.
    user_view = {
        **current_user,
        "name": name,
        "email": email,
        "institution": institution,
        "description": description,
        "profile_image_url": profile_image_url,
    }

    try:
        profile = UserProfileUpdate(
            name=name.strip(),
            email=email.strip(),
            institution=(institution or "").strip() or None,
            description=(description or "").strip() or None,
            profile_image_url=(profile_image_url or "").strip() or None,
        )
    except ValidationError as e:
        errors.extend(err["msg"] for err in e.errors())
        return ctx.templates_api.TemplateResponse(
            request=request,
            name="user/profile_content.html",
            context={
                "request": request,
                "user": user_view,
                "errors": errors,
                "success": False,
            },
        )

    try:
        await crud_users.update(db, object=profile.model_dump(), id=current_user["id"])
    except Exception as e:
        if (
            "UNIQUE constraint failed: users.email" in str(e)
            or "unique" in str(e).lower()
            and "email" in str(e).lower()
        ):
            errors.append("Ese correo ya está en uso por otra cuenta.")
        else:
            errors.append(f"No se pudo actualizar el perfil: {e}")
        return ctx.templates_api.TemplateResponse(
            request=request,
            name="user/profile_content.html",
            context={
                "request": request,
                "user": user_view,
                "errors": errors,
                "success": False,
            },
        )

    updated_user = await crud_users.get(db, id=current_user["id"])
    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/profile_content.html",
        context={
            "request": request,
            "user": updated_user,
            "errors": [],
            "success": True,
        },
    )
