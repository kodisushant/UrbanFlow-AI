"""
UrbanFlow AI - Emergency Resource Selection, Corridor Simulation & Traffic Diversion
Member 4: Road Network, Emergency Routing & Traffic Diversion
"""

from __future__ import annotations
import math
from typing import List, Dict, Optional, Any, Tuple, Set
from .models import (
    EmergencyUnit,
    EmergencyUnitType,
    UnitStatus,
    ResourceRecommendation,
    RoutePath,
    RouteContext,
    VehicleClass,
    EmergencyCorridor,
    TrafficDiversionPlan,
    SignalState,
    finite_or_none,
)
from .graph import CityGraph
from .algorithms import astar, dijkstra


# -----------------------------------------------------------------------------
# Emergency Scoring Named Constants
# -----------------------------------------------------------------------------
# Time score = 10000.0 / (adjusted_eta_seconds + 1.0)
# Bonuses are kept modest (3.0 - 5.0) to ensure a slower unit never displaces a faster unit.
BONUS_ALS_EQUIPPED = 5.0      # Advanced Life Support capability on critical medical calls
BONUS_RESCUE_CUTTERS = 4.0   # Hydraulic rescue cutters for entrapment/accidents
BONUS_RAPID_RESPONSE = 3.0   # Specialized high-mobility rapid response capability


def map_incident_to_required_services(incident_type: str, severity: str = "moderate") -> List[EmergencyUnitType]:
    """
    Determine which emergency services are needed based on incident classification.
    """
    inc_lower = incident_type.lower()
    services: List[EmergencyUnitType] = []

    if any(k in inc_lower for k in ["collision", "accident", "crash", "injury", "pedestrian", "casualty"]):
        services.append(EmergencyUnitType.AMBULANCE)
        services.append(EmergencyUnitType.POLICE)

    if any(k in inc_lower for k in ["fire", "explosion", "smoke", "hazmat", "chemical", "spill", "tanker"]):
        if EmergencyUnitType.FIRE_ENGINE not in services:
            services.append(EmergencyUnitType.FIRE_ENGINE)
        if EmergencyUnitType.AMBULANCE not in services:
            services.append(EmergencyUnitType.AMBULANCE)
        if EmergencyUnitType.POLICE not in services:
            services.append(EmergencyUnitType.POLICE)

    if any(k in inc_lower for k in ["blockage", "stalled_vehicle", "debris", "road_hazard", "congestion"]):
        if EmergencyUnitType.POLICE not in services:
            services.append(EmergencyUnitType.POLICE)

    if not services:
        services = [EmergencyUnitType.POLICE, EmergencyUnitType.AMBULANCE]

    return services


def rank_emergency_resources(
    graph: CityGraph,
    units: List[EmergencyUnit],
    incident_id: str,
    target_node: str,
    required_service_type: EmergencyUnitType,
    incident_severity: str = "moderate",
    active_corridor_roads: Optional[Set[str]] = None,
) -> List[ResourceRecommendation]:
    """
    Ranks emergency units based on service capability, availability, and Adjusted ETA.

    Definition of Adjusted ETA:
        The estimated travel time (in seconds) for the emergency responder to travel
        from its current location node to the target node, accounting for emergency
        vehicle dynamics (siren speedup and any active green corridors).
    """
    recommendations: List[ResourceRecommendation] = []

    if target_node not in graph.nodes:
        return []

    # 1. Filter by service type
    same_type_units = [u for u in units if u.unit_type == required_service_type]
    if not same_type_units:
        return []

    # Prefer available units, or fall back to earliest-free busy units if none available
    available_units = [u for u in same_type_units if u.availability == UnitStatus.AVAILABLE]
    candidates = available_units if available_units else same_type_units
    is_fallback = len(available_units) == 0

    ctx = RouteContext(
        vehicle_class=VehicleClass.EMERGENCY,
        corridor_roads=active_corridor_roads or set(),
    )

    for unit in candidates:
        route = astar(graph, unit.location_node, target_node, ctx=ctx)
        if not route:
            route = dijkstra(graph, unit.location_node, target_node, ctx=ctx)
        if not route:
            continue

        travel_time = route.estimated_travel_time_seconds
        # If unit is currently busy, add its remaining busy duration to adjusted ETA
        busy_delay = unit.busy_until_seconds if unit.availability != UnitStatus.AVAILABLE else 0.0
        adjusted_eta = travel_time + busy_delay

        match_reasons: List[str] = [
            f"Service type match: {unit.unit_type.value}",
            f"Unit status: {unit.availability.value}" + (f" (free in {round(busy_delay)}s)" if busy_delay > 0 else ""),
            f"Adjusted ETA: {round(adjusted_eta / 60.0, 1)} min ({round(route.total_distance_meters / 1000.0, 2)} km)",
        ]

        capability_bonus = 0.0
        if "advanced_life_support" in unit.capabilities and incident_severity in ["critical", "high"]:
            capability_bonus += BONUS_ALS_EQUIPPED
            match_reasons.append("Advanced Life Support (ALS) equipped")
        if "hydraulic_rescue_cutters" in unit.capabilities:
            capability_bonus += BONUS_RESCUE_CUTTERS
            match_reasons.append("Equipped with hydraulic rescue gear")
        if "rapid_response" in unit.capabilities:
            capability_bonus += BONUS_RAPID_RESPONSE
            match_reasons.append("Rapid response rated unit")

        if is_fallback:
            match_reasons.append("NOTE: No idle unit available; recommending earliest available busy unit")

        # Composite score strictly dominated by travel time
        time_score = 10000.0 / (adjusted_eta + 1.0)
        total_score = time_score + capability_bonus

        rec = ResourceRecommendation(
            unit=unit,
            incident_id=incident_id,
            target_node=target_node,
            adjusted_eta_seconds=adjusted_eta,
            distance_meters=route.total_distance_meters,
            route=route,
            score=total_score,
            rank=0,
            match_reasons=match_reasons,
        )
        recommendations.append(rec)

    recommendations.sort(key=lambda r: r.score, reverse=True)
    for idx, rec in enumerate(recommendations):
        rec.rank = idx + 1

    return recommendations


