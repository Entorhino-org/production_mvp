"""
FastAPI dependencies: DB session, current user, role-based access guards, AI token limits.
"""

from uuid import UUID
from datetime import date
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole, AITokenUsage, AISettings

security_scheme = HTTPBearer()


# ── Get current user from JWT ─────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT bearer token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


# ── Role-based guards ─────────────────────────────────────────

def require_role(*roles: UserRole):
    """Factory that returns a dependency enforcing one of the given roles."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(r.value for r in roles)}",
            )
        return current_user
    return _check


# Convenience shortcuts
require_admin = require_role(UserRole.ADMIN, UserRole.SCHOOL_ADMIN)
require_super_admin = require_role(UserRole.ADMIN)  # System config only
require_teacher = require_role(UserRole.TEACHER)
require_student = require_role(UserRole.STUDENT)
require_parent = require_role(UserRole.PARENT)
require_teacher_or_admin = require_role(UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN)


# ── Verified & approved user check ────────────────────────────

async def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user has verified their email."""
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )
    return current_user


async def require_approved_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user is verified AND approved (for students/teachers needing approval)."""
    if not current_user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified.")
    if current_user.role in (UserRole.STUDENT, UserRole.TEACHER) and not current_user.is_approved:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account pending approval.")
    return current_user


# ── AI token limit checker ────────────────────────────────────

async def check_ai_token_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check if user has remaining AI tokens for today."""
    # Get settings
    result = await db.execute(select(AISettings).limit(1))
    ai_settings = result.scalar_one_or_none()

    if ai_settings:
        limit = (
            ai_settings.daily_student_limit
            if current_user.role == UserRole.STUDENT
            else ai_settings.daily_teacher_limit
        )
    else:
        from app.config import get_settings
        s = get_settings()
        limit = (
            s.DEFAULT_DAILY_STUDENT_TOKEN_LIMIT
            if current_user.role == UserRole.STUDENT
            else s.DEFAULT_DAILY_TEACHER_TOKEN_LIMIT
        )

    # Admin / School Admin has no limit
    if current_user.role in (UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        return current_user

    # Get today's usage
    today = date.today()
    result = await db.execute(
        select(func.coalesce(func.sum(AITokenUsage.tokens_used), 0))
        .where(AITokenUsage.user_id == current_user.id, AITokenUsage.date == today)
    )
    used = result.scalar()

    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI token limit reached ({limit} tokens). Try again tomorrow.",
        )

    return current_user
