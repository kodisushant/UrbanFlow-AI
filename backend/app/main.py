from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api_router import api_router
from app.agents.coordinator import workflow_coordinator


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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


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

