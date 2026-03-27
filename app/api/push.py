"""
Web Push Notifications API — subscribe, unsubscribe, and send push notifications.
Push delivery runs in background threads to avoid blocking the event loop.
"""

import json
import asyncio
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db, async_session
from app.models.user import User, UserRole
from app.models.communication import PushSubscription
from app.core.dependencies import get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/push", tags=["Push Notifications"])


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe_push(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save or update a push subscription for the current user."""
    endpoint = req.get("endpoint")
    p256dh = req.get("keys", {}).get("p256dh")
    auth = req.get("keys", {}).get("auth")

    if not endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Missing subscription data")

    # Upsert: remove old subscription with same endpoint
    await db.execute(
        delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    await db.flush()

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
    )
    db.add(sub)
    await db.flush()
    return {"message": "Push subscription saved"}


@router.post("/unsubscribe")
async def unsubscribe_push(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a push subscription."""
    endpoint = req.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Missing endpoint")
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == current_user.id,
        )
    )
    await db.flush()
    return {"message": "Push subscription removed"}


def _sync_webpush(subscription_info: dict, payload: str) -> str | None:
    """Synchronous webpush call — runs in thread pool via asyncio.to_thread.
    Returns subscription endpoint if stale (410/404), None otherwise."""
    from pywebpush import webpush, WebPushException
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_MAILTO},
        )
        return None
    except WebPushException as e:
        if "410" in str(e) or "404" in str(e):
            return subscription_info["endpoint"]  # stale
        logger.warning("[PUSH] Error: %s", str(e)[:100])
        return None
    except Exception as e:
        logger.warning("[PUSH] Unexpected error: %s", e)
        return None


async def send_push_to_user(db: AsyncSession, user_id, title: str, body: str, url: str = "/dashboard"):
    """Send push notification to all subscriptions of a user.
    webpush calls run in thread pool so they don't block the event loop."""
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subs = result.scalars().all()
    if not subs:
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": "/static/icon-192.png",
    })

    # Run all webpush calls in parallel threads
    tasks = []
    sub_map = {}  # endpoint -> sub.id
    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        sub_map[sub.endpoint] = sub.id
        tasks.append(asyncio.to_thread(_sync_webpush, subscription_info, payload))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Clean up stale subscriptions
    stale_ids = []
    for r in results:
        if isinstance(r, str) and r in sub_map:
            stale_ids.append(sub_map[r])
    if stale_ids:
        await db.execute(
            delete(PushSubscription).where(PushSubscription.id.in_(stale_ids))
        )
        await db.flush()


async def _background_push_task(user_ids: list, title: str, body: str, url: str):
    """Fire-and-forget background task that sends push to multiple users.
    Uses its own DB session so it doesn't block the caller's session."""
    try:
        async with async_session() as db:
            for uid in user_ids:
                try:
                    await send_push_to_user(db, uid, title, body, url)
                except Exception:
                    pass  # Never crash the background task
            await db.commit()
    except Exception as e:
        logger.warning("[PUSH BG] Background push failed: %s", e)


def fire_push_background(user_ids: list, title: str, body: str, url: str = "/dashboard"):
    """Schedule push notifications as a fire-and-forget background task.
    Call this instead of send_push_to_user when you don't need to wait for delivery.
    This is the recommended way to send push notifications from API handlers."""
    if not user_ids:
        return
    asyncio.create_task(_background_push_task(user_ids, title, body, url))


async def send_push_to_role(db: AsyncSession, role: UserRole, title: str, body: str, url: str = "/dashboard"):
    """Send push to all users with a given role (non-blocking background)."""
    result = await db.execute(
        select(PushSubscription.user_id).join(User, PushSubscription.user_id == User.id).where(User.role == role).distinct()
    )
    user_ids = [r[0] for r in result.all()]
    fire_push_background(user_ids, title, body, url)


async def send_push_to_all(db: AsyncSession, title: str, body: str, url: str = "/dashboard"):
    """Send push to all subscribed users (non-blocking background)."""
    result = await db.execute(
        select(PushSubscription.user_id).distinct()
    )
    user_ids = [r[0] for r in result.all()]
    fire_push_background(user_ids, title, body, url)

