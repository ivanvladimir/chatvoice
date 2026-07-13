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


# =============================================================================
# Password Utilities
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash.
    
    Note: This is intentionally synchronous as bcrypt is CPU-bound.
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.
    
    Note: This is intentionally synchronous as bcrypt is CPU-bound.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# =============================================================================
# Authentication
# =============================================================================

async def authenticate_user(
    username_or_email: str, 
    password: str, 
    db: AsyncSession
) -> dict[str, Any] | None:
    """Authenticate a user by username or email.
    
    Returns user dict if valid credentials, None otherwise.
    """
    if "@" in username_or_email:
        db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False, is_verified=True)
    else:
        db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False, is_verified=True)

    if not db_user:
        return None

    if not verify_password(password, db_user["hashed_password"]):
        return None

    return db_user


# =============================================================================
# JWT Token Creation
# =============================================================================

def _create_token(
    data: dict[str, Any],
    token_type: TokenType,
    expires_delta: timedelta | None = None,
) -> str:
    """Internal helper to create a JWT token with proper expiration."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        default_deltas = {
            TokenType.ACCESS: timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            TokenType.REFRESH: timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        }
        # Verification tokens should always have explicit expiration
        if token_type not in default_deltas:
            raise ValueError(f"Token type '{token_type}' requires explicit expires_delta")
        expire = datetime.now(UTC) + default_deltas[token_type]
    
    to_encode.update({
        "exp": expire,
        "token_type": token_type,
    })
    
    return jwt.encode(to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)


async def create_access_token(
    data: dict[str, Any], 
    expires_delta: timedelta | None = None
) -> str:
    """Create an access token."""
    return _create_token(data, TokenType.ACCESS, expires_delta)


async def create_refresh_token(
    data: dict[str, Any], 
    expires_delta: timedelta | None = None
) -> str:
    """Create a refresh token."""
    return _create_token(data, TokenType.REFRESH, expires_delta)


def create_verification_token(
    email: str, 
    token_type: Literal[TokenType.EMAIL_VERIFICATION, TokenType.PASSWORD_RESET],
    expires_delta: timedelta,
) -> str:
    """Create a verification or password reset token.
    
    These tokens are:
    - Not blacklisted (single-use, time-limited)
    - Tied to an email, not a username
    - Must have explicit expiration
    """
    return _create_token(
        data={"sub": email},
        token_type=token_type,
        expires_delta=expires_delta,
    )


# =============================================================================
# JWT Token Verification
# =============================================================================

async def verify_token(
    token: str, 
    expected_token_type: TokenType, 
    db: AsyncSession
) -> TokenData | None:
    """Verify an auth token (access/refresh) and return TokenData if valid.
    
    Checks blacklist and token type. Returns None if invalid.
    """
    is_blacklisted = await crud_token_blacklist.exists(db, token=token)
    if is_blacklisted:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        
        if payload.get("token_type") != expected_token_type:
            return None
            
        username_or_email = payload.get("sub")
        if not username_or_email:
            return None

        return TokenData(username_or_email=username_or_email)

    except JWTError:
        return None


def decode_verification_token(
    token: str,
    expected_type: Literal[TokenType.EMAIL_VERIFICATION, TokenType.PASSWORD_RESET],
) -> str:
    """Decode and validate a verification/reset token.
    
    Returns the email from the token.
    
    Raises:
        CustomException: If token is expired, invalid, or wrong type.
    """
    from .exceptions.http_exceptions import CustomException
    
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY.get_secret_value(), 
            algorithms=[ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise CustomException(status_code=401, detail="El token ha expirado. Solicita un nuevo token.")
    except jwt.InvalidTokenError:
        raise CustomException(status_code=401, detail="El token proporcionado es incorrecto.")

    email = payload.get("sub")
    token_type = payload.get("token_type")

    if not email or token_type != expected_type:
        raise CustomException(status_code=401, detail="El token proporcionado es incorrecto.")

    return email


# =============================================================================
# Token Blacklisting
# =============================================================================

async def _blacklist_single_token(token: str, db: AsyncSession) -> None:
    """Blacklist a single token by extracting its expiration from the payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp is not None:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=UTC)
            await crud_token_blacklist.create(
                db, 
                object=TokenBlacklistCreate(token=token, expires_at=expires_at)
            )
    except JWTError:
        # If token is invalid, it's effectively "blacklisted" already
        pass


async def blacklist_token(token: str, db: AsyncSession) -> None:
    """Blacklist a single token."""
    await _blacklist_single_token(token, db)


async def blacklist_tokens(access_token: str, refresh_token: str, db: AsyncSession) -> None:
    """Blacklist both access and refresh tokens.
    
    Continues blacklisting even if one token fails.
    """
    await _blacklist_single_token(access_token, db)
    await _blacklist_single_token(refresh_token, db)
