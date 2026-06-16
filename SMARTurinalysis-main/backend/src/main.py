"""
Main entry point for the SMARTurinalysis FastAPI application.
Bootstrap server, configures CORS, Sentry, and serves the frontend.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.config.config import settings, init_sentry
from src.domains.synthetic.router import router as synthetic_router
from src.domains.analysis.router import router as analysis_router
from src.domains.blood_analysis.router import router as blood_router
from src.domains.nutritional_agents.router import router as nutrition_router
from src.domains.nutritional_agents.ws_router import router as nutrition_ws_router
from src.shared.database import close_client


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.domains.nutritional_agents.background.market_updater import run_market_updater
import logging

logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    
    # Initialize and start background scheduler
    scheduler = AsyncIOScheduler()
    interval_minutes = settings.MARKET_UPDATER_INTERVAL_MINUTES
    scheduler.add_job(run_market_updater, "interval", minutes=interval_minutes, id="market_updater_job")
    scheduler.start()
    logger.info(f"Background Market Updater scheduled to run every {interval_minutes} minutes.")
    
    yield
    
    scheduler.shutdown()
    await close_client()

from src.shared.middleware import JWTSessionMiddleware

# Initialize Sentry error tracking
init_sentry()

app = FastAPI(
    title=settings.APP_NAME,
    description="Stateless colorimetric urinalysis API with synthetic generation",
    version="1.0.0",
    lifespan=lifespan,
)

# Register JWT Session Middleware first for session tracking
app.add_middleware(JWTSessionMiddleware)

# CORS middleware for local frontend development support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
import uuid
from src.shared.jwt import create_session_token

@app.post("/api/session/init")
async def init_session():
    """
    Initialize a secure session and set the HttpOnly JWT cookie.
    """
    session_id = str(uuid.uuid4())
    token = create_session_token({"session_id": session_id})
    response = JSONResponse(content={"status": "session_initialized"})
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )
    return response

# Include Bounded Context Domain routers
app.include_router(synthetic_router)
app.include_router(analysis_router)
app.include_router(blood_router)
app.include_router(nutrition_router)
app.include_router(nutrition_ws_router)

# Directories for static assets and frontend UI
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "static")
FRONTEND_DIR = os.path.join(CURRENT_DIR, "frontend")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

# Mount static files folder (for generated/aligned images)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount frontend client files
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
