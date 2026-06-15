import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.domains.subscriptions.database import AsyncSessionLocal, engine
from src.domains.subscriptions.models import UserPlan, AvailablePlan, Base
from sqlalchemy.future import select

async def seed_data():
    async with engine.begin() as conn:
        # Note: assuming tables are already created in supabase.
        # If not, we could do await conn.run_sync(Base.metadata.create_all)
        pass

    async with AsyncSessionLocal() as session:
        print("Seeding Available Plans...")
        plans = [
            AvailablePlan(plan_id="free", daily_limit=1, is_available=True, display_name="Free (Trial)"),
            AvailablePlan(plan_id="pro", daily_limit=10, is_available=True, display_name="Pro (Alpha)"),
            AvailablePlan(plan_id="enterprise", daily_limit=1000, is_available=True, display_name="Enterprise (Pro)")
        ]
        
        for p in plans:
            existing = await session.execute(select(AvailablePlan).where(AvailablePlan.plan_id == p.plan_id))
            if not existing.scalars().first():
                session.add(p)
            else:
                # Update limit if needed
                stmt = await session.execute(select(AvailablePlan).where(AvailablePlan.plan_id == p.plan_id))
                obj = stmt.scalars().first()
                obj.daily_limit = p.daily_limit
                obj.is_available = p.is_available

        print("Seeding Test Users...")
        test_users = [
            ("uuid-free-user", "free"),
            ("uuid-pro-user", "pro"),
            ("uuid-enterprise-user", "enterprise"),
        ]

        for u_uuid, p_id in test_users:
            existing = await session.execute(select(UserPlan).where(UserPlan.user_uuid == u_uuid))
            obj = existing.scalars().first()
            if not obj:
                session.add(UserPlan(
                    user_plan_uuid=f"plan-{u_uuid}",
                    user_uuid=u_uuid,
                    discord_id=u_uuid,
                    username=f"Test {p_id.capitalize()}",
                    email=f"test_{p_id}@example.com",
                    plan=p_id,
                    is_active=True
                ))
            else:
                obj.plan = p_id

        await session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
