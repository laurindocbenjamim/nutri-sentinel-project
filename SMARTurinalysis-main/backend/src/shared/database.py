"""
Shared async MongoDB client using Motor.

Provides a single application-level MongoClient instance, a lazy database
accessor, and a collection helper — all driven by values in the .env file
via pydantic-settings.

Usage:
    from src.shared.database import get_collection
    col = get_collection("user_profiles")
    doc = await col.find_one({"user_id": user_id})
"""

from __future__ import annotations
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from src.config.config import settings

# Module-level singleton — created once on first call to get_client()
_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    """
    Return the shared Motor async MongoDB client, initializing it on first call.
    Raises RuntimeError if MONGODB_URI is not configured.
    """
    global _client
    if _client is None:
        if not settings.MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is not set. Add it to your .env file."
            )
        import certifi
        _client = AsyncIOMotorClient(settings.MONGODB_URI, tlsCAFile=certifi.where())
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Return the configured database from the shared client."""
    return get_client()[settings.MONGODB_DB_NAME]


def get_collection(name: str) -> AsyncIOMotorCollection:
    """
    Return a named collection from the configured database.

    Args:
        name: Collection name (e.g., 'user_profiles', 'analysis').
    """
    return get_database()[name]


async def close_client() -> None:
    """Gracefully close the Motor client. Call on application shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
