from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class RouteStatus(str, Enum):
    CALCULATED = "calculated"
    ACTIVE_DISPATCH = "active_dispatch"
    RE_ROUTED = "re_routed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SimulationStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class RoutePath(BaseModel):
    node_sequence: List[str] = Field(default_factory=list, description="Ordered list of intersection node IDs")
    road_ids: List[str] = Field(default_factory=list, description="Ordered list of traversed road segment IDs")
    estimated_travel_time_seconds: int = Field(default=0, ge=0)
    distance_meters: float = Field(default=0.0, ge=0.0)
    coordinates: List[Dict[str, float]] = Field(default_factory=list)


class RouteRequest(BaseModel):
    origin_node: str = Field(..., description="Starting intersection node ID")
    destination_node: str = Field(..., description="Destination intersection node ID")
    unit_id: Optional[str] = Field(None, description="Optional emergency unit ID")
    incident_id: Optional[str] = Field(None, description="Associated incident ID")
    avoid_road_ids: List[str] = Field(default_factory=list, description="Road IDs to avoid (e.g. blockages)")
    algorithm: str = Field(default="astar", description="Routing algorithm: dijkstra or astar")


class RouteResult(BaseModel):
    route_id: str
    origin_node: str = "INT-04"
    destination_node: str = "INT-03"
    algorithm: str = "astar"
    unit_id: Optional[str] = None
    unit_type: Optional[str] = None
    route_kind: str = "emergency_corridor"
    incident_id: Optional[str] = None
    road_ids: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    total_distance_meters: float = 0.0
    estimated_travel_time_seconds: int = 0
    estimated_travel_time_minutes: float = 0.0
    coordinates: List[Dict[str, float]] = Field(default_factory=list)
    unit_current_position: Dict[str, Any] = Field(default_factory=dict)
    eta_seconds: int = 0
    route_status: str = "calculated"
    simulation_status: str = "idle"
    primary_route: Optional[RoutePath] = None
    alternative_routes: List[Any] = Field(default_factory=list)
    avoided_roads: List[str] = Field(default_factory=list)
    signal_priority_nodes: List[str] = Field(default_factory=list)
    diverted_roads: List[str] = Field(default_factory=list)
    explanation: str = Field(default="Optimal emergency route selected.")


class SegmentCongestionInfo(BaseModel):
    road_id: str
    name: str
    source_node: str
    target_node: str
    length_meters: float
    speed_limit_kmph: float
    congestion_level: str
    congestion_multiplier: float
    is_blocked: bool
    segment_travel_time_seconds: float


class FindPathMode(str, Enum):
    OPTIMISED = "optimised"
    BASELINE = "baseline"


class FindPathRequest(BaseModel):
    from_node: str = Field(..., description="Origin node ID")
    to_node: str = Field(..., description="Destination node ID")
    mode: str = Field(default="optimised", description="'optimised' or 'baseline'")
    algorithm: str = Field(default="astar", description="'astar' or 'dijkstra' (for optimised mode)")


class FindPathResult(BaseModel):
    mode: str
    algorithm: str
    from_node: str
    to_node: str
    node_sequence: List[str] = Field(default_factory=list)
    road_ids: List[str] = Field(default_factory=list)
    geometry: List[List[float]] = Field(default_factory=list, description="Ordered [[lat, lon], ...] coordinates along route")
    total_distance_km: float = 0.0
    total_distance_meters: float = 0.0
    estimated_travel_time_seconds: float = 0.0
    estimated_travel_time_minutes: float = 0.0
    nodes_explored: int = 0
    compute_ms: float = 0.0
    congested_segments_count: int = 0
    blocked_roads_count: int = 0
    has_blocked_segments: bool = False
    detour_penalty_applied_seconds: float = 0.0
    segments: List[SegmentCongestionInfo] = Field(default_factory=list)
    is_reachable: bool = True
    message: Optional[str] = None


class ComparePathsRequest(BaseModel):
    from_node: str = Field(..., description="Origin node ID")
    to_node: str = Field(..., description="Destination node ID")
    algorithm: str = Field(default="astar", description="'astar' or 'dijkstra' for optimised path")


class ComparePathsResult(BaseModel):
    from_node: str
    to_node: str
    is_reachable: bool = True
    routes_match: bool = False
    summary: str
    time_saved_minutes: float = 0.0
    time_saved_percent: float = 0.0
    distance_diff_km: float = 0.0
    optimised: FindPathResult
    baseline: FindPathResult


class RandomizeTrafficRequest(BaseModel):
    seed: Optional[int] = Field(None, description="Optional seed for deterministic traffic generation")
    num_blocked_roads: Optional[int] = Field(None, ge=1, le=10, description="Number of roads to block (default 2-4)")


class RandomizeTrafficResult(BaseModel):
    status: str
    seed_used: int
    blocked_roads: List[str]
    congested_roads_count: int

    @model_validator(mode="after")
    def populate_flattened_fields(self):
        if self.primary_route:
            if not self.node_ids and self.primary_route.node_sequence:
                self.node_ids = self.primary_route.node_sequence
            if not self.road_ids and self.primary_route.road_ids:
                self.road_ids = self.primary_route.road_ids
            if not self.total_distance_meters and self.primary_route.distance_meters:
                self.total_distance_meters = self.primary_route.distance_meters
            if not self.estimated_travel_time_seconds and self.primary_route.estimated_travel_time_seconds:
                self.estimated_travel_time_seconds = self.primary_route.estimated_travel_time_seconds
            if not self.coordinates and getattr(self.primary_route, "coordinates", None):
                self.coordinates = self.primary_route.coordinates
        if not self.eta_seconds and self.estimated_travel_time_seconds:
            self.eta_seconds = self.estimated_travel_time_seconds
        if not self.estimated_travel_time_minutes and self.estimated_travel_time_seconds:
            self.estimated_travel_time_minutes = round(self.estimated_travel_time_seconds / 60.0, 1)
        if not self.origin_node and self.node_ids:
            self.origin_node = self.node_ids[0]
        if not self.destination_node and self.node_ids:
            self.destination_node = self.node_ids[-1]
        return self

    model_config = ConfigDict(from_attributes=True)
