"""
UrbanFlow AI - Routing Service Layer
Member 4: Road Network, Emergency Routing & Traffic Diversion

Service class providing a clean, dictionary-based interface for Member 1's backend orchestration.
Pure Python - zero third-party dependencies required.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from .engine import UrbanFlowRoutingEngine
from .models import RoutePath


class RoutingService:
    """
    High-level service class wrapping the UrbanFlow routing engine.
    All inputs and outputs are plain Python dictionaries and primitives.
    """

    def __init__(self, engine: Optional[UrbanFlowRoutingEngine] = None):
        self.engine = engine or UrbanFlowRoutingEngine()

    def compute_route(
        self,
        origin_node: str,
        destination_node: str,
        algorithm: str = "astar",
        num_alternatives: int = 2,
        is_emergency: bool = False,
        unit_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        excluded_roads: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Calculates primary and alternative routes between two intersections."""
        result = self.engine.find_route(
            origin_node=origin_node,
            destination_node=destination_node,
            algorithm=algorithm,
            num_alternatives=num_alternatives,
            is_emergency=is_emergency,
            unit_id=unit_id,
            incident_id=incident_id,
            excluded_roads=excluded_roads,
        )
        return result.to_dict()

    def rank_units(
        self,
        incident_id: str,
        incident_type: str,
        latitude: float,
        longitude: float,
        severity: str = "moderate",
    ) -> Dict[str, Any]:
        """Ranks available emergency responders by ETA and capability."""
        rankings = self.engine.select_and_rank_emergency_units(
            incident_id=incident_id,
            incident_type=incident_type,
            incident_latitude=latitude,
            incident_longitude=longitude,
            severity=severity,
        )
        return {"incident_id": incident_id, "rankings": rankings, "simulated": True}

    def dispatch_emergency(
        self,
        corridor_id: str,
        unit_id: str,
        incident_id: str,
        target_node: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches an emergency responder, calculating its route and establishing a green corridor."""
        unit = self.engine.emergency_units.get(unit_id)
        if not unit:
            raise ValueError(f"Emergency unit '{unit_id}' not found.")

        dest = target_node or "INT-03"
        route_res = self.engine.find_route(
            origin_node=unit.location_node,
            destination_node=dest,
            algorithm="astar",
            num_alternatives=1,
            is_emergency=True,
            unit_id=unit_id,
            incident_id=incident_id,
        )

        corridor_data = self.engine.dispatch_emergency_corridor(
            corridor_id=corridor_id,
            unit_id=unit_id,
            incident_id=incident_id,
            route=route_res.primary_route,
        )

        return {
            "corridor": corridor_data,
            "route": route_res.to_dict(),
            "simulated": True,
        }

    def close_road(
        self,
        road_id: str,
        reason: str = "accident_blockage",
        direction: str = "both",
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Closes road segment(s) and establishes a civilian diversion detour."""
        inc_id = incident_id or f"INC-AUTOCLOSE-{road_id}"
        closed_ids = self.engine.report_incident_blockage(
            incident_id=inc_id,
            road_id=road_id,
            reason=reason,
            direction=direction,
        )
        diversion = self.engine.active_diversions.get(inc_id)
        return {
            "status": "closed",
            "closed_roads": closed_ids,
            "incident_id": inc_id,
            "diversion_plan": diversion.to_dict() if diversion else None,
            "simulated": True,
        }

    def reopen_road(self, road_id: str, direction: str = "both", incident_id: Optional[str] = None) -> Dict[str, Any]:
        """Reopens a previously closed road segment and clears any associated diversion."""
        inc_id = incident_id or f"INC-AUTOCLOSE-{road_id}"
        reopened = self.engine.clear_incident_blockage(incident_id=inc_id, road_id=road_id, direction=direction)
        return {
            "status": "reopened",
            "reopened_roads": reopened,
            "simulated": True,
        }

    def update_traffic(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Applies traffic congestion observations and triggers route recalculation."""
        count = self.engine.apply_traffic_forecast(observations)
        active_route_updates = self.engine.recompute_active_routes()
        return {
            "status": "updated",
            "observations_applied": count,
            "active_route_updates": active_route_updates,
            "simulated": True,
        }

    def compute_diversion(self, incident_id: str, blocked_road_id: str) -> Dict[str, Any]:
        """Computes civilian traffic diversion plan around a blockage."""
        from .emergency import plan_traffic_diversion
        corr_roads = set()
        held_cross = set()
        for c in self.engine.active_corridors.values():
            if c.active:
                corr_roads.update(c.route_roads)
                held_cross.update(c.affected_cross_streets)

        plan = plan_traffic_diversion(
            graph=self.engine.graph,
            incident_id=incident_id,
            blocked_road_id=blocked_road_id,
            active_corridor_roads=corr_roads,
            held_cross_streets=held_cross,
        )
        return plan.to_dict()

    def simulate_movement(
        self,
        unit_id: str,
        destination_node: str = "INT-03",
        time_step_seconds: float = 15.0,
    ) -> Dict[str, Any]:
        """Generates step-by-step vehicle trajectory frames."""
        unit = self.engine.emergency_units.get(unit_id)
        if not unit:
            raise ValueError(f"Emergency unit '{unit_id}' not found.")

        route_res = self.engine.find_route(
            origin_node=unit.location_node,
            destination_node=destination_node,
            algorithm="astar",
            is_emergency=True,
            unit_id=unit_id,
        )

        timeline = self.engine.simulate_emergency_movement(
            unit_id=unit_id,
            route=route_res.primary_route,
            time_step_seconds=time_step_seconds,
        )

        return {
            "unit_id": unit_id,
            "route": route_res.to_dict(),
            "timeline": timeline,
            "simulated": True,
        }

    def get_graph_geojson(self) -> Dict[str, Any]:
        """Returns standard GeoJSON FeatureCollection of the city network."""
        return self.engine.graph.to_geojson()

