"""
JWT (JSON Web Token) session management utility.
Handles generating, verifying, and decoding HttpOnly session tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from src.config.config import settings

# Session validity duration (1 hour)
SESSION_DURATION = timedelta(hours=1)

def create_session_token(data: Dict[str, Any]) -> str:
    """
    Generate a signed JWT session token with an expiration timestamp.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + SESSION_DURATION
    payload.update({"exp": expire})
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token

def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT session token.
    Returns decoded claims if valid, or None if expired/invalid.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
