import time
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from app.schemas.route import (
    RouteRequest,
    RouteResult,
    RouteStatus,
    SimulationStatus,
    FindPathRequest,
    FindPathResult,
    ComparePathsRequest,
    ComparePathsResult,
    SegmentCongestionInfo,
    RandomizeTrafficRequest,
    RandomizeTrafficResult,
    CongestBaselineRequest,
    CongestBaselineResult,
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


def _evaluate_path_under_current_conditions(
    path_nodes: List[str],
    path_roads: List[str],
    mode: str,
    algorithm: str,
    from_node: str,
    to_node: str,
    nodes_explored: int,
    compute_ms: float,
    total_distance_meters: float,
    base_travel_time_seconds: float = 0.0,
) -> FindPathResult:
    """
    Evaluates a sequence of nodes/roads under current live city conditions:
    - calculates per-segment travel time using current congestion multipliers
    - flags any blocked roads and applies DETOUR penalty for baseline routes
    """
    segments: List[SegmentCongestionInfo] = []
    congested_count = 0
    blocked_count = 0
    calc_time_sec = 0.0

    for i, road_id in enumerate(path_roads):
        edge = city_graph_service.get_edge(road_id)
        u = path_nodes[i]
        v = path_nodes[i + 1]
        if not edge:
            continue

        speed_mps = (edge.speed_limit_kmph * 1000.0 / 3600.0) if edge.speed_limit_kmph > 0 else 13.89
        base_seg_time = edge.length_meters / speed_mps
        seg_time = base_seg_time * max(1.0, edge.congestion_weight_multiplier)

        if edge.current_congestion_level != "free_flow" or edge.congestion_weight_multiplier > 1.05:
            congested_count += 1

        if edge.is_blocked:
            blocked_count += 1

        calc_time_sec += seg_time
        segments.append(
            SegmentCongestionInfo(
                road_id=road_id,
                name=edge.name,
                source_node=u,
                target_node=v,
                length_meters=edge.length_meters,
                speed_limit_kmph=edge.speed_limit_kmph,
                congestion_level=edge.current_congestion_level,
                congestion_multiplier=edge.congestion_weight_multiplier,
                is_blocked=edge.is_blocked,
                segment_travel_time_seconds=round(seg_time, 1),
            )
        )

    # Detour penalty if baseline encounters blocked roads
    detour_penalty = 0.0
    if mode == "baseline" and blocked_count > 0:
        detour_penalty = blocked_count * settings.BLOCKED_ROAD_DETOUR_PENALTY_SECONDS

    final_time_sec = calc_time_sec + detour_penalty
    if mode == "optimised" and base_travel_time_seconds > 0:
        # Use exact cost computed during graph search
        final_time_sec = base_travel_time_seconds

    geometry = city_graph_service._build_geometry_coordinates(path_nodes, path_roads)

    return FindPathResult(
        mode=mode,
        algorithm=algorithm,
        from_node=from_node,
        to_node=to_node,
        node_sequence=path_nodes,
        road_ids=path_roads,
        geometry=geometry,
        total_distance_km=round(total_distance_meters / 1000.0, 3),
        total_distance_meters=round(total_distance_meters, 1),
        estimated_travel_time_seconds=round(final_time_sec, 1),
        estimated_travel_time_minutes=round(final_time_sec / 60.0, 2),
        nodes_explored=nodes_explored,
        compute_ms=round(compute_ms, 2),
        congested_segments_count=congested_count,
        blocked_roads_count=blocked_count,
        has_blocked_segments=(blocked_count > 0),
        detour_penalty_applied_seconds=detour_penalty,
        segments=segments,
        is_reachable=True,
    )


def _compute_single_path(
    from_node: str,
    to_node: str,
    mode: str = "optimised",
    algorithm: str = "astar",
) -> FindPathResult:
    resolved_from = city_graph_service._resolve_node_id(from_node)
    resolved_to = city_graph_service._resolve_node_id(to_node)

    if resolved_from not in city_graph_service.nodes or resolved_to not in city_graph_service.nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_NODE", "message": f"One or both nodes ('{from_node}', '{to_node}') not found in city graph."}
        )

    if resolved_from == resolved_to:
        node = city_graph_service.get_node(resolved_from)
        geom = [[node.latitude, node.longitude]] if node else []
        return FindPathResult(
            mode=mode,
            algorithm=algorithm,
            from_node=resolved_from,
            to_node=resolved_to,
            node_sequence=[resolved_from],
            road_ids=[],
            geometry=geom,
            total_distance_km=0.0,
            total_distance_meters=0.0,
            estimated_travel_time_seconds=0.0,
            estimated_travel_time_minutes=0.0,
            nodes_explored=1,
            compute_ms=0.05,
            congested_segments_count=0,
            blocked_roads_count=0,
            has_blocked_segments=False,
            detour_penalty_applied_seconds=0.0,
            segments=[],
            is_reachable=True,
            message="Origin and destination are the same node.",
        )

    start_time = time.perf_counter()

    if mode == "optimised":
        res = city_graph_service.find_shortest_path_with_stats(
            origin_node=resolved_from,
            destination_node=resolved_to,
            avoid_road_ids=None,
            algorithm=algorithm,
            allow_destination_access=False
        )
        compute_ms = (time.perf_counter() - start_time) * 1000.0

        if not res:
            return FindPathResult(
                mode=mode,
                algorithm=algorithm,
                from_node=resolved_from,
                to_node=resolved_to,
                is_reachable=False,
                message=f"No traversable path from {resolved_from} to {resolved_to} avoiding road closures.",
                compute_ms=round(compute_ms, 2),
            )

        path_nodes, path_roads, total_time, total_dist, nodes_explored = res
        return _evaluate_path_under_current_conditions(
            path_nodes=path_nodes,
            path_roads=path_roads,
            mode="optimised",
            algorithm=algorithm,
            from_node=resolved_from,
            to_node=resolved_to,
            nodes_explored=nodes_explored,
            compute_ms=compute_ms,
            total_distance_meters=total_dist,
            base_travel_time_seconds=total_time,
        )

    else:  # baseline ("Without Optimisation")
        res = city_graph_service.find_shortest_distance_path(
            origin_node=resolved_from,
            destination_node=resolved_to,
        )
        compute_ms = (time.perf_counter() - start_time) * 1000.0

        if not res:
            return FindPathResult(
                mode=mode,
                algorithm="distance_shortest",
                from_node=resolved_from,
                to_node=resolved_to,
                is_reachable=False,
                message=f"No path between {resolved_from} and {resolved_to} on graph.",
                compute_ms=round(compute_ms, 2),
            )

        path_nodes, path_roads, total_dist, nodes_explored = res
        return _evaluate_path_under_current_conditions(
            path_nodes=path_nodes,
            path_roads=path_roads,
            mode="baseline",
            algorithm="distance_shortest",
            from_node=resolved_from,
            to_node=resolved_to,
            nodes_explored=nodes_explored,
            compute_ms=compute_ms,
            total_distance_meters=total_dist,
        )


