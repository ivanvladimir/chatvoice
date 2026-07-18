from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.users import crud_users
from .config import settings
from .db.crud_token_blacklist import crud_token_blacklist
from .schemas import TokenBlacklistCreate, TokenData

# =============================================================================
# Configuration
# =============================================================================

SECRET_KEY: SecretStr = settings.SECRET_KEY
ALGORITHM: str = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
WS_SESSION_EXPIRE_MINUTES: int = settings.WS_SESSION_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS: int = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


# =============================================================================
# Enums
# =============================================================================

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    WS_SESSION = "ws_session"


# =============================================================================
# Password Utilities
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# =============================================================================
# Authentication
# =============================================================================

async def authenticate_user(username_or_email: str, password: str, db: AsyncSession) -> dict[str, Any] | None:
    if "@" in username_or_email:
        db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False, is_verified=True)
    else:
        db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False, is_verified=True)

    if not db_user or not verify_password(password, db_user["hashed_password"]):
        return None
    return db_user


# =============================================================================
# JWT Token Creation
# =============================================================================

def _create_token(data: dict[str, Any], token_type: TokenType, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        default_deltas = {
            TokenType.ACCESS: timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            TokenType.REFRESH: timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        }
        if token_type not in default_deltas:
            raise ValueError(f"Token type '{token_type}' requires explicit expires_delta")
        expire = datetime.now(UTC) + default_deltas[token_type]
    
    to_encode.update({
        "exp": expire,
        "token_type": token_type,
    })
    
    return jwt.encode(to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)


# --- CHANGED: Made synchronous, shortened default expire time ---
def create_ws_session_token(
    data: dict[str, Any], 
    expires_delta: timedelta | None = timedelta(minutes=15) # Short lifespan!
) -> str:
    """Create a short-lived WebSocket session token. No DB blacklist check needed."""
    return _create_token(data, TokenType.WS_SESSION, expires_delta)


async def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    return _create_token(data, TokenType.ACCESS, expires_delta)

async def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    return _create_token(data, TokenType.REFRESH, expires_delta)

def create_verification_token(
    email: str, 
    token_type: Literal[TokenType.EMAIL_VERIFICATION, TokenType.PASSWORD_RESET],
    expires_delta: timedelta,
) -> str:
    return _create_token(data={"sub": email}, token_type=token_type, expires_delta=expires_delta)


# =============================================================================
# JWT Token Verification
# =============================================================================

async def verify_token(token: str, expected_token_type: TokenType, db: AsyncSession) -> TokenData | None:
    """Verify an HTTP auth token. Checks the DB blacklist."""
    is_blacklisted = await crud_token_blacklist.exists(db, token=token)
    if is_blacklisted:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        if payload.get("token_type") != expected_token_type or not payload.get("sub"):
            return None
        return TokenData(username_or_email=payload.get("sub"))
    except JWTError:
        return None


def decode_verification_token(
    token: str,
    expected_type: Literal[TokenType.EMAIL_VERIFICATION, TokenType.PASSWORD_RESET],
) -> str:
    from .exceptions.http_exceptions import CustomException
    
    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise CustomException(status_code=401, detail="El token ha expirado. Solicita un nuevo token.")
    except jwt.InvalidTokenError:
        raise CustomException(status_code=401, detail="El token proporcionado es incorrecto.")

    email = payload.get("sub")
    if not email or payload.get("token_type") != expected_type:
        raise CustomException(status_code=401, detail="El token proporcionado es incorrecto.")
    return email


# --- CHANGED: Renamed to be specific, returns None instead of raising HTTP errors ---
def decode_ws_token(token: str) -> dict | None:
    """Decode a WebSocket token. 
    
    Returns the payload dict if valid, None if expired/invalid.
    Does NOT check the DB blacklist (WS tokens are short-lived).
    Does NOT raise HTTP exceptions (breaks WebSockets).
    """
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY.get_secret_value(), 
            algorithms=[ALGORITHM],
        )
    except JWTError:
        return None

    if not payload or payload.get("token_type") != TokenType.WS_SESSION:
        return None

    return payload


# =============================================================================
# Token Blacklisting
# =============================================================================

async def _blacklist_single_token(token: str, db: AsyncSession) -> None:
    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp is not None:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=UTC)
            await crud_token_blacklist.create(db, object=TokenBlacklistCreate(token=token, expires_at=expires_at))
    except JWTError:
        pass

async def blacklist_token(token: str, db: AsyncSession) -> None:
    await _blacklist_single_token(token, db)

async def blacklist_tokens(access_token: str, refresh_token: str, db: AsyncSession) -> None:
    await _blacklist_single_token(access_token, db)
    await _blacklist_single_token(refresh_token, db)


