<<<<<<< HEAD
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.schemas.city import CityGraph
from app.schemas.incident import IncidentRecord, IncidentDetectionPayload, ObservedVehicle
=======
from typing import Dict, Any, List
from fastapi import APIRouter
from app.schemas.city import CityGraph
from app.schemas.resource import EmergencyUnit
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
from app.services.city_graph_service import city_graph_service
from app.services.resource_service import resource_service
from app.agents.coordinator import workflow_coordinator

router = APIRouter(prefix="/simulation", tags=["Simulation & Map Grid"])


class RoadClosureRequest(BaseModel):
    road_id: str = Field(..., description="Road segment identifier e.g. ROAD-03A")
    is_blocked: bool = Field(default=True, description="True to block, False to reopen")


class RoadDivertRequest(BaseModel):
    road_id: str = Field(..., description="Road segment identifier e.g. ROAD-03A")
    is_diverted: bool = Field(default=True, description="True to mark diverted, False to clear")


class SignalPriorityRequest(BaseModel):
    node_ids: List[str] = Field(..., description="List of node IDs e.g. ['INT-03', 'INT-19']")
    active: bool = Field(default=True)


class CandidateSimulationRequest(BaseModel):
    location_node: str = Field(default="INT-03")
    road_id: Optional[str] = Field(default="ROAD-03A")
    candidate_type: str = Field(default="possible_collision")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    camera_id: str = Field(default="cctv_camera_01")


@router.get("/city-graph", response_model=CityGraph)
async def get_city_graph() -> CityGraph:
    """
    Member 5 Frontend Interactive Map Endpoint.
<<<<<<< HEAD
    Returns the complete Cyber City road network graph (20 nodes, 58 segments).
=======
    Returns the complete city graph with nodes, road edges, signal states, and coordinates.
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
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


@router.post("/road-closure", response_model=Dict[str, Any])
async def toggle_road_closure(req: RoadClosureRequest) -> Dict[str, Any]:
    """Toggle blockage / closure on a specific road segment."""
    edge = city_graph_service.get_edge(req.road_id)
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROAD_NOT_FOUND", "message": f"Road segment '{req.road_id}' not found."}
        )
    city_graph_service.set_road_blocked(req.road_id, req.is_blocked)
    return {
        "status": "success",
        "road_id": req.road_id,
        "is_blocked": req.is_blocked,
        "message": f"Road {req.road_id} {'blocked' if req.is_blocked else 'reopened'}."
    }


@router.post("/road-divert", response_model=Dict[str, Any])
async def toggle_road_divert(req: RoadDivertRequest) -> Dict[str, Any]:
    """Toggle diversion designation on a road segment."""
    edge = city_graph_service.get_edge(req.road_id)
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROAD_NOT_FOUND", "message": f"Road segment '{req.road_id}' not found."}
        )
    city_graph_service.set_road_diverted(req.road_id, req.is_diverted)
    return {
        "status": "success",
        "road_id": req.road_id,
        "is_diverted": req.is_diverted
    }


@router.post("/signal-priority", response_model=Dict[str, Any])
async def set_signal_priority_corridor(req: SignalPriorityRequest) -> Dict[str, Any]:
    """Simulate emergency green corridor signal preemption on given intersections."""
    if req.active:
        city_graph_service.set_signal_priority(req.node_ids)
    else:
        for nid in req.node_ids:
            node = city_graph_service.get_node(nid)
            if node:
                node.signal_state = "normal"
    return {
        "status": "success",
        "node_ids": req.node_ids,
        "active": req.active
    }


@router.post("/detect-candidate", response_model=IncidentRecord, status_code=status.HTTP_201_CREATED)
async def simulate_candidate_detection(req: Optional[CandidateSimulationRequest] = None) -> IncidentRecord:
    """
    Simulate CCTV candidate detection at a given intersection or road.
    Transitions system to Step 1 (Candidate Detection) awaiting operator verification.
    """
    p = req or CandidateSimulationRequest()
    payload = IncidentDetectionPayload(
        camera_id=p.camera_id,
        source=p.camera_id,
        candidate_type=p.candidate_type,
        type=p.candidate_type,
        confidence=p.confidence,
        heuristic_score=p.confidence,
        location_node=p.location_node,
        affected_road_id=p.road_id,
        road_id=p.road_id,
        evidence_image_url="assets/evidence/INC-CCTV-001_frame_426.jpg",
        evidence_urls=[
            "assets/evidence/INC-CCTV-001_frame_426.jpg",
            "assets/evidence/INC-CCTV-001_crop_14_19.jpg"
        ],
        observed_vehicles=[
            ObservedVehicle(vehicle_class="car", bbox=[120, 240, 200, 310], speed_kmph=0.0, is_stopped=True),
            ObservedVehicle(vehicle_class="truck", bbox=[180, 250, 320, 380], speed_kmph=0.0, is_stopped=True)
        ],
        is_simulated=True
    )
    return workflow_coordinator.handle_detection(payload)
