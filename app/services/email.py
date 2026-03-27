"""
Email service — sends OTPs via Resend.
"""

import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import resend
import logging

logger = logging.getLogger(__name__)

from app.models.user import OTPCode, OTPPurpose


async def _get_resend_config(db: AsyncSession):
    """Get Resend API key and from email from cached settings."""
    from app.services.ai import get_cached_setting, _ensure_cache
    await _ensure_cache(db)
    api_key = get_cached_setting("resend_api_key", "")
    from_email = get_cached_setting("resend_from_email", "")
    return api_key, from_email


def _generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return "".join(random.choices(string.digits, k=6))


async def send_otp_email(
    db: AsyncSession,
    email: str,
    purpose: OTPPurpose = OTPPurpose.EMAIL_VERIFY,
    expiry_minutes: int = 10,
) -> str:
    """
    Generate an OTP, store it in the database, and send it via Resend.
    Returns the OTP code (useful for testing).
    """
    code = _generate_otp()

    # Store OTP in database
    otp = OTPCode(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
    )
    db.add(otp)
    await db.flush()

    # Subject line based on purpose
    if purpose == OTPPurpose.EMAIL_VERIFY:
        subject = "Entorhino — Verify Your Email"
        body = f"""
        <h2>Welcome to Entorhino!</h2>
        <p>Your verification code is:</p>
        <h1 style="color: #4F46E5; letter-spacing: 8px; font-size: 36px;">{code}</h1>
        <p>This code expires in {expiry_minutes} minutes.</p>
        <p>If you didn't request this, please ignore this email.</p>
        """
    else:
        subject = "Entorhino — Parent Link Verification"
        body = f"""
        <h2>Parent Linking Request</h2>
        <p>A parent/guardian is trying to link to your account.</p>
        <p>Share this code with them:</p>
        <h1 style="color: #4F46E5; letter-spacing: 8px; font-size: 36px;">{code}</h1>
        <p>This code expires in {expiry_minutes} minutes.</p>
        <p>If you didn't expect this, please ignore this email.</p>
        """

    # Send via Resend — dynamically load config from DB
    try:
        api_key, from_email = await _get_resend_config(db)
        resend.api_key = api_key
        resend.Emails.send({
            "from": from_email,
            "to": [email],
            "subject": subject,
            "html": body,
        })
    except Exception as e:
        # Log but don't crash — the OTP is still stored
        logger.warning(f"[EMAIL ERROR] Failed to send to {email}: {e}")

    # Always log OTP to console for dev convenience
    logger.debug(f"\n{'='*50}")
    logger.info(f"  📧 OTP for {email}: {code}")
    logger.debug(f"  Purpose: {purpose.value}")
    logger.debug(f"{'='*50}\n")

    return code


async def verify_otp(
    db: AsyncSession,
    email: str,
    code: str,
    purpose: OTPPurpose = OTPPurpose.EMAIL_VERIFY,
) -> bool:
    """Verify an OTP code. Returns True if valid, False otherwise."""
    result = await db.execute(
        select(OTPCode)
        .where(
            OTPCode.email == email,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.used == False,
            OTPCode.expires_at > datetime.utcnow(),
        )
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    )
    otp = result.scalar_one_or_none()

    if otp is None:
        return False

    # Mark as used
    otp.used = True
    await db.flush()
    return True
