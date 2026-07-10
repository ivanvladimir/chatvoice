from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user, get_current_superuser
from ...core.exceptions.http_exceptions import (
    UnauthorizedException,
    DuplicateValueException,
    ForbiddenException,
    NotFoundException,
    CustomException,
)
#from ...core.utils import queue
from ...core.schemas import Token
from ...schemas.user import UserCreate, UserRead, UserCreateInternal
from ...crud.users import crud_users
from ...core.security import (
    TokenType,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_verification_token,
    verify_token,
    get_password_hash,
)
from ...core.types import UserRole

router = APIRouter(prefix="/auth",tags=["auth"])


# =============================================================================
# Pydantic Models
# =============================================================================

class LoginRequest(BaseModel):
    """JSON login request body for HTMX/Alpine.js frontend."""
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Login response with access token and user info."""
    access_token: str
    token_type: str = "bearer"
    username: str
    name: str


class UserResponse(BaseModel):
    """Current user info response."""
    id: int
    username: str
    name: str
    email: str
    is_verified: bool
    role: UserRole


class RegisterRequest(BaseModel):
    """JSON registration request body."""
    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    role: UserRole
    password: str = Field(..., min_length=8, max_length=100)
    institution: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
 
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ResetPasswordRequest(BaseModel):
    """Reset password request body."""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class MessageResponse(BaseModel):
    """Generic message response."""
    status: str = "success"
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

def clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        path="/",  # Must match the path used when setting
        secure=settings.ENVIRONMENT == "production",
        httponly=True,
        samesite="lax",
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh token cookie with proper security settings."""
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=max_age,
        path="/",
    )

# =============================================================================
# Auth Endpoints (for HTMX/Alpine.js frontend)
# =============================================================================

@router.post("/login/json", response_model=LoginResponse)
async def login_json(
    response: Response,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    data: LoginRequest,
) -> LoginResponse:
    """
    Login endpoint for JSON requests (HTMX/Alpine.js).
    Returns access token and user info, sets refresh token as cookie.
    """
    user = await authenticate_user(username_or_email=data.username, password=data.password, db=db)
    if not user:
        raise UnauthorizedException("Usuario, email o contraseña incorrectos.")

    access_token = await create_access_token(data={"sub": user["username"]})
    refresh_token = await create_refresh_token(data={"sub": user["username"]})

    set_refresh_cookie(response, refresh_token)

    return LoginResponse(
        access_token=access_token,
        username=user["username"],
        name=user["name"],
    )


@router.post("/login", response_model=Token)
async def login_form(
    response: Response,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    Login endpoint for OAuth2 form data (Swagger UI, traditional forms).
    """
    user = await authenticate_user(username_or_email=form_data.username, password=form_data.password, db=db)
    if not user:
        raise UnauthorizedException("Usuario, email o contraseña incorrectos.")

    access_token = await create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = await create_refresh_token(data={"sub": user["username"]})

    set_refresh_cookie(response, refresh_token)

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user info."""
    return UserResponse(**current_user)


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> Token:
    """
    Refresh access token using refresh token from cookie.
    Clears cookie if refresh token is invalid.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        clear_refresh_cookie(response)
        raise UnauthorizedException("Refresh token missing.")

    user_data = await verify_token(refresh_token, TokenType.REFRESH, db)
    if not user_data:
        clear_refresh_cookie(response)
        raise UnauthorizedException("Invalid refresh token.")

    new_access_token = await create_access_token(data={"sub": user_data.username_or_email})
    return Token(access_token=new_access_token, token_type="bearer")


@router.post("/logout")
async def logout(response: Response) -> MessageResponse:
    """Logout by clearing the refresh token cookie."""
    clear_refresh_cookie(response)
    return MessageResponse(message="Sesión cerrada exitosamente.")


# =============================================================================
# Registration Endpoints
# =============================================================================

@router.post("/register/json", status_code=status.HTTP_201_CREATED)
async def register_user_json(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    data: RegisterRequest,
) -> JSONResponse:
    """Register user from JSON request body."""
    return await _register_user(
        db=db,
        request=request,
        name=data.name,
        username=data.username,
        email=data.email,
        role=data.role,
        password=data.password,
        institution=data.institution,
        description=data.description,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user_form(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    institution: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
) -> JSONResponse:
    """Register user from form data."""
    return await _register_user(
        db=db,
        request=request,
        name=name,
        username=username,
        role=role,
        email=email,
        password=password,
        institution=institution,
        description=description,
    )


async def _register_user(
    db: AsyncSession,
    request: Request,
    name: str,
    username: str,
    role: UserRole,
    email: str,
    password: str,
    institution: Optional[str],
    description: Optional[str],
) -> JSONResponse:
    """Shared registration logic."""
    try:
        user = UserCreate(
            name=name,
            username=username,
            email=email,
            role=role,
            password=password,
            institution=institution,
            description=description,
        )
    except ValidationError as e:
        errors = "; ".join(err["msg"] for err in e.errors())
        raise CustomException(status_code=422, detail=f"Error en los valores proporcionados: {errors}")

    # Check for duplicates
    if await crud_users.exists(db=db, email=user.email):
        raise DuplicateValueException("El email ya está registrado.")

    if await crud_users.exists(db=db, username=user.username):
        raise DuplicateValueException("El nombre de usuario no está disponible.")

    # Create user
    user_internal_dict = user.model_dump()
    user_internal_dict["hashed_password"] = get_password_hash(password=user_internal_dict.pop("password"))
    user_internal = UserCreateInternal(**user_internal_dict)

    created_user = await crud_users.create(
        db=db,
        object=user_internal,
        schema_to_select=UserRead,
        return_as_model=True,
    )

    if not created_user:
        raise CustomException(status_code=500, detail="Error al crear el usuario.")

    # Send verification email
    verification_token = create_verification_token(
        email=user.email, 
        token_type=TokenType.EMAIL_VERIFICATION, # Use Enum
        expires_delta=timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES), # Required now
    )
    
    verification_url = str(request.url_for("email_verification")) + f"?token={verification_token}"
    
    #job = await queue.pool.enqueue_job(
    #    "send_email_task",
    #    "Verificación de cuenta - AATI",
    #    [user.email],
    #    f"""
    #    <p>Su correo <strong>{user.email}</strong> ha sido registrado exitosamente en AATI.</p>
    #    
    #    <p>Para verificar su cuenta, haga clic en el siguiente enlace:</p>
    #    <p><a href="{verification_url}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Verificar mi cuenta</a></p>
    #    
    #    <p style="margin-top: 20px; color: #666;">Si usted no se registró en AATI, por favor ignore este correo.</p>
    #    """,
    #)

    if not job:
        # User was created but email failed - log this, don't fail the request
        pass  # Consider adding logging here

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": f"Cuenta creada exitosamente. Se enviará un correo a {user.email} para verificar la cuenta.",
            "user": {
                "id": created_user.id,
                "name": user.name,
                "role": user.role,
                "username": user.username,
                "email": user.email,
            },
        },
    )