def create_emergency_corridor(
    graph: CityGraph,
    corridor_id: str,
    unit_id: str,
    incident_id: str,
    route: RoutePath,
) -> EmergencyCorridor:
    """
    Simulates emergency green wave corridor creation along the selected route.
    1. Sets traffic signals along route intersections to EMERGENCY_PRIORITY.
    2. Identifies cross-street incoming roads and holds their signals at RED.
    """
    route_nodes = route.node_ids
    route_roads = route.road_ids

    # Set signals along route
    for nid in route_nodes:
        graph.set_signal_state(nid, SignalState.EMERGENCY_PRIORITY)

    # Identify cross streets
    cross_streets: List[str] = []
    for nid in route_nodes:
        for incoming_edge in graph.reverse_adjacency.get(nid, []):
            if incoming_edge.road_id not in route_roads:
                cross_streets.append(incoming_edge.road_id)

    corridor_duration = route.estimated_travel_time_seconds * 1.25  # 25% safety margin

    return EmergencyCorridor(
        corridor_id=corridor_id,
        unit_id=unit_id,
        incident_id=incident_id,
        route_nodes=route_nodes,
        route_roads=route_roads,
        active=True,
        signal_prioritized_intersections=route_nodes,
        affected_cross_streets=list(set(cross_streets)),
        estimated_duration_seconds=corridor_duration,
    )


def plan_traffic_diversion(
    graph: CityGraph,
    incident_id: str,
    blocked_road_id: str,
    active_corridor_roads: Optional[Set[str]] = None,
    held_cross_streets: Optional[Set[str]] = None,
) -> TrafficDiversionPlan:
    """
    Generates a traffic diversion plan for civilian vehicles when an incident blocks a road.
    Computes detour from an upstream decision node (or source node) to the target downstream node,
    strictly avoiding the blocked road, active emergency corridor roads, and held cross-streets.
    """
    if blocked_road_id not in graph.edges:
        raise ValueError(f"Road {blocked_road_id} not found in graph.")

    blocked_edge = graph.edges[blocked_road_id]
    u = blocked_edge.source
    v = blocked_edge.target

    # Determine upstream decision node: look for incoming node into u
    incoming_edges = graph.reverse_adjacency.get(u, [])
    decision_node = u
    for inc_e in incoming_edges:
        if inc_e.road_id != blocked_road_id and not inc_e.is_closed:
            decision_node = inc_e.source
            break

    # Build exclusion set: blocked road + active emergency corridor + held cross streets
    excluded = {blocked_road_id}
    if active_corridor_roads:
        excluded.update(active_corridor_roads)
    if held_cross_streets:
        excluded.update(held_cross_streets)

    # Context for civilian diversion
    ctx = RouteContext(
        vehicle_class=VehicleClass.CIVILIAN,
        corridor_roads=active_corridor_roads or set(),
        held_cross_streets=held_cross_streets or set(),
    )

    # Compute detour from decision_node to v
    detour = dijkstra(graph, decision_node, v, ctx=ctx, excluded_road_ids=excluded)
    if not detour:
        detour = astar(graph, decision_node, v, ctx=ctx, excluded_road_ids=excluded)

    # Compute baseline distance & time through blocked edge
    orig_time = blocked_edge.base_travel_time_seconds
    orig_dist = blocked_edge.length_meters
    if decision_node != u:
        inc_edge = [e for e in graph.adjacency.get(decision_node, []) if e.target == u]
        if inc_edge:
            orig_dist += inc_edge[0].length_meters
            orig_time += inc_edge[0].base_travel_time_seconds

    affected_arterials: List[str] = [blocked_edge.name]

    if detour:
        extra_dist = max(0.0, detour.total_distance_meters - orig_dist)
        extra_time = max(0.0, detour.estimated_travel_time_seconds - orig_time)
        road_ids = detour.road_ids
        node_ids = detour.node_ids
        detour_dist = detour.total_distance_meters
        detour_time = detour.estimated_travel_time_seconds
        for rid in road_ids:
            affected_arterials.append(graph.edges[rid].name)
        instructions = (
            f"Approaching traffic diverted at decision intersection {graph.nodes[decision_node].name} ({decision_node}) "
            f"via {len(road_ids)} segment{'s' if len(road_ids) != 1 else ''} to rejoin at {graph.nodes[v].name} ({v})."
        )
    else:
        extra_dist = 0.0
        extra_time = 0.0
        road_ids = []
        node_ids = []
        detour_dist = 0.0
        detour_time = 0.0
        instructions = "No viable local detour found without using held cross-streets or emergency corridors."

    explanation = (
        f"Incident on {blocked_edge.name} ({blocked_road_id}) blocks traffic from {graph.nodes[u].name} to {graph.nodes[v].name}. "
        + (f"Detour established from {decision_node} adding {round(extra_dist/1000.0, 2)} km (+{round(extra_time)}s)."
           if detour else "Awaiting corridor clearance.")
    )

    return TrafficDiversionPlan(
        incident_id=incident_id,
        blocked_road_id=blocked_road_id,
        from_node=u,
        decision_node=decision_node,
        to_node=v,
        road_ids=road_ids,
        node_ids=node_ids,
        detour_distance_meters=detour_dist,
        detour_time_seconds=detour_time,
        extra_distance_meters=extra_dist,
        extra_time_seconds=extra_time,
        instructions=instructions,
        explanation=explanation,
        affected_arterials=list(set(affected_arterials)),
    )


