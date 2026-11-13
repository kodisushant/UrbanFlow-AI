import uuid
from typing import List, Set, Optional, Dict, Any
from app.schemas.route import RouteResult, RoutePath, RouteStatus, SimulationStatus
from app.schemas.resource import EmergencyUnit
from app.schemas.incident import IncidentRecord
from app.services.city_graph_service import city_graph_service


class RouteOptimizationAgent:
    """
    Route Optimization Agent.
    Interfaces with the deterministic graph engine, calculates primary and alternative routes,
    designates signal priority corridors, populates geographic coordinates for Leaflet map rendering,
    and formats explainable routing decisions.
    """

    def plan_emergency_route(
        self,
        unit: EmergencyUnit,
        incident: IncidentRecord,
        avoid_road_ids: Optional[Set[str]] = None,
        algorithm: str = "astar"
    ) -> Optional[RouteResult]:
        origin = unit.current_node
        destination = incident.location_node
        avoid_roads = set(avoid_road_ids or [])

        # If incident has an affected road, avoid it
        if incident.affected_road_id:
            avoid_roads.add(incident.affected_road_id)

        # 1. Calculate Primary Route
        primary_path = city_graph_service.find_shortest_path(
            origin_node=origin,
            destination_node=destination,
            avoid_road_ids=avoid_roads,
            algorithm=algorithm
        )

        if not primary_path:
            return None

        # 2. Calculate Alternative Route by avoiding the first major road of the primary path
        alt_avoid = set(avoid_roads)
        if primary_path.road_ids:
            alt_avoid.add(primary_path.road_ids[0])

        alternative_path = city_graph_service.find_shortest_path(
            origin_node=origin,
            destination_node=destination,
            avoid_road_ids=alt_avoid,
            algorithm=algorithm
        )
        alt_routes = [alternative_path] if alternative_path else []

        # 3. Identify Signal Priority Nodes along the primary path (excluding terminus)
        signal_nodes = [
            nid for nid in primary_path.node_sequence
            if city_graph_service.get_node(nid) and city_graph_service.get_node(nid).is_signalized
        ]
        # Set signal state on graph
        city_graph_service.set_signal_priority(signal_nodes)

        # 4. Designate Diverted Roads
        diverted_roads = list(avoid_roads)
        for d_road in diverted_roads:
            city_graph_service.set_road_diverted(d_road, True)

        # 5. Extract coordinate list for frontend Leaflet polyline rendering
        coords = list(primary_path.coordinates) if primary_path.coordinates else []
        if not coords:
            for nid in primary_path.node_sequence:
                node = city_graph_service.get_node(nid)
                if node:
                    coords.append({"latitude": node.latitude, "longitude": node.longitude})

        # 6. Formulate human-readable explanation
        eta_min = round(primary_path.estimated_travel_time_seconds / 60.0, 1)
        savings_text = ""
        if alternative_path:
            diff = alternative_path.estimated_travel_time_seconds - primary_path.estimated_travel_time_seconds
            if diff > 0:
                savings_text = f" (saves approx {diff} seconds compared to alternative corridor)."

        explanation = (
            f"Optimized path via {algorithm.upper()} algorithm traversing {len(primary_path.node_sequence)} intersections. "
            f"Estimated ETA: {eta_min} min ({primary_path.estimated_travel_time_seconds}s) covering {primary_path.distance_meters}m{savings_text} "
            f"Green signal priority assigned to {len(signal_nodes)} intersections: {', '.join(signal_nodes[:4])}. "
            f"General traffic diverted away from {len(diverted_roads)} blocked/critical road segments: {', '.join(diverted_roads)}."
        )

        route_id = f"ROUTE-EMERGENCY-{uuid.uuid4().hex[:4].upper()}"

        return RouteResult(
            route_id=route_id,
            origin_node=origin,
            destination_node=destination,
            algorithm=algorithm,
            unit_id=unit.unit_id,
            unit_type=unit.unit_type,
            route_kind="emergency_corridor",
            incident_id=incident.incident_id,
            road_ids=primary_path.road_ids,
            node_ids=primary_path.node_sequence,
            total_distance_meters=primary_path.distance_meters,
            estimated_travel_time_seconds=primary_path.estimated_travel_time_seconds,
            estimated_travel_time_minutes=eta_min,
            coordinates=coords,
            unit_current_position={
                "node": unit.current_node,
                "latitude": unit.latitude,
                "longitude": unit.longitude
            },
            eta_seconds=primary_path.estimated_travel_time_seconds,
            route_status="active_dispatch",
            simulation_status="running",
            primary_route=primary_path,
            alternative_routes=alt_routes,
            avoided_roads=list(avoid_roads),
            signal_priority_nodes=signal_nodes,
            diverted_roads=diverted_roads,
            explanation=explanation
        )


route_agent = RouteOptimizationAgent()
