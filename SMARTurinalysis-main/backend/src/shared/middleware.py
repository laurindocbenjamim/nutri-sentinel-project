"""
Middleware for JWT session validation.
Ensures every request has a valid HttpOnly session cookie.
"""

import uuid
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.shared.jwt import create_session_token, verify_session_token

class JWTSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce and manage HttpOnly JWT session cookies.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        
        # Bypass validation for OpenAPI schema, docs, session init, and static assets like CSS/JS
        if (path.startswith("/docs") or 
            path.startswith("/openapi.json") or 
            path == "/api/session/init" or
            path.endswith(".css") or 
            path.endswith(".js") or 
            path.endswith(".png") or 
            path.endswith(".jpg") or 
            path.endswith(".webp") or 
            path.endswith(".ico")):
            return await call_next(request)
            
        session_token = request.cookies.get("session_token")
        
        # Verify existing token
        session_valid = False
        if session_token:
            payload = verify_session_token(session_token)
            if payload:
                session_valid = True
                
        # Proceed with the request
        response = await call_next(request)
        
        # Automatically initialize session if missing
        if not session_valid:
            session_id = str(uuid.uuid4())
            new_token = create_session_token({"session_id": session_id})
            
            from src.config.config import settings
            
            response.set_cookie(
                key="session_token",
                value=new_token,
                httponly=True,
                samesite="none" if settings.SECURE_COOKIE else "lax",
                secure=settings.SECURE_COOKIE,
                path="/"
            )
            
        return response