def simulate_unit_movement_timeline(
    graph: CityGraph,
    unit: EmergencyUnit,
    route: RoutePath,
    time_step_seconds: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Simulates the emergency vehicle traveling along its designated route in discrete time steps.
    All outputs include 'simulated': true.
    """
    timeline: List[Dict[str, Any]] = []
    if not route.node_ids or not route.road_ids:
        return timeline

    total_time = route.estimated_travel_time_seconds
    total_dist = route.total_distance_meters
    avg_speed_mps = total_dist / max(total_time, 1.0)

    elapsed_time = 0.0
    accumulated_distance = 0.0

    segment_cum_dists: List[float] = [0.0]
    running_dist = 0.0
    for rid in route.road_ids:
        running_dist += graph.edges[rid].length_meters
        segment_cum_dists.append(running_dist)

    while elapsed_time <= total_time + time_step_seconds:
        current_dist = min(accumulated_distance, total_dist)
        fraction = current_dist / max(total_dist, 1.0)

        seg_idx = 0
        while seg_idx < len(route.road_ids) and segment_cum_dists[seg_idx + 1] < current_dist:
            seg_idx += 1
        seg_idx = min(seg_idx, len(route.road_ids) - 1)

        current_road = graph.edges[route.road_ids[seg_idx]]
        u_node = graph.nodes[current_road.source]
        v_node = graph.nodes[current_road.target]

        seg_start_dist = segment_cum_dists[seg_idx]
        seg_end_dist = segment_cum_dists[seg_idx + 1]
        seg_len = max(seg_end_dist - seg_start_dist, 1.0)
        seg_progress = max(0.0, min(1.0, (current_dist - seg_start_dist) / seg_len))

        current_lat = u_node.latitude + seg_progress * (v_node.latitude - u_node.latitude)
        current_lon = u_node.longitude + seg_progress * (v_node.longitude - u_node.longitude)

        is_arrived = (current_dist >= total_dist) or (elapsed_time >= total_time)
        status = UnitStatus.ON_SCENE.value if is_arrived else UnitStatus.EN_ROUTE.value

        timeline.append({
            "elapsed_seconds": round(elapsed_time, 1),
            "unit_id": unit.unit_id,
            "status": status,
            "current_road_id": current_road.road_id,
            "current_road_name": current_road.name,
            "current_latitude": round(current_lat, 6),
            "current_longitude": round(current_lon, 6),
            "distance_travelled_meters": round(current_dist, 1),
            "remaining_distance_meters": round(max(0.0, total_dist - current_dist), 1),
            "remaining_time_seconds": round(max(0.0, total_time - elapsed_time), 1),
            "percent_completed": round(fraction * 100.0, 1),
            "simulated": True,
        })

        if is_arrived:
            break

        elapsed_time += time_step_seconds
        accumulated_distance += avg_speed_mps * time_step_seconds

    return timeline
