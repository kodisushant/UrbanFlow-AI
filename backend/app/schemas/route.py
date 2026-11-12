from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


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


class RoutePath(BaseModel):
    node_sequence: List[str] = Field(..., description="Ordered list of intersection node IDs")
    road_ids: List[str] = Field(..., description="Ordered list of traversed road segment IDs")
    estimated_travel_time_seconds: int = Field(..., ge=0)
    distance_meters: float = Field(..., ge=0.0)


class RouteRequest(BaseModel):
    origin_node: str = Field(..., description="Starting intersection node ID")
    destination_node: str = Field(..., description="Destination intersection node ID")
    unit_id: Optional[str] = Field(None, description="Optional emergency unit ID")
    incident_id: Optional[str] = Field(None, description="Associated incident ID")
    avoid_road_ids: List[str] = Field(default_factory=list, description="Road IDs to avoid (e.g. blockages)")
    algorithm: str = Field(default="astar", description="Routing algorithm: dijkstra or astar")


class RouteResult(BaseModel):
    route_id: str
    unit_id: Optional[str] = None
    incident_id: Optional[str] = None
    unit_current_position: Dict[str, Any] = Field(
        ...,
        description="Current coordinate/node of unit: {'node': str, 'latitude': float, 'longitude': float}"
    )
    destination_node: str
    eta_seconds: int = Field(..., ge=0, description="Estimated time of arrival in seconds")
    route_status: RouteStatus = RouteStatus.CALCULATED
    simulation_status: SimulationStatus = SimulationStatus.IDLE
    algorithm: str = "astar"
    primary_route: RoutePath
    alternative_routes: List[RoutePath] = Field(default_factory=list)
    avoided_roads: List[str] = Field(default_factory=list, description="Road segments avoided due to incidents/closures")
    signal_priority_nodes: List[str] = Field(default_factory=list, description="Nodes flagged for green signal corridor")
    diverted_roads: List[str] = Field(default_factory=list, description="Roads from which regular traffic is diverted")
    explanation: str = Field(..., description="Human-readable rationale for route selection")

    model_config = ConfigDict(from_attributes=True)

