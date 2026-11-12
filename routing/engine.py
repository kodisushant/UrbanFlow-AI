"""
UrbanFlow AI - Central Route Optimization Engine
Member 4: Road Network, Emergency Routing & Traffic Diversion

Thread-safe orchestrator providing graph optimization, dynamic recalculation
with hysteresis, emergency responder selection, corridor lifecycle, and traffic diversion.
"""

from __future__ import annotations
import threading
import math
from typing import Dict, List, Optional, Any, Set
from .models import (
    Node,
    Edge,
    RoutePath,
    RouteResult,
    RouteContext,
    VehicleClass,
    EmergencyUnit,
    EmergencyUnitType,
    UnitStatus,
    ResourceRecommendation,
    EmergencyCorridor,
    TrafficDiversionPlan,
    SignalState,
    finite_or_none,
)
from .graph import CityGraph
from .algorithms import dijkstra, astar, yen_k_shortest_paths, penalty_based_alternatives
from .city_data import build_cyber_city_network, get_sample_emergency_units
from .emergency import (
    rank_emergency_resources,
    create_emergency_corridor,
    plan_traffic_diversion,
    simulate_unit_movement_timeline,
    map_incident_to_required_services,
)


class ActiveRouteTracker:
    """Tracks an in-progress route to support dynamic recalculation with hysteresis."""
    def __init__(
        self,
        route_id: str,
        origin: str,
        destination: str,
        current_route: RoutePath,
        is_emergency: bool = False,
        unit_id: Optional[str] = None,
        algorithm: str = "astar",
    ):
        self.route_id = route_id
        self.origin = origin
        self.destination = destination
        self.current_route = current_route
        self.is_emergency = is_emergency
        self.unit_id = unit_id
        self.algorithm = algorithm