@router.post("/find-path", response_model=FindPathResult)
async def find_path(req: FindPathRequest) -> FindPathResult:
    """
    Find Path endpoint: calculates either 'optimised' (A*/Dijkstra with congestion & block avoidance)
    or 'baseline' (shortest distance ignoring live data, evaluated under real conditions with detour penalty).
    """
    return _compute_single_path(
        from_node=req.from_node,
        to_node=req.to_node,
        mode=req.mode,
        algorithm=req.algorithm
    )


@router.post("/compare", response_model=ComparePathsResult)
async def compare_paths(req: ComparePathsRequest) -> ComparePathsResult:
    """
    Compare Paths endpoint: computes both optimised and baseline paths side-by-side,
    calculating travel time savings, distance difference, and summary analytics.
    """
    opt = _compute_single_path(
        from_node=req.from_node,
        to_node=req.to_node,
        mode="optimised",
        algorithm=req.algorithm
    )

    base = _compute_single_path(
        from_node=req.from_node,
        to_node=req.to_node,
        mode="baseline",
        algorithm="distance_shortest"
    )

    if not opt.is_reachable and not base.is_reachable:
        return ComparePathsResult(
            from_node=req.from_node,
            to_node=req.to_node,
            is_reachable=False,
            routes_match=False,
            summary="Destination is unreachable from origin under current road network.",
            optimised=opt,
            baseline=base,
        )

    # Check if routes match
    routes_match = (
        opt.is_reachable and base.is_reachable and
        opt.node_sequence == base.node_sequence and
        opt.blocked_roads_count == 0
    )

    time_diff_sec = base.estimated_travel_time_seconds - opt.estimated_travel_time_seconds
    time_saved_min = round(max(0.0, time_diff_sec) / 60.0, 1)

    time_saved_pct = 0.0
    if base.estimated_travel_time_seconds > 0:
        time_saved_pct = round((time_diff_sec / base.estimated_travel_time_seconds) * 100.0, 1)
        time_saved_pct = max(0.0, time_saved_pct)

    dist_diff_km = round(base.total_distance_km - opt.total_distance_km, 2)

    if routes_match:
        summary = "Routes match! With no congestion or closures along this corridor, both algorithms chose the identical path."
    elif not opt.is_reachable:
        summary = "Optimised routing found no safe path due to closures; baseline path is blocked."
    elif opt.estimated_travel_time_seconds < base.estimated_travel_time_seconds:
        summary = f"Optimised route is {time_saved_min} min ({time_saved_pct}%) faster"
        if base.blocked_roads_count > 0:
            summary += f" and avoids {base.blocked_roads_count} road closure(s)"
        summary += "."
    else:
        summary = "Both routes have equivalent travel times under current conditions."

    return ComparePathsResult(
        from_node=req.from_node,
        to_node=req.to_node,
        is_reachable=opt.is_reachable,
        routes_match=routes_match,
        summary=summary,
        time_saved_minutes=time_saved_min,
        time_saved_percent=time_saved_pct,
        distance_diff_km=dist_diff_km,
        optimised=opt,
        baseline=base,
    )


