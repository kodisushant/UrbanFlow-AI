from fastapi import APIRouter
from app.api.v1.incidents import router as incidents_router
from app.api.v1.traffic import router as traffic_router
from app.api.v1.resources import router as resources_router
from app.api.v1.routing import router as routing_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.orchestration import router as orchestration_router

api_router = APIRouter()

api_router.include_router(incidents_router)
api_router.include_router(traffic_router)
api_router.include_router(resources_router)
api_router.include_router(routing_router)
api_router.include_router(simulation_router)
api_router.include_router(orchestration_router)

