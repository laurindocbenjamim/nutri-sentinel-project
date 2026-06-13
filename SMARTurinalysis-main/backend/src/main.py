"""
Main entry point for the SMARTurinalysis FastAPI application.
Bootstrap server, configures CORS, Sentry, and serves the frontend.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.config.config import settings, init_sentry
from src.domains.synthetic.router import router as synthetic_router
from src.domains.analysis.router import router as analysis_router

# Initialize Sentry error tracking
init_sentry()

app = FastAPI(
    title=settings.APP_NAME,
    description="Stateless colorimetric urinalysis API with synthetic generation",
    version="1.0.0"
)

# CORS middleware for local frontend development support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Bounded Context Domain routers
app.include_router(synthetic_router)
app.include_router(analysis_router)

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
