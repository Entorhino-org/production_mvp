"""
Announcements API — create, list, and track read status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.communication import Announcement, AnnouncementTarget, AnnouncementRead
from app.schemas.communication import AnnouncementCreate
from app.core.dependencies import get_current_user
from app.api.websocket import manager as ws_manager

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


@router.post("/", status_code=201)
async def create_announcement(
    req: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an announcement (teachers/admins only)."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins can post announcements")

    announcement = Announcement(
        author_id=current_user.id,
        title=req.title,
        content=req.content,
        target=AnnouncementTarget(req.target),
    )
    db.add(announcement)
    await db.flush()

    # Broadcast via WebSocket to target users
    target_roles = {
        AnnouncementTarget.ALL: [UserRole.ADMIN, UserRole.SCHOOL_ADMIN, UserRole.TEACHER, UserRole.STUDENT, UserRole.PARENT],
        AnnouncementTarget.STUDENTS: [UserRole.STUDENT],
        AnnouncementTarget.TEACHERS: [UserRole.TEACHER],
        AnnouncementTarget.PARENTS: [UserRole.PARENT],
    }
    roles = target_roles.get(announcement.target, [])
    try:
        if announcement.target == AnnouncementTarget.ALL:
            await ws_manager.broadcast_all({
                "type": "announcement",
                "title": req.title,
                "content": req.content,
                "author": current_user.full_name,
            })
        else:
            await ws_manager.broadcast_to_roles(roles, {
                "type": "announcement",
                "title": req.title,
                "content": req.content,
                "author": current_user.full_name,
            })
    except Exception:
        pass  # Don't fail the API call if broadcast fails

    # Send web push notifications
    try:
        from app.api.push import send_push_to_all, send_push_to_role
        push_title = f"📢 {req.title}"
        push_body = req.content[:200] if req.content else ""
        if announcement.target == AnnouncementTarget.ALL:
            await send_push_to_all(db, push_title, push_body, "/dashboard")
        else:
            for role in roles:
                await send_push_to_role(db, role, push_title, push_body, "/dashboard")
    except Exception as e:
        print(f"[PUSH] Announcement push failed: {e}")

    return {"id": str(announcement.id), "message": "Announcement posted"}


@router.get("/")
async def list_announcements(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List announcements visible to the current user, with read status. Paginated."""
    limit = min(max(limit, 1), 100)
    # Filter by role-appropriate targets
    role_targets = [AnnouncementTarget.ALL]
    if current_user.role == UserRole.TEACHER:
        role_targets.append(AnnouncementTarget.TEACHERS)
    elif current_user.role == UserRole.STUDENT:
        role_targets.append(AnnouncementTarget.STUDENTS)
    elif current_user.role == UserRole.PARENT:
        role_targets.append(AnnouncementTarget.PARENTS)
    elif current_user.role in (UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        role_targets = list(AnnouncementTarget)

    # Left join with AnnouncementRead to get read status
    result = await db.execute(
        select(Announcement, User, AnnouncementRead.id.label("read_id"))
        .join(User, Announcement.author_id == User.id)
        .outerjoin(
            AnnouncementRead,
            (AnnouncementRead.announcement_id == Announcement.id)
            & (AnnouncementRead.user_id == current_user.id),
        )
        .where(Announcement.target.in_(role_targets))
        .order_by(Announcement.created_at.desc())
        .offset(offset).limit(limit)
    )

    return [
        {
            "id": str(a.id),
            "title": a.title,
            "content": a.content,
            "target": a.target.value,
            "author_name": u.full_name,
            "is_read": read_id is not None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a, u, read_id in result.all()
    ]


@router.get("/unread-count")
async def unread_announcement_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Count unread announcements for badge."""
    role_targets = [AnnouncementTarget.ALL]
    if current_user.role == UserRole.TEACHER:
        role_targets.append(AnnouncementTarget.TEACHERS)
    elif current_user.role == UserRole.STUDENT:
        role_targets.append(AnnouncementTarget.STUDENTS)
    elif current_user.role == UserRole.PARENT:
        role_targets.append(AnnouncementTarget.PARENTS)
    elif current_user.role in (UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        role_targets = list(AnnouncementTarget)

    result = await db.execute(
        select(func.count(Announcement.id))
        .outerjoin(
            AnnouncementRead,
            (AnnouncementRead.announcement_id == Announcement.id)
            & (AnnouncementRead.user_id == current_user.id),
        )
        .where(Announcement.target.in_(role_targets), AnnouncementRead.id == None)
    )
    return {"unread_count": result.scalar() or 0}


@router.put("/mark-all-read")
async def mark_all_announcements_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all visible announcements as read for the current user."""
    role_targets = [AnnouncementTarget.ALL]
    if current_user.role == UserRole.TEACHER:
        role_targets.append(AnnouncementTarget.TEACHERS)
    elif current_user.role == UserRole.STUDENT:
        role_targets.append(AnnouncementTarget.STUDENTS)
    elif current_user.role == UserRole.PARENT:
        role_targets.append(AnnouncementTarget.PARENTS)
    elif current_user.role in (UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        role_targets = list(AnnouncementTarget)

    # Get unread announcement IDs
    result = await db.execute(
        select(Announcement.id)
        .outerjoin(
            AnnouncementRead,
            (AnnouncementRead.announcement_id == Announcement.id)
            & (AnnouncementRead.user_id == current_user.id),
        )
        .where(Announcement.target.in_(role_targets), AnnouncementRead.id == None)
    )
    unread_ids = [row[0] for row in result.all()]

    for ann_id in unread_ids:
        db.add(AnnouncementRead(user_id=current_user.id, announcement_id=ann_id))
    await db.flush()

    return {"message": f"{len(unread_ids)} announcements marked as read"}


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if str(ann.author_id) != str(current_user.id) and current_user.role not in (UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(ann)
    await db.flush()
    return {"message": "Announcement deleted"}