class UrbanFlowRoutingEngine:
    """
    Main Route Optimization and Traffic Control Engine for UrbanFlow AI.
    Thread-safe (threading.RLock) for concurrent access in FastAPI / server environments.
    """

    def __init__(self, graph: Optional[CityGraph] = None):
        self._lock = threading.RLock()
        self.graph: CityGraph = graph or build_cyber_city_network()
        self.emergency_units: Dict[str, EmergencyUnit] = {
            u.unit_id: u for u in get_sample_emergency_units(self.graph)
        }
        self.active_corridors: Dict[str, EmergencyCorridor] = {}
        self.active_diversions: Dict[str, TrafficDiversionPlan] = {}
        self.active_routes: Dict[str, ActiveRouteTracker] = {}

    # -------------------------------------------------------------------------
    # Route Optimization (Dijkstra / A* / Alternatives)
    # -------------------------------------------------------------------------

    def find_route(
        self,
        origin_node: str,
        destination_node: str,
        algorithm: str = "astar",
        num_alternatives: int = 2,
        is_emergency: bool = False,
        unit_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        excluded_roads: Optional[List[str]] = None,
    ) -> RouteResult:
        """
        Calculate primary route and diverse alternative routes.
        Accounts for closures, congestion, emergency sirens, and active corridors.
        """
        with self._lock:
            if origin_node not in self.graph.nodes:
                raise ValueError(f"Origin node '{origin_node}' not found in graph.")
            if destination_node not in self.graph.nodes:
                raise ValueError(f"Destination node '{destination_node}' not found in graph.")

            algo_choice = algorithm.lower().strip()
            search_fn = astar if algo_choice == "astar" else dijkstra
            excluded_set = set(excluded_roads or [])

            # Determine RouteContext
            vclass = VehicleClass.EMERGENCY if is_emergency else VehicleClass.CIVILIAN
            corridor_roads: Set[str] = set()
            held_cross_streets: Set[str] = set()

            for corr in self.active_corridors.values():
                if corr.active:
                    corridor_roads.update(corr.route_roads)
                    held_cross_streets.update(corr.affected_cross_streets)

            ctx = RouteContext(
                vehicle_class=vclass,
                corridor_roads=corridor_roads,
                held_cross_streets=held_cross_streets,
                ignore_closures=False,
            )

            # 1. Compute baseline path with closures ignored to identify truly avoided closures
            base_ctx = RouteContext(
                vehicle_class=vclass,
                corridor_roads=corridor_roads,
                held_cross_streets=held_cross_streets,
                ignore_closures=True,
            )
            baseline_path = search_fn(self.graph, origin_node, destination_node, ctx=base_ctx, excluded_road_ids=excluded_set)
            blocked_roads_avoided: List[str] = []
            if baseline_path:
                blocked_roads_avoided = [
                    rid for rid in baseline_path.road_ids
                    if self.graph.edges[rid].is_closed
                ]

            # 2. Compute Primary Route respecting closures
            primary = search_fn(self.graph, origin_node, destination_node, ctx=ctx, excluded_road_ids=excluded_set)
            if not primary:
                # Clean "no path" result - no crash, finite_or_none returns null for inf
                return RouteResult(
                    origin_node=origin_node,
                    destination_node=destination_node,
                    algorithm=algo_choice,
                    primary_route=RoutePath([], [], 0.0, float("inf"), [], "Destination unreachable"),
                    alternative_routes=[],
                    blocked_roads_avoided=blocked_roads_avoided,
                    explanation=f"No traversable route found from {origin_node} to {destination_node}. Destination is unreachable due to road closures.",
                )

            # 3. Alternative Routes (Yen's K-Shortest Paths & Penalty Detours)
            alternatives: List[RoutePath] = []
            if num_alternatives > 0:
                k_paths = yen_k_shortest_paths(
                    self.graph,
                    origin_node,
                    destination_node,
                    k=num_alternatives + 1,
                    algorithm=algo_choice,
                    ctx=ctx,
                    excluded_road_ids=excluded_set,
                )
                for path in k_paths[1:]:
                    alternatives.append(path)

                if len(alternatives) < num_alternatives:
                    penalty_alts = penalty_based_alternatives(
                        self.graph,
                        origin_node,
                        destination_node,
                        primary_route=primary,
                        count=num_alternatives - len(alternatives),
                        algorithm=algo_choice,
                        ctx=ctx,
                    )
                    for palt in penalty_alts:
                        if not any(palt.node_ids == existing.node_ids for existing in alternatives):
                            alternatives.append(palt)

            # 4. Congestion avoided check
            congested_avoided = any(
                self.graph.edges[rid].congestion_factor > 2.0
                for rid in self.graph.edges
                if rid not in primary.road_ids
            )

            # 5. Explanation rationale
            explanation = self._generate_route_explanation(
                primary=primary,
                baseline=baseline_path,
                alternatives=alternatives,
                is_emergency=is_emergency,
                algorithm=algo_choice,
                blocked_roads_avoided=blocked_roads_avoided,
            )

            return RouteResult(
                origin_node=origin_node,
                destination_node=destination_node,
                algorithm=algo_choice,
                primary_route=primary,
                alternative_routes=alternatives,
                blocked_roads_avoided=blocked_roads_avoided,
                congestion_avoided=congested_avoided,
                is_emergency_route=is_emergency,
                unit_id=unit_id,
                incident_id=incident_id,
                explanation=explanation,
            )

    def _generate_route_explanation(
        self,
        primary: RoutePath,
        baseline: Optional[RoutePath],
        alternatives: List[RoutePath],
        is_emergency: bool,
        algorithm: str,
        blocked_roads_avoided: List[str],
    ) -> str:
        """Construct human-readable route rationale with grammatical correctness."""
        dist_km = round(primary.total_distance_meters / 1000.0, 2)
        mins = round(primary.estimated_travel_time_seconds / 60.0, 1)
        num_segs = len(primary.road_ids)

        parts = [
            f"Selected route via {num_segs} segment{'s' if num_segs != 1 else ''} covering {dist_km} km "
            f"with an estimated travel time of {mins} minutes using {algorithm.upper()} optimization."
        ]

        # Only mention detour if path differs from baseline and avoided blocked roads
        if baseline and primary.road_ids != baseline.road_ids and blocked_roads_avoided:
            parts.append(
                f"Detoured around closed road segment(s) ({', '.join(blocked_roads_avoided)}) "
                f"on the direct baseline corridor."
            )

        if is_emergency:
            parts.append("Emergency priority siren dynamics and green-corridor priority applied.")

        if alternatives:
            alt_summaries = [
                f"Alt #{i+1}: {round(a.estimated_travel_time_seconds/60.0, 1)} min ({round(a.total_distance_meters/1000.0, 2)} km, {round(a.overlap_ratio*100)}% overlap)"
                for i, a in enumerate(alternatives)
            ]
            parts.append(f"Identified {len(alternatives)} alternative route{'s' if len(alternatives) != 1 else ''} ({', '.join(alt_summaries)}).")

        return " ".join(parts)

    # -------------------------------------------------------------------------
    # Road Closures, Partial Lane Reductions & Reopenings
    # -------------------------------------------------------------------------

    def report_incident_blockage(
        self,
        incident_id: str,
        road_id: str,
        reason: str = "vehicle_collision",
        direction: str = "both",
    ) -> List[str]:
        """Close road segment(s), trigger diversion planning and active route recalculation."""
        with self._lock:
            closed_ids = self.graph.close_road(road_id, reason=reason, direction=direction)
            if closed_ids:
                # Active corridor roads to avoid
                active_corr_roads: Set[str] = set()
                held_cross_streets: Set[str] = set()
                for c in self.active_corridors.values():
                    if c.active:
                        active_corr_roads.update(c.route_roads)
                        held_cross_streets.update(c.affected_cross_streets)

                diversion = plan_traffic_diversion(
                    graph=self.graph,
                    incident_id=incident_id,
                    blocked_road_id=road_id,
                    active_corridor_roads=active_corr_roads,
                    held_cross_streets=held_cross_streets,
                )
                self.active_diversions[incident_id] = diversion
                self.recompute_active_routes()
            return closed_ids

    def clear_incident_blockage(self, incident_id: str, road_id: str, direction: str = "both") -> List[str]:
        """Reopen a road segment after incident resolution and remove diversion."""
        with self._lock:
            reopened = self.graph.reopen_road(road_id, direction=direction)
            if incident_id in self.active_diversions:
                del self.active_diversions[incident_id]
            self.recompute_active_routes()
            return reopened

    def set_lane_blockage(
        self,
        road_id: str,
        remaining_capacity_fraction: float,
        direction: str = "forward",
    ) -> List[str]:
        """Set partial capacity blockage (e.g. 0.5 capacity) and recompute active routes."""
        with self._lock:
            modified = self.graph.set_lane_blockage(road_id, remaining_capacity_fraction, direction=direction)
            if modified:
                self.recompute_active_routes()
            return modified

    def update_road_congestion(self, road_id: str, factor: float) -> bool:
        """Update live congestion factor for a road segment."""
        with self._lock:
            success = self.graph.update_congestion(road_id, factor)
            if success:
                self.recompute_active_routes()
            return success

    def apply_traffic_forecast(self, observations: List[Dict[str, Any]]) -> int:
        """Apply congestion updates from Member 3's ML forecast or CCTV observation."""
        with self._lock:
            count = self.graph.bulk_update_traffic_observations(observations)
            if count > 0:
                self.recompute_active_routes()
            return count

    # -------------------------------------------------------------------------
    # Route Recalculation with Hysteresis (Anti-Fluttering)
    # -------------------------------------------------------------------------

    def register_active_route(
        self,
        route_id: str,
        origin: str,
        destination: str,
        current_route: RoutePath,
        is_emergency: bool = False,
        unit_id: Optional[str] = None,
        algorithm: str = "astar",
    ) -> None:
        """Register an active tracked route for dynamic recalculation."""
        with self._lock:
            self.active_routes[route_id] = ActiveRouteTracker(
                route_id=route_id,
                origin=origin,
                destination=destination,
                current_route=current_route,
                is_emergency=is_emergency,
                unit_id=unit_id,
                algorithm=algorithm,
            )

    def unregister_active_route(self, route_id: str) -> None:
        """Remove a completed or cancelled active route."""
        with self._lock:
            if route_id in self.active_routes:
                del self.active_routes[route_id]

    def recompute_active_routes(
        self,
        threshold_improvement_fraction: float = 0.10,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Recomputes all registered active routes when network state changes.
        Applies hysteresis: only switches route if new path is at least 10% faster,
        preventing route fluttering / flip-flopping.
        """
        with self._lock:
            results: Dict[str, Dict[str, Any]] = {}
            for route_id, tracker in list(self.active_routes.items()):
                # Determine RouteContext
                vclass = VehicleClass.EMERGENCY if tracker.is_emergency else VehicleClass.CIVILIAN
                corridor_roads: Set[str] = set()
                held_cross_streets: Set[str] = set()
                for corr in self.active_corridors.values():
                    if corr.active:
                        corridor_roads.update(corr.route_roads)
                        held_cross_streets.update(corr.affected_cross_streets)

                ctx = RouteContext(
                    vehicle_class=vclass,
                    corridor_roads=corridor_roads,
                    held_cross_streets=held_cross_streets,
                )

                # Re-evaluate current route's travel time
                current_time = 0.0
                is_current_blocked = False
                for rid in tracker.current_route.road_ids:
                    edge = self.graph.edges.get(rid)
                    if not edge or edge.is_closed:
                        is_current_blocked = True
                        current_time = float("inf")
                        break
                    cost = edge.compute_travel_time(ctx)
                    if math.isinf(cost):
                        is_current_blocked = True
                        current_time = float("inf")
                        break
                    current_time += cost

                # Search for candidate path
                search_fn = astar if tracker.algorithm == "astar" else dijkstra
                candidate = search_fn(self.graph, tracker.origin, tracker.destination, ctx=ctx)

                if not candidate:
                    results[route_id] = {
                        "switched": False,
                        "status": "unreachable",
                        "current_time": finite_or_none(current_time),
                    }
                    continue

                new_time = candidate.estimated_travel_time_seconds
                should_switch = False
                improvement = 0.0

                if is_current_blocked:
                    should_switch = True
                    improvement = 1.0
                elif current_time > 0 and not math.isinf(current_time):
                    improvement = (current_time - new_time) / current_time
                    if improvement >= threshold_improvement_fraction:
                        should_switch = True

                if should_switch:
                    tracker.current_route = candidate
                    results[route_id] = {
                        "switched": True,
                        "old_time_seconds": finite_or_none(current_time),
                        "new_time_seconds": finite_or_none(new_time),
                        "improvement_percent": round(improvement * 100.0, 1),
                        "new_nodes": candidate.node_ids,
                    }
                else:
                    results[route_id] = {
                        "switched": False,
                        "current_time_seconds": finite_or_none(current_time),
                        "potential_improvement_percent": round(improvement * 100.0, 1),
                    }

            return results

    # -------------------------------------------------------------------------
    # Emergency Unit Dispatch & Corridor Orchestration
    # -------------------------------------------------------------------------

    def select_and_rank_emergency_units(
        self,
        incident_id: str,
        incident_type: str,
        incident_latitude: float,
        incident_longitude: float,
        severity: str = "moderate",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ranks nearest suitable emergency units across required service categories.
        """
        with self._lock:
            nearest_node = self.graph.find_nearest_node(incident_latitude, incident_longitude)
            if not nearest_node:
                return {}

            required_services = map_incident_to_required_services(incident_type, severity=severity)
            results: Dict[str, List[Dict[str, Any]]] = {}

            active_corr_roads: Set[str] = set()
            for c in self.active_corridors.values():
                if c.active:
                    active_corr_roads.update(c.route_roads)

            for service_type in required_services:
                ranked = rank_emergency_resources(
                    graph=self.graph,
                    units=list(self.emergency_units.values()),
                    incident_id=incident_id,
                    target_node=nearest_node.node_id,
                    required_service_type=service_type,
                    incident_severity=severity,
                    active_corridor_roads=active_corr_roads,
                )
                results[service_type.value] = [r.to_dict() for r in ranked]

            return results

    def dispatch_emergency_corridor(
        self,
        corridor_id: str,
        unit_id: str,
        incident_id: str,
        route: RoutePath,
    ) -> Dict[str, Any]:
        """
        Activate emergency green corridor and mark unit as DISPATCHED.
        """
        with self._lock:
            if unit_id in self.emergency_units:
                self.emergency_units[unit_id].availability = UnitStatus.DISPATCHED

            corridor = create_emergency_corridor(
                graph=self.graph,
                corridor_id=corridor_id,
                unit_id=unit_id,
                incident_id=incident_id,
                route=route,
            )
            self.active_corridors[corridor_id] = corridor
            return corridor.to_dict()

    def clear_emergency_corridor(self, corridor_id: str) -> bool:
        """Deactivate corridor and restore prioritized intersection signals to GREEN."""
        with self._lock:
            corridor = self.active_corridors.get(corridor_id)
            if not corridor:
                return False

            for nid in corridor.route_nodes:
                self.graph.set_signal_state(nid, SignalState.GREEN)

            corridor.active = False
            del self.active_corridors[corridor_id]
            return True

    def release_unit(self, unit_id: str) -> bool:
        """Release a dispatched unit back to AVAILABLE status and clear any active corridors."""
        with self._lock:
            if unit_id not in self.emergency_units:
                return False

            unit = self.emergency_units[unit_id]
            unit.availability = UnitStatus.AVAILABLE
            unit.busy_until_seconds = 0.0

            # Clear any active corridor belonging to this unit
            to_clear = [cid for cid, corr in self.active_corridors.items() if corr.unit_id == unit_id]
            for cid in to_clear:
                self.clear_emergency_corridor(cid)

            return True

    def simulate_emergency_movement(
        self,
        unit_id: str,
        route: RoutePath,
        time_step_seconds: float = 15.0,
    ) -> List[Dict[str, Any]]:
        """Generate time-step trajectory simulation of the emergency unit."""
        with self._lock:
            unit = self.emergency_units.get(unit_id)
            if not unit:
                raise ValueError(f"Emergency unit '{unit_id}' not found.")

            timeline = simulate_unit_movement_timeline(
                graph=self.graph,
                unit=unit,
                route=route,
                time_step_seconds=time_step_seconds,
            )
            return timeline

    # -------------------------------------------------------------------------
    # Full Demonstration Scenario Runner
    # -------------------------------------------------------------------------

    def run_demonstration_scenario(self) -> Dict[str, Any]:
        """
        Executes a deterministic end-to-end benchmark scenario demonstrating all 12 requirements.
        """
        with self._lock:
            incident_id = "INC-DEMO-001"
            incident_type = "two_car_collision_with_injury"
            incident_lat, incident_lon = 17.4485, 78.3740  # INT-03 (Cyber Gateway)
            blocked_road = "ROAD-03A"

            # 1. Pre-incident route from Hospital North (INT-04) to City Center (INT-01)
            pre_route = self.find_route("INT-04", "INT-01", algorithm="astar", num_alternatives=1)

            # 2. Block road due to incident (both directions)
            closed_ids = self.report_incident_blockage(incident_id, blocked_road, reason="two_car_collision", direction="both")

            # 3. Simulate adjacent congestion spillover
            self.update_road_congestion("ROAD-01A", 2.8)

            # 4. Rank and select emergency units
            unit_rankings = self.select_and_rank_emergency_units(
                incident_id=incident_id,
                incident_type=incident_type,
                incident_latitude=incident_lat,
                incident_longitude=incident_lon,
                severity="high",
            )

            best_ambulance = unit_rankings.get("ambulance", [{}])[0]
            amb_unit_id = best_ambulance.get("unit_id", "AMB-01")

            # 5. Recalculate emergency route from ambulance station to incident
            amb_route_result = self.find_route(
                origin_node=self.emergency_units[amb_unit_id].location_node,
                destination_node="INT-03",
                algorithm="astar",
                num_alternatives=2,
                is_emergency=True,
                unit_id=amb_unit_id,
                incident_id=incident_id,
            )

            # 6. Activate green corridor
            corridor = self.dispatch_emergency_corridor(
                corridor_id="CORRIDOR-DEMO-01",
                unit_id=amb_unit_id,
                incident_id=incident_id,
                route=amb_route_result.primary_route,
            )

            # 7. Get civilian diversion plan
            diversion_plan = self.active_diversions.get(incident_id)

            # 8. Simulate vehicle movement
            movement_timeline = self.simulate_emergency_movement(
                unit_id=amb_unit_id,
                route=amb_route_result.primary_route,
                time_step_seconds=20.0,
            )

            return {
                "scenario": "Cyber City Emergency Response Benchmark",
                "simulated": True,
                "incident": {
                    "incident_id": incident_id,
                    "type": incident_type,
                    "coordinates": {"latitude": incident_lat, "longitude": incident_lon},
                    "blocked_roads": closed_ids,
                },
                "pre_incident_route": pre_route.to_dict(),
                "emergency_unit_rankings": unit_rankings,
                "assigned_unit_id": amb_unit_id,
                "emergency_route": amb_route_result.to_dict(),
                "emergency_corridor": corridor,
                "civilian_diversion_plan": diversion_plan.to_dict() if diversion_plan else None,
                "movement_timeline": movement_timeline,
                "graph_summary": {
                    "total_nodes": len(self.graph.nodes),
                    "total_edges": len(self.graph.edges),
                    "closed_edges": [e.road_id for e in self.graph.edges.values() if e.is_closed],
                },
            }