# =============================================================================
# Email Verification Endpoints
# =============================================================================

@router.post("/verify_email")
async def verify_email(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> JSONResponse:
    """Verify user email using token."""
    data = await request.json()
    token = data.get("token")

    if not token:
        raise CustomException(status_code=422, detail="Token no proporcionado.")

    email = decode_verification_token(token, TokenType.EMAIL_VERIFICATION)

    user_read = await crud_users.get(
        db=db,
        email=email,
        schema_to_select=UserRead,
        return_as_model=True,
    )

    if not user_read:
        raise NotFoundException("Usuario no encontrado.")

    if user_read.is_verified:
        raise CustomException(status_code=422, detail="Esta cuenta ya ha sido verificada.")

    updated_user = await crud_users.update(
        db=db,
        object={"is_verified": True},
        id=user_read.id,
        schema_to_select=UserRead,
        return_as_model=True,
    )

    if not updated_user:
        raise CustomException(status_code=500, detail="Error al verificar el correo. Contacte al administrador.")

    return JSONResponse(
        content={
            "status": "success",
            "message": "Email verificado correctamente. Ya puede acceder a la plataforma.",
            "redirect_url": str(request.url_for("main")),
        }
    )


# =============================================================================
# Password Reset Endpoints
# =============================================================================

@router.post("/request_reset_password/json")
async def request_reset_password_json(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    data: dict,
) -> MessageResponse:
    """Request password reset from JSON body."""
    email = data.get("email")
    if not email:
        raise CustomException(status_code=422, detail="Email no proporcionado.")
    return await _request_reset_password(db=db, request=request, email=email)


@router.post("/request_reset_password")
async def request_reset_password_form(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    email: str = Form(...),
) -> MessageResponse:
    """Request password reset from form data."""
    return await _request_reset_password(db=db, request=request, email=email)


async def _request_reset_password(
    db: AsyncSession,
    request: Request,
    email: str,
) -> MessageResponse:
    """Shared password reset request logic."""
    user = await crud_users.get(
        db=db,
        email=email,
        schema_to_select=UserRead,
        return_as_model=True,
    )

    if not user:
        # Don't reveal if email exists or not (security best practice)
        return MessageResponse(message="Si el email está registrado, recibirá un correo para restablecer la contraseña.")

    reset_token = create_verification_token(
        email=user.email, 
        token_type=TokenType.PASSWORD_RESET, # Use Enum
        expires_delta=timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES), # Required now
    )
    reset_url = str(request.url_for("reset_password")) + f"?token={reset_token}"

    job = await queue.pool.enqueue_job(
        "send_email_task",
        "Solicitud de cambio de contraseña - AATI",
        [user.email],
        f"""
        <p>Se ha solicitado cambiar la contraseña para la cuenta asociada a <strong>{user.email}</strong> en AATI.</p>
        
        <p>Si reconoce esta solicitud, haga clic en el siguiente enlace:</p>
        <p><a href="{reset_url}" style="padding: 10px 20px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px;">Cambiar contraseña</a></p>
        
        <p style="margin-top: 20px; color: #666;">Si usted no hizo esta solicitud, por favor ignore este correo.</p>
        """,
    )

    if not job:
        raise CustomException(status_code=500, detail="Error al enviar el correo. Contacte al administrador.")

    return MessageResponse(message="Si el email está registrado, recibirá un correo para restablecer la contraseña.")


@router.post("/reset_password")
async def reset_password(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    data: ResetPasswordRequest,
) -> JSONResponse:
    """Reset user password using token."""
    email = decode_verification_token(data.token, TokenType.PASSWORD_RESET)

    user_read = await crud_users.get(
        db=db,
        email=email,
        schema_to_select=UserRead,
        return_as_model=True,
    )

    if not user_read:
        raise NotFoundException("Usuario no encontrado.")

    if not user_read.is_verified:
        raise CustomException(status_code=422, detail="El usuario no ha sido verificado. Verifique su email primero.")

    updated_user = await crud_users.update(
        db=db,
        object={"hashed_password": get_password_hash(password=data.new_password)},
        id=user_read.id,
        schema_to_select=UserRead,
        return_as_model=True,
    )

    if not updated_user:
        raise CustomException(status_code=500, detail="Error al actualizar la contraseña. Contacte al administrador.")

    return JSONResponse(
        content={
            "status": "success",
            "message": "La contraseña ha sido actualizada correctamente.",
            "redirect_url": str(request.url_for("main")),
        }
    )