@router.post("/randomize-traffic", response_model=RandomizeTrafficResult)
async def randomize_traffic(req: RandomizeTrafficRequest = RandomizeTrafficRequest()) -> RandomizeTrafficResult:
    """
    Sets random congestion levels on roads and blocks 2-4 roads for realistic comparison testing.
    """
    try:
        seed, blocked, congested, details = city_graph_service.randomize_traffic_conditions(
            seed=req.seed,
            num_blocked=req.num_blocked_roads
        )
        return RandomizeTrafficResult(
            status="traffic_randomized",
            seed_used=seed,
            blocked_roads=blocked,
            congested_roads_count=congested,
            congested_roads=details,
        )
    except Exception as e:
        import logging
        logging.getLogger("urbanflow.routing").exception(f"Failed to randomize traffic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to randomize traffic: {str(e)}"
        )


@router.post("/congest-baseline", response_model=CongestBaselineResult)
async def congest_baseline_route(req: CongestBaselineRequest) -> CongestBaselineResult:
    """
    Demo scenario helper: applies heavy congestion and blocks one road strictly
    along the distance-shortest path between from_node and to_node.
    """
    try:
        resolved_from = city_graph_service._resolve_node_id(req.from_node)
        resolved_to = city_graph_service._resolve_node_id(req.to_node)

        if resolved_from not in city_graph_service.nodes or resolved_to not in city_graph_service.nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid node: '{req.from_node}' or '{req.to_node}' not found in city graph."
            )

        congested, blocked = city_graph_service.congest_path(resolved_from, resolved_to)
        if not congested:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No baseline path exists between {req.from_node} and {req.to_node} to congest."
            )

        return CongestBaselineResult(
            status="baseline_congested",
            from_node=req.from_node,
            to_node=req.to_node,
            congested_roads=congested,
            blocked_road=blocked,
            message=(
                f"Demo scenario applied: {len(congested)} road segments congested, "
                f"and road '{blocked}' closed on the baseline route."
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("urbanflow.routing").exception(f"Failed to congest baseline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply baseline congestion: {str(e)}"
        )
