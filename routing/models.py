"""
UrbanFlow AI - Graph Optimization & Routing Models
Member 4: Road Network, Emergency Routing & Traffic Diversion
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Set
from enum import Enum


# -----------------------------------------------------------------------------
# Global Speed and Corridor Tuning Constants
# -----------------------------------------------------------------------------
SIREN_SPEEDUP = 1.25           # Emergency siren speedup (~25% faster than baseline traffic)
CORRIDOR_FACTOR = 0.80         # Additional 20% speedup along prioritized green corridor
MAX_COMBINED_SPEEDUP = 2.00    # Hard cap on emergency vehicle speedup (cost >= base / 2.0)
DEFAULT_HOLD_DELAY_SECONDS = 45.0  # Simulated delay added to civilian vehicles at held cross-streets


def finite_or_none(val: Optional[float], decimals: int = 2) -> Optional[float]:
    """
    Ensures floats exported to JSON are strictly finite.
    Returns None for infinite or NaN values, preventing invalid 'Infinity' in JSON output.
    """
    if val is None or math.isinf(val) or math.isnan(val):
        return None
    return round(float(val), decimals)


class VehicleClass(str, Enum):
    CIVILIAN = "civilian"
    EMERGENCY = "emergency"


class NodeType(str, Enum):
    INTERSECTION = "intersection"
    HOSPITAL = "hospital"
    FIRE_STATION = "fire_station"
    POLICE_STATION = "police_station"
    TRANSIT_HUB = "transit_hub"


class SignalState(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    AMBER = "AMBER"
    EMERGENCY_PRIORITY = "EMERGENCY_PRIORITY"


class CongestionLevel(str, Enum):
    FREE_FLOW = "free_flow"      # factor ~1.0
    MODERATE = "moderate"        # factor ~1.6
    HEAVY = "heavy"              # factor ~2.5
    SEVERE = "severe"            # factor ~3.5
    GRIDLOCK = "gridlock"        # factor ~4.5


class EmergencyUnitType(str, Enum):
    AMBULANCE = "ambulance"
    FIRE_ENGINE = "fire_engine"
    POLICE = "police"


class UnitStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    BUSY = "busy"


@dataclass
class RouteContext:
    """
    Contextual parameters for dynamic edge cost evaluation.
    Separates civilian vs emergency routing dynamics and active green corridor holds.
    """
    vehicle_class: VehicleClass = VehicleClass.CIVILIAN
    corridor_roads: Set[str] = field(default_factory=set)
    held_cross_streets: Set[str] = field(default_factory=set)
    hold_delay_s: float = DEFAULT_HOLD_DELAY_SECONDS
    ignore_closures: bool = False  # Used internally to compute unblocked baseline paths


@dataclass
class Node:
    """Represents a road intersection or facility landmark."""
    node_id: str
    name: str
    latitude: float
    longitude: float
    node_type: NodeType = NodeType.INTERSECTION
    signal_state: SignalState = SignalState.GREEN
    signal_cycle_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "node_type": self.node_type.value if isinstance(self.node_type, Enum) else str(self.node_type),
            "signal_state": self.signal_state.value if isinstance(self.signal_state, Enum) else str(self.signal_state),
            "signal_cycle_seconds": self.signal_cycle_seconds,
            "simulated": True,
        }


@dataclass
class Edge:
    """Represents a directed road segment connecting two nodes."""
    road_id: str
    source: str
    target: str
    name: str
    length_meters: float
    speed_limit_kmph: float
    lanes: int = 2
    is_one_way: bool = False
    pair_id: Optional[str] = None       # Shared ID for forward/reverse pair
    direction: str = "forward"          # 'forward' or 'reverse'
    congestion_factor: float = 1.0     # 1.0 = free flow; higher = slower
    capacity_fraction: float = 1.0     # Remaining lane capacity (1.0 = full, 0.5 = half lanes blocked)
    is_closed: bool = False             # True if closed due to accident/roadblock
    closure_reason: Optional[str] = None

    @property
    def base_travel_time_seconds(self) -> float:
        """Calculates free-flow travel time: length / (speed in m/s)."""
        speed_mps = (self.speed_limit_kmph * 1000.0) / 3600.0
        return self.length_meters / max(speed_mps, 0.1)

    def compute_travel_time(self, ctx: Optional[RouteContext] = None) -> float:
        """
        Calculates dynamic travel time accounting for closures, congestion,
        emergency siren speedup, corridor prioritization, and cross-street signal holds.
        """
        if self.is_closed and (ctx is None or not ctx.ignore_closures):
            return float("inf")

        # Base travel time under current congestion
        speed_mps = (self.speed_limit_kmph * 1000.0) / 3600.0
        effective_congestion = max(1.0, self.congestion_factor)
        base = (self.length_meters / max(speed_mps, 0.1)) * effective_congestion

        if ctx is None or ctx.vehicle_class == VehicleClass.CIVILIAN:
            cost = base
            if ctx and self.road_id in ctx.held_cross_streets:
                cost += ctx.hold_delay_s
            return cost
        else:
            # Emergency vehicle with sirens active
            cost = base / SIREN_SPEEDUP
            if ctx and self.road_id in ctx.corridor_roads:
                cost *= CORRIDOR_FACTOR
            # Enforce hard cap on combined speedup
            min_allowed_cost = base / MAX_COMBINED_SPEEDUP
            return max(cost, min_allowed_cost)

    @property
    def effective_travel_time_seconds(self) -> float:
        """Default effective travel time for civilian vehicle under standard conditions."""
        return self.compute_travel_time(None)

    def to_dict(self) -> Dict[str, Any]:
        eff_time = self.effective_travel_time_seconds
        return {
            "road_id": self.road_id,
            "pair_id": self.pair_id or self.road_id,
            "direction": self.direction,
            "source": self.source,
            "target": self.target,
            "name": self.name,
            "length_meters": self.length_meters,
            "speed_limit_kmph": self.speed_limit_kmph,
            "lanes": self.lanes,
            "is_one_way": self.is_one_way,
            "congestion_factor": round(self.congestion_factor, 2),
            "capacity_fraction": round(self.capacity_fraction, 2),
            "is_closed": self.is_closed,
            "closure_reason": self.closure_reason,
            "base_travel_time_seconds": round(self.base_travel_time_seconds, 1),
            "effective_travel_time_seconds": finite_or_none(eff_time, 1),
        }


@dataclass
class RoutePath:
    """Represents a computed route from origin to destination."""
    node_ids: List[str]
    road_ids: List[str]
    total_distance_meters: float
    estimated_travel_time_seconds: float
    coordinates: List[Tuple[float, float]] = field(default_factory=list)  # [(lat, lon), ...]
    summary: str = ""
    overlap_ratio: float = 0.0  # Shared length ratio with primary path (0.0 for primary)

    def to_dict(self) -> Dict[str, Any]:
        time_s = finite_or_none(self.estimated_travel_time_seconds, 1)
        time_min = finite_or_none(self.estimated_travel_time_seconds / 60.0, 2) if time_s is not None else None
        return {
            "node_ids": self.node_ids,
            "road_ids": self.road_ids,
            "total_distance_meters": round(self.total_distance_meters, 1),
            "estimated_travel_time_seconds": time_s,
            "estimated_travel_time_minutes": time_min,
            "coordinates": [{"latitude": lat, "longitude": lon} for lat, lon in self.coordinates],
            "summary": self.summary,
            "overlap_ratio": round(self.overlap_ratio, 2),
        }


@dataclass
class RouteResult:
    """Complete response for route optimization, matching proposed v1 API contract."""
    origin_node: str
    destination_node: str
    algorithm: str
    primary_route: RoutePath
    alternative_routes: List[RoutePath] = field(default_factory=list)
    blocked_roads_avoided: List[str] = field(default_factory=list)
    congestion_avoided: bool = False
    is_emergency_route: bool = False
    unit_id: Optional[str] = None
    incident_id: Optional[str] = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        time_s = finite_or_none(self.primary_route.estimated_travel_time_seconds, 1)
        time_min = finite_or_none(self.primary_route.estimated_travel_time_seconds / 60.0, 2) if time_s is not None else None
        return {
            "origin_node": self.origin_node,
            "destination_node": self.destination_node,
            "algorithm": self.algorithm,
            "unit_id": self.unit_id,
            "incident_id": self.incident_id,
            "is_emergency_route": self.is_emergency_route,
            "road_ids": self.primary_route.road_ids,
            "node_ids": self.primary_route.node_ids,
            "estimated_travel_time_seconds": time_s,
            "estimated_travel_time_minutes": time_min,
            "total_distance_meters": round(self.primary_route.total_distance_meters, 1),
            "coordinates": [{"latitude": lat, "longitude": lon} for lat, lon in self.primary_route.coordinates],
            "blocked_roads_avoided": self.blocked_roads_avoided,
            "congestion_avoided": self.congestion_avoided,
            "alternative_routes": [alt.to_dict() for alt in self.alternative_routes],
            "explanation": self.explanation,
            "simulated": True,
        }


@dataclass
class EmergencyUnit:
    """Represents an emergency responder vehicle."""
    unit_id: str
    unit_type: EmergencyUnitType
    location_node: str
    latitude: float
    longitude: float
    availability: UnitStatus = UnitStatus.AVAILABLE
    capabilities: List[str] = field(default_factory=list)
    speed_factor: float = SIREN_SPEEDUP
    busy_until_seconds: float = 0.0     # Time until unit becomes free if BUSY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "type": self.unit_type.value if isinstance(self.unit_type, Enum) else str(self.unit_type),
            "location_node": self.location_node,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "availability": self.availability.value if isinstance(self.availability, Enum) else str(self.availability),
            "capabilities": self.capabilities,
            "speed_factor": self.speed_factor,
            "busy_until_seconds": round(self.busy_until_seconds, 1),
            "simulated": True,
        }


@dataclass
class ResourceRecommendation:
    """Scored emergency unit recommendation for an incident."""
    unit: EmergencyUnit
    incident_id: str
    target_node: str
    adjusted_eta_seconds: float     # Explicit Adjusted ETA (with emergency dynamics)
    distance_meters: float
    route: RoutePath
    score: float
    rank: int
    match_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        time_s = finite_or_none(self.adjusted_eta_seconds, 1)
        time_min = finite_or_none(self.adjusted_eta_seconds / 60.0, 2) if time_s is not None else None
        return {
            "unit_id": self.unit.unit_id,
            "unit_type": self.unit.unit_type.value if isinstance(self.unit.unit_type, Enum) else str(self.unit.unit_type),
            "incident_id": self.incident_id,
            "target_node": self.target_node,
            "rank": self.rank,
            "score": round(self.score, 2),
            "adjusted_eta_seconds": time_s,
            "estimated_travel_time_seconds": time_s,
            "estimated_travel_time_minutes": time_min,
            "distance_meters": round(self.distance_meters, 1),
            "availability": self.unit.availability.value if isinstance(self.unit.availability, Enum) else str(self.unit.availability),
            "capabilities": self.unit.capabilities,
            "route_nodes": self.route.node_ids,
            "route_roads": self.route.road_ids,
            "match_reasons": self.match_reasons,
            "simulated": True,
        }


@dataclass
class EmergencyCorridor:
    """Active emergency green corridor along a designated route."""
    corridor_id: str
    unit_id: str
    incident_id: str
    route_nodes: List[str]
    route_roads: List[str]
    active: bool
    signal_prioritized_intersections: List[str]
    affected_cross_streets: List[str]
    estimated_duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corridor_id": self.corridor_id,
            "unit_id": self.unit_id,
            "incident_id": self.incident_id,
            "route_nodes": self.route_nodes,
            "route_roads": self.route_roads,
            "active": self.active,
            "signal_prioritized_intersections": self.signal_prioritized_intersections,
            "affected_cross_streets": self.affected_cross_streets,
            "estimated_duration_seconds": round(self.estimated_duration_seconds, 1),
            "simulated": True,
        }


@dataclass
class TrafficDiversionPlan:
    """Plan for diverting regular civilian traffic around blocked road segments."""
    incident_id: str
    blocked_road_id: str
    from_node: str              # Upstream source node of blocked road
    decision_node: str          # Intersection where traffic diverts
    to_node: str                # Target downstream intersection
    road_ids: List[str]         # Detour route road IDs
    node_ids: List[str]         # Detour route node IDs
    detour_distance_meters: float
    detour_time_seconds: float
    extra_distance_meters: float
    extra_time_seconds: float
    instructions: str
    explanation: str = ""
    affected_arterials: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "blocked_road_id": self.blocked_road_id,
            "from_node": self.from_node,
            "decision_node": self.decision_node,
            "to_node": self.to_node,
            "road_ids": self.road_ids,
            "node_ids": self.node_ids,
            "detour_distance_meters": round(self.detour_distance_meters, 1),
            "detour_time_seconds": round(self.detour_time_seconds, 1),
            "extra_distance_meters": round(self.extra_distance_meters, 1),
            "extra_time_seconds": round(self.extra_time_seconds, 1),
            "instructions": self.instructions,
            "explanation": self.explanation,
            "affected_arterials": self.affected_arterials,
            "simulated": True,
        }
