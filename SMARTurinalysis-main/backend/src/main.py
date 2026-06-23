"""
Main entry point for the SMARTurinalysis FastAPI application.
Bootstrap server, configures CORS, Sentry, and serves the frontend.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    global scheduler
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

# Parse ALLOWED_ORIGINS string into a list
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")] if settings.ALLOWED_ORIGINS else ["*"]

# CORS middleware for local frontend development support
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
    from src.config.config import settings
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="none" if settings.SECURE_COOKIE else "lax",
        secure=settings.SECURE_COOKIE,
        path="/"
    )
    return response

from datetime import datetime
from src.shared.database import get_collection

@app.get("/api/system/background-agents")
async def get_background_agents():
    """Returns the status of real-time background agents running in APScheduler."""
    if 'scheduler' not in globals() or not scheduler.running:
        return {"agents": []}
        
    agents = []
    try:
        col = get_collection("system_state")
        agent_state = await col.find_one({"agent": "market_updater"}) or {}
    except Exception:
        agent_state = {}

    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        # Provide a human-readable name based on job.id
        name = job.id.replace("_", " ").title()
        
        # Pull live status if it's the market updater
        action = agent_state.get("action", "Idle") if job.id == "market_updater_job" else "Idle"
        target = agent_state.get("target") if job.id == "market_updater_job" else None
        old_price = agent_state.get("old_price") if job.id == "market_updater_job" else None
        new_price = agent_state.get("new_price") if job.id == "market_updater_job" else None
        
        agents.append({
            "id": job.id,
            "name": name,
            "status": "Running" if action != "Idle" else "Idle",
            "next_run": next_run,
            "action": action,
            "target": target,
            "old_price": old_price,
            "new_price": new_price
        })
        
    return {"agents": agents}

@app.websocket("/api/system/ws/background-agents")
async def ws_background_agents(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            agents = []
            try:
                col = get_collection("system_state")
                agent_state = await col.find_one({"agent": "market_updater"}) or {}
            except Exception:
                agent_state = {}

            if "scheduler" in globals():
                for job in scheduler.get_jobs():
                    next_run = job.next_run_time.isoformat() if job.next_run_time else None
                    name = job.id.replace("_", " ").title()
                    
                    action = agent_state.get("action", "Idle") if job.id == "market_updater_job" else "Idle"
                    target = agent_state.get("target") if job.id == "market_updater_job" else None
                    old_price = agent_state.get("old_price") if job.id == "market_updater_job" else None
                    new_price = agent_state.get("new_price") if job.id == "market_updater_job" else None
                    
                    agents.append({
                        "id": job.id,
                        "name": name,
                        "status": "Running" if action != "Idle" else "Idle",
                        "next_run": next_run,
                        "action": action,
                        "target": target,
                        "old_price": old_price,
                        "new_price": new_price
                    })
            
            await websocket.send_json({"agents": agents})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

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
