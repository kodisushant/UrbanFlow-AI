"""
UrbanFlow AI - Routing and Graph Optimization Module
Member 4: Road Network, Emergency Routing & Traffic Diversion
"""

from .models import (
    Node,
    Edge,
    NodeType,
    SignalState,
    EmergencyUnitType,
    UnitStatus,
    VehicleClass,
    RouteContext,
    RoutePath,
    RouteResult,
    EmergencyUnit,
    ResourceRecommendation,
    EmergencyCorridor,
    TrafficDiversionPlan,
    finite_or_none,
    SIREN_SPEEDUP,
    CORRIDOR_FACTOR,
    MAX_COMBINED_SPEEDUP,
    DEFAULT_HOLD_DELAY_SECONDS,
)
from .graph import CityGraph, haversine_distance_meters
from .algorithms import (
    dijkstra,
    astar,
    yen_k_shortest_paths,
    penalty_based_alternatives,
    compute_minimum_effective_cost_per_meter,
)
from .city_data import build_cyber_city_network, get_sample_emergency_units
from .emergency import (
    rank_emergency_resources,
    create_emergency_corridor,
    plan_traffic_diversion,
    simulate_unit_movement_timeline,
    map_incident_to_required_services,
)
from .engine import UrbanFlowRoutingEngine
from .service import RoutingService

__all__ = [
    "Node",
    "Edge",
    "NodeType",
    "SignalState",
    "EmergencyUnitType",
    "UnitStatus",
    "VehicleClass",
    "RouteContext",
    "RoutePath",
    "RouteResult",
    "EmergencyUnit",
    "ResourceRecommendation",
    "EmergencyCorridor",
    "TrafficDiversionPlan",
    "finite_or_none",
    "SIREN_SPEEDUP",
    "CORRIDOR_FACTOR",
    "MAX_COMBINED_SPEEDUP",
    "DEFAULT_HOLD_DELAY_SECONDS",
    "CityGraph",
    "haversine_distance_meters",
    "dijkstra",
    "astar",
    "yen_k_shortest_paths",
    "penalty_based_alternatives",
    "compute_minimum_effective_cost_per_meter",
    "build_cyber_city_network",
    "get_sample_emergency_units",
    "rank_emergency_resources",
    "create_emergency_corridor",
    "plan_traffic_diversion",
    "simulate_unit_movement_timeline",
    "map_incident_to_required_services",
    "UrbanFlowRoutingEngine",
    "RoutingService",
]
