from typing import Dict, Any
from fastapi import APIRouter
from app.schemas.city import CityGraph
from app.services.city_graph_service import city_graph_service
from app.agents.coordinator import workflow_coordinator

router = APIRouter(prefix="/simulation", tags=["Simulation & Map Grid"])


@router.get("/city-graph", response_model=CityGraph)
async def get_city_graph() -> CityGraph:
    """
    Member 5 Frontend Interactive Map Endpoint.
    Returns the complete city graph of 20 nodes, 32 road edges, signal states, and coordinates.
    """
    return city_graph_service.get_city_graph()


@router.post("/reset", response_model=Dict[str, Any])
async def reset_simulation() -> Dict[str, Any]:
    """
    Instant demo reset.
    Clears all active incidents, restores units to stations, unblocks roads, and resets traffic.
    """
    workflow_coordinator.reset_state()
    return {
        "status": "success",
        "message": "Metropolis SmartGrid simulation and multi-agent state reset to baseline standby."
    }

