"""
Alerts API — view and manage smart alerts.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.communication import Alert
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/")
async def list_my_alerts(
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alerts for the current user (teacher/parent/admin). Paginated."""
    limit = min(max(limit, 1), 100)
    query = (
        select(Alert, User)
        .join(User, Alert.student_id == User.id)
        .where(Alert.recipient_id == current_user.id)
    )

    if unread_only:
        query = query.where(Alert.is_read == False)

    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)

    return [
        {
            "id": str(a.id),
            "student_id": str(a.student_id),
            "student_name": u.full_name,
            "alert_type": a.alert_type.value,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a, u in result.all()
    ]


@router.get("/unread-count")
async def unread_alert_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count(Alert.id))
        .where(Alert.recipient_id == current_user.id, Alert.is_read == False)
    )
    return {"unread_count": result.scalar()}


@router.put("/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.recipient_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    await db.flush()
    return {"message": "Alert marked as read"}


@router.put("/mark-all-read")
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(
            Alert.recipient_id == current_user.id,
            Alert.is_read == False,
        )
    )
    alerts = result.scalars().all()
    for alert in alerts:
        alert.is_read = True
    await db.flush()
    return {"message": f"{len(alerts)} alerts marked as read"}
