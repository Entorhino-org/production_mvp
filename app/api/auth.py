"""
Auth API — register, verify OTP, login, refresh token, resend OTP.
Handles multi-step signup for student/teacher/parent roles.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole, OTPPurpose
from app.schemas.auth import (
    RegisterRequest, VerifyOTPRequest, LoginRequest,
    TokenResponse, RefreshRequest, ResendOTPRequest, UserBasic,
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_refresh_token,
)
from app.core.rate_limit import limiter, get_client_ip
from app.services.email import send_otp_email, verify_otp

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 5 registrations per minute per IP (Redis-backed)
    await limiter.check_async(f"register:{get_client_ip(request)}", max_requests=5, window_seconds=60)
    """
    Step 1: Register with email, password, name, phone, role.
    An OTP is sent to the email for verification.
    """
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Admin is auto-approved AND auto-verified (no OTP needed)
    is_admin = (req.role == UserRole.ADMIN)

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        phone=req.phone,
        role=req.role,
        is_email_verified=is_admin,
        is_approved=is_admin,
    )

    # Set role-specific fields
    if req.role == UserRole.PARENT and req.relationship_type:
        user.relationship_type = req.relationship_type

    db.add(user)
    await db.flush()

    # Admin skips OTP — everyone else verifies via email
    if not is_admin:
        await send_otp_email(db, req.email, OTPPurpose.EMAIL_VERIFY)

    # For admin, return tokens so they can login immediately
    if is_admin:
        tokens = _create_tokens(user)
        tokens["message"] = "Admin account created. You are now logged in."
        return tokens

    return {
        "message": "Registration successful. Please check your email for the OTP.",
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }


@router.post("/verify-otp")
async def verify_otp_endpoint(req: VerifyOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 10 attempts per minute per email (Redis-backed)
    await limiter.check_async(f"verify-otp:{req.email}", max_requests=10, window_seconds=60)
    """Verify email using OTP code."""
    valid = await verify_otp(db, req.email, req.code, OTPPurpose.EMAIL_VERIFY)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Mark user as email verified
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_email_verified = True
    await db.flush()

    # Generate tokens so user is logged in after verification
    tokens = _create_tokens(user)
    return tokens


@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 10 login attempts per minute per IP (Redis-backed)
    await limiter.check_async(f"login:{get_client_ip(request)}", max_requests=10, window_seconds=60)
    """Login with email and password. Returns JWT tokens."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Let unverified users login so frontend can redirect to OTP page
    tokens = _create_tokens(user)
    return tokens


@router.post("/refresh")
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Get new access token using refresh token."""
    payload = decode_refresh_token(req.refresh_token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    tokens = _create_tokens(user)
    return tokens


@router.post("/resend-otp")
async def resend_otp(req: ResendOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 3 OTP resends per minute per email (Redis-backed)
    await limiter.check_async(f"resend-otp:{req.email}", max_requests=3, window_seconds=60)
    """Resend OTP to the email."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    await send_otp_email(db, req.email, OTPPurpose.EMAIL_VERIFY)
    return {"message": "OTP sent successfully"}


def _create_tokens(user: User) -> dict:
    """Helper to create access + refresh tokens and return response."""
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_email_verified": user.is_email_verified,
            "is_approved": user.is_approved,
        },
    }
