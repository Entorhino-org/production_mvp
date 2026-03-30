"""
Seed a super admin account for initial deployment.
Run ONCE after first deploy: python seed_admin.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


async def main():
    from app.database import engine, Base, async_session
    from app.models.user import User, UserRole
    from app.core.security import hash_password

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        from sqlalchemy import select

        # Check if super admin already exists
        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"✅ Super admin already exists: {existing.email}")
            return

        # Create default super admin
        email = os.environ.get("ADMIN_EMAIL", "admin@entorhino.com")
        password = os.environ.get("ADMIN_PASSWORD", "admin123")
        full_name = os.environ.get("ADMIN_NAME", "Super Admin")

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            is_email_verified=True,
            is_approved=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Super admin created: {email} (password from ADMIN_PASSWORD; not logged)")


if __name__ == "__main__":
    asyncio.run(main())
