"""
QC Crypto Lab — JWT auth layer.
Uses python-jose (JWT) + passlib[bcrypt] for password hashing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt
from passlib.context import CryptContext

from database import SessionLocal, User, RefreshToken

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SECRET_KEY = "qc-crypto-lab-jwt-secret-change-in-production-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT token creation
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create refresh token and persist it to the DB. Returns the encoded JWT."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # Persist to DB
    session = SessionLocal()
    try:
        rt = RefreshToken(
            jti=jti,
            user_id=user_id,
            expires_at=expire,
            revoked=False,
        )
        session.add(rt)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Failed to persist refresh token: %s", exc)
        raise
    finally:
        session.close()

    return token


def verify_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException 401 on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        logger.debug("JWT decode error: %s", exc)
        raise credentials_exception from exc
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    """FastAPI dependency: decode access token, return User ORM object."""
    token = credentials.credentials
    payload = verify_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an access token",
        )

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account deactivated",
            )
        # Detach from session before returning so it can be used outside
        session.expunge(user)
        return user
    finally:
        session.close()


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency: requires admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


def revoke_refresh_token(jti: str) -> bool:
    """Mark a refresh token as revoked. Returns True if found, False otherwise."""
    session = SessionLocal()
    try:
        rt = session.get(RefreshToken, jti)
        if rt is None:
            return False
        rt.revoked = True
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        logger.error("revoke_refresh_token failed: %s", exc)
        return False
    finally:
        session.close()


def validate_refresh_token(token: str) -> dict:
    """Validate a refresh token string; raise HTTPException on failure."""
    payload = verify_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )

    jti = payload.get("jti")
    if jti is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing jti")

    session = SessionLocal()
    try:
        rt = session.get(RefreshToken, jti)
        if rt is None or rt.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or not found",
            )
    finally:
        session.close()

    return payload
