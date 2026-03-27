"""
Web Push Notifications API — subscribe, unsubscribe, and send push notifications.
"""

import json
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.user import User, UserRole
from app.models.communication import PushSubscription
from app.core.dependencies import get_current_user
from app.config import get_settings

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


async def send_push_to_user(db: AsyncSession, user_id, title: str, body: str, url: str = "/dashboard"):
    """Send a web push notification to all subscriptions of a user.
    This is a fire-and-forget helper — errors are logged but not raised."""
    from pywebpush import webpush, WebPushException

    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subs = result.scalars().all()

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": "/static/icon-192.png",
    })

    stale_ids = []
    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            }
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_MAILTO},
            )
        except WebPushException as e:
            # 410 Gone means the subscription expired — clean up
            if "410" in str(e) or "404" in str(e):
                stale_ids.append(sub.id)
            else:
                print(f"[PUSH] Error sending to {sub.endpoint[:50]}: {e}")
        except Exception as e:
            print(f"[PUSH] Unexpected error: {e}")
            traceback.print_exc()

    # Clean up stale subscriptions
    if stale_ids:
        await db.execute(
            delete(PushSubscription).where(PushSubscription.id.in_(stale_ids))
        )
        await db.flush()


async def send_push_to_role(db: AsyncSession, role: UserRole, title: str, body: str, url: str = "/dashboard"):
    """Send push to all users with a given role."""
    result = await db.execute(
        select(PushSubscription.user_id).join(User, PushSubscription.user_id == User.id).where(User.role == role).distinct()
    )
    user_ids = [r[0] for r in result.all()]
    for uid in user_ids:
        await send_push_to_user(db, uid, title, body, url)


async def send_push_to_all(db: AsyncSession, title: str, body: str, url: str = "/dashboard"):
    """Send push to all subscribed users."""
    result = await db.execute(
        select(PushSubscription.user_id).distinct()
    )
    user_ids = [r[0] for r in result.all()]
    for uid in user_ids:
        await send_push_to_user(db, uid, title, body, url)
