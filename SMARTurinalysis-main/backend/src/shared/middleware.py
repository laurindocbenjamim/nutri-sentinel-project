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
                
        # API request authorization
        if path.startswith("/api/"):
            if not session_valid:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid or missing session token. Please reload the application."}
                )
            return await call_next(request)
            
        # For HTML pages and root access, automatically initialize session if missing
        response = await call_next(request)
        if not session_valid:
            session_id = str(uuid.uuid4())
            new_token = create_session_token({"session_id": session_id})
            
            response.set_cookie(
                key="session_token",
                value=new_token,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
                path="/"
            )
            
        return response
