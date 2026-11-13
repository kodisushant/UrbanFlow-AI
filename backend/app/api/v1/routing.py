import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.schemas.route import (
    RouteRequest,
    RouteResult,
    RouteStatus,
    SimulationStatus,
    FindPathRequest,
    FindPathResult,
    ComparePathRequest,
    ComparePathResult,
    RandomizeTrafficRequest,
    RandomizeTrafficResult,
)
from app.services.city_graph_service import city_graph_service
from app.services.resource_service import resource_service
from app.agents.coordinator import workflow_coordinator

router = APIRouter(prefix="/routing", tags=["Road Graph & Routing"])


@router.post("/calculate", response_model=RouteResult)
async def calculate_route(req: RouteRequest) -> RouteResult:
    """
    Member 4 Routing Engine Integration Endpoint.
    Calculates primary and alternative paths avoiding blocked/specified roads using A* or Dijkstra.
    Includes unit position, ETA, route status, avoided roads, signal-priority nodes, and simulation status.
    """
    origin_node = city_graph_service.get_node(req.origin_node)
    dest_node = city_graph_service.get_node(req.destination_node)

    if not origin_node or not dest_node:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_NODE", "message": "Origin or destination node not found in city graph."}
        )

    # Unit current position
    unit_pos = {"node": req.origin_node, "latitude": origin_node.latitude, "longitude": origin_node.longitude}
    if req.unit_id:
        unit = resource_service.get_unit(req.unit_id)
        if unit:
            unit_pos = {"node": unit.current_node, "latitude": unit.latitude, "longitude": unit.longitude}

    primary_path = city_graph_service.find_shortest_path(
        origin_node=req.origin_node,
        destination_node=req.destination_node,
        avoid_road_ids=set(req.avoid_road_ids),
        algorithm=req.algorithm
    )

    if not primary_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NO_PATH_FOUND", "message": "No traversable path between nodes with current road closures."}
        )

    # Calculate alternative route by avoiding first segment of primary route
    alt_avoid = set(req.avoid_road_ids)
    if primary_path.road_ids:
        alt_avoid.add(primary_path.road_ids[0])

    alt_path = city_graph_service.find_shortest_path(
        origin_node=req.origin_node,
        destination_node=req.destination_node,
        avoid_road_ids=alt_avoid,
        algorithm=req.algorithm
    )
    alt_routes = [alt_path] if alt_path else []

    # Signal priority nodes
    signal_nodes = [
        nid for nid in primary_path.node_sequence
        if city_graph_service.get_node(nid) and city_graph_service.get_node(nid).is_signalized
    ]

    diverted = list(req.avoid_road_ids)

    return RouteResult(
        route_id=f"ROUTE-{uuid.uuid4().hex[:6].upper()}",
        unit_id=req.unit_id,
        incident_id=req.incident_id,
        unit_current_position=unit_pos,
        destination_node=req.destination_node,
        eta_seconds=primary_path.estimated_travel_time_seconds,
        route_status=RouteStatus.CALCULATED,
        simulation_status=SimulationStatus.IDLE,
        algorithm=req.algorithm,
        primary_route=primary_path,
        alternative_routes=alt_routes,
        avoided_roads=list(req.avoid_road_ids),
        signal_priority_nodes=signal_nodes,
        diverted_roads=diverted,
        explanation=(
            f"Calculated path via {req.algorithm.upper()} with ETA {primary_path.estimated_travel_time_seconds}s "
            f"covering {primary_path.distance_meters}m. {len(signal_nodes)} signal priority nodes designated."
        )
    )


@router.get("/active", response_model=List[RouteResult])
async def list_active_routes() -> List[RouteResult]:
    """Retrieve all active emergency routes currently in progress."""
    return workflow_coordinator.get_state().active_routes


# -----------------------------------------------------------------------------
# Find Path Mode & Route Comparison Endpoints
# -----------------------------------------------------------------------------

@router.post("/find-path", response_model=FindPathResult)
async def post_find_path(req: FindPathRequest) -> FindPathResult:
    """
    Computes a single route in either 'optimised' or 'baseline' mode.
    - 'optimised': A* or Dijkstra with congestion weights, avoiding closed roads.
    - 'baseline': Shortest distance only, then evaluated under real conditions (with detour penalties if blocked).
    """
    try:
        return city_graph_service.find_path(
            from_node=req.from_node,
            to_node=req.to_node,
            mode=req.mode,
            algorithm=req.algorithm,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_NODE", "message": str(e)}
        )


@router.post("/compare", response_model=ComparePathResult)
async def post_compare_paths(req: ComparePathRequest) -> ComparePathResult:
    """
    Calculates both Optimised and Baseline routes side-by-side, returning metrics and time savings.
    """
    try:
        return city_graph_service.compare_paths(
            from_node=req.from_node,
            to_node=req.to_node,
            algorithm=req.algorithm,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_NODE", "message": str(e)}
        )


@router.post("/randomize-traffic", response_model=RandomizeTrafficResult)
async def post_randomize_traffic(req: RandomizeTrafficRequest) -> RandomizeTrafficResult:
    """
    Randomizes congestion levels across all roads and blocks 2-4 roads.
    """
    res = city_graph_service.randomize_traffic(
        seed=req.seed,
        min_blocks=req.min_blocks,
        max_blocks=req.max_blocks,
    )
    return RandomizeTrafficResult(**res)
