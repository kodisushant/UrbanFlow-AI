import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure repository root is on sys.path for cross-module routing and vision imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.config import settings
from app.api.v1.api_router import api_router
from app.agents.coordinator import workflow_coordinator

try:
    from routing.api import router as member4_routing_router
except ImportError:
    member4_routing_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize default city network and reset coordinator to standby
    workflow_coordinator.reset_state()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "UrbanFlow AI Backend: Multi-Agent Traffic Intelligence & "
        "Emergency Response Optimization System API."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend integration (Member 5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount Member 4 routing router if available (supports both /routing and /api/v1/routing)
if member4_routing_router:
    app.include_router(member4_routing_router)
    app.include_router(member4_routing_router, prefix=settings.API_V1_STR)

# Mount static assets directory (CCTV evidence, configs, sample feeds)
assets_path = os.path.join(ROOT_DIR, "assets")
if os.path.isdir(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    app.mount("/static", StaticFiles(directory=assets_path), name="static")


@app.get("/healthz", tags=["System Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "simulation_prototype"
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to UrbanFlow AI API. Visit /docs for the interactive Swagger documentation.",
        "documentation": "/docs",
        "health": "/healthz"
    }
