from datetime import datetime
from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class UserPlan(Base):
    __tablename__ = "users_plan"
    user_plan_uuid = Column(String, primary_key=True, unique=True, index=True)
    user_uuid = Column(String, index=True)
    discord_id = Column(String, unique=True, index=True)
    username = Column(String)
    email = Column(String)
    plan = Column(String, default="free")  # free, explorer, pro
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    receive_alerts = Column(Boolean, default=True)
    watched_terms = Column(JSON, default=list) 


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)  # Using discord_id for usage tracking as per user's prompt
    timestamp = Column(DateTime, default=datetime.now)
    term = Column(String)
    command_used = Column(String)
    tokens_used = Column(Integer)
    provider = Column(String)

class AvailablePlan(Base):
    __tablename__ = "available_plans"

    plan_id = Column(String, primary_key=True)
    daily_limit = Column(Integer, default=0)
    cooldown = Column(Integer, default=120)
    price = Column(String)
    plan_name = Column(String)
    display_name = Column(String)
    functionalities = Column(String)
    stripe_price_id = Column(String, nullable=True)
    enabled_sources = Column(String, default="google,duckduckgo")
    product_quantity = Column(Integer, default=1)
    trial_period_days = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    product_type = Column(String)

class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String, index=True)
    previous_plan = Column(String)
    new_plan = Column(String)
    change_type = Column(String)  # 'new', 'upgrade', 'downgrade', 'cancel', 'renewal'
    stripe_session_id = Column(String, nullable=True)
    amount = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

class UserUsage(Base):
    __tablename__ = 'user_usage'
    discord_id = Column(String, primary_key=True, index=True)
    daily_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.now)
    agent_logs = Column(JSON, default=list) # JSON string of last 3 activities
