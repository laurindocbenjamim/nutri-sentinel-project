from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import logging

from src.domains.subscriptions.models import UserPlan, AvailablePlan, UserUsage

logger = logging.getLogger("nutri-sentinel")

class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_plan(self, user_uuid: str) -> str:
        """Fetches the user's plan tier, defaults to 'free' if not found."""
        result = await self.session.execute(
            select(UserPlan).where(UserPlan.user_uuid == user_uuid, UserPlan.is_active == True)
        )
        user_plan = result.scalars().first()
        return user_plan.plan if user_plan else "free"

    async def get_available_plan(self, plan_id: str) -> Optional[AvailablePlan]:
        """Fetches plan details to get the daily limits."""
        result = await self.session.execute(
            select(AvailablePlan).where(AvailablePlan.plan_id == plan_id, AvailablePlan.is_available == True)
        )
        return result.scalars().first()

    async def get_or_create_usage(self, user_uuid: str) -> UserUsage:
        """Gets user usage, resets if it's a new day, or creates if not exists."""
        # Note: the table uses discord_id as PK, we'll store user_uuid there
        result = await self.session.execute(
            select(UserUsage).where(UserUsage.discord_id == user_uuid)
        )
        usage = result.scalars().first()
        
        now = datetime.now()
        if not usage:
            usage = UserUsage(discord_id=user_uuid, daily_count=0, last_reset=now)
            self.session.add(usage)
            await self.session.commit()
            await self.session.refresh(usage)
            return usage
        
        # Reset if last_reset is from a previous day
        if usage.last_reset.date() < now.date():
            usage.daily_count = 0
            usage.last_reset = now
            await self.session.commit()
            await self.session.refresh(usage)
            
        return usage

    async def check_and_consume_quota(self, user_uuid: str) -> bool:
        """
        Checks if the user has enough daily limit to perform an action.
        Currently bypassed as requested to fix the OCR Quota Exceeded error.
        """
        return True
