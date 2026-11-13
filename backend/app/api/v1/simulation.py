from typing import Dict, Any, List
from fastapi import APIRouter
from app.schemas.city import CityGraph
from app.schemas.resource import EmergencyUnit
from app.services.city_graph_service import city_graph_service
from app.services.resource_service import resource_service
from app.agents.coordinator import workflow_coordinator

router = APIRouter(prefix="/simulation", tags=["Simulation & Map Grid"])


@router.get("/city-graph", response_model=CityGraph)
async def get_city_graph() -> CityGraph:
    """
    Member 5 Frontend Interactive Map Endpoint.
    Returns the complete city graph with nodes, road edges, signal states, and coordinates.
    """
    return city_graph_service.get_city_graph()


@router.get("/tick", response_model=List[EmergencyUnit])
async def simulation_tick(speed: float = 5.0) -> List[EmergencyUnit]:
    """
    Simulation Tick Endpoint:
    Returns each unit's current lat/lon interpolated along its route geometry based on
    elapsed simulated time and speed, with status transitioning from en_route -> on_scene
    when destination is reached.
    """
    return resource_service.tick(speed_multiplier=speed)


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

