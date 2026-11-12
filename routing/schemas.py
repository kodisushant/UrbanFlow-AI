"""
UrbanFlow AI - Proposed v1 Pydantic Schemas for Member 1 FastAPI Backend
Member 4: Road Network, Emergency Routing & Traffic Diversion

Versioned as v1. Uses Pydantic v2 if installed; degrades gracefully if pydantic is not installed.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

try:
    from pydantic import BaseModel, Field

    class RouteRequestV1(BaseModel):
        origin_node: str = Field(..., description="Starting intersection node ID (e.g. 'INT-04')")
        destination_node: str = Field(..., description="Target intersection node ID (e.g. 'INT-01')")
        algorithm: str = Field("astar", description="Routing algorithm: 'astar' or 'dijkstra'")
        num_alternatives: int = Field(2, ge=0, le=5, description="Number of alternative routes to compute")
        is_emergency: bool = Field(false, description="Enable emergency sirens and green corridor discounts")
        unit_id: Optional[str] = Field(None, description="Optional dispatched emergency unit ID")
        incident_id: Optional[str] = Field(None, description="Optional associated incident ID")
        excluded_roads: Optional[List[str]] = Field(None, description="List of road IDs to exclude")

    class CoordinatePointV1(BaseModel):
        latitude: float
        longitude: float

    class AlternativeRouteV1(BaseModel):
        node_ids: List[str]
        road_ids: List[str]
        total_distance_meters: float
        estimated_travel_time_seconds: Optional[float]
        estimated_travel_time_minutes: Optional[float]
        coordinates: List[CoordinatePointV1]
        summary: str
        overlap_ratio: float

    class RouteResponseV1(BaseModel):
        origin_node: str
        destination_node: str
        algorithm: str
        unit_id: Optional[str] = None
        incident_id: Optional[str] = None
        is_emergency_route: bool
        road_ids: List[str]
        node_ids: List[str]
        estimated_travel_time_seconds: Optional[float]
        estimated_travel_time_minutes: Optional[float]
        total_distance_meters: float
        coordinates: List[CoordinatePointV1]
        blocked_roads_avoided: List[str]
        congestion_avoided: bool
        alternative_routes: List[AlternativeRouteV1]
        explanation: str
        simulated: bool = True

    class EmergencyDispatchRequestV1(BaseModel):
        corridor_id: str = Field(..., description="Unique ID for corridor (e.g. 'CORR-01')")
        unit_id: str = Field(..., description="ID of unit to dispatch (e.g. 'AMB-01')")
        incident_id: str = Field(..., description="Associated incident ID")
        target_node: Optional[str] = Field("INT-03", description="Target intersection node ID")

    class RoadClosureRequestV1(BaseModel):
        road_id: str = Field(..., description="Road segment ID to close (e.g. 'ROAD-03A')")
        reason: str = Field("accident_blockage", description="Reason for closure")
        direction: str = Field("both", description="'forward' or 'both'")
        incident_id: Optional[str] = Field(None, description="Associated incident ID")

    class RoadClosureResponseV1(BaseModel):
        status: str
        closed_roads: List[str]
        incident_id: str
        diversion_plan: Optional[Dict[str, Any]] = None
        simulated: bool = True

    class TrafficObservationItemV1(BaseModel):
        road_id: str
        congestion_level: Optional[str] = None
        congestion_factor: Optional[float] = None
        estimated_speed_kmph: Optional[float] = None

    class TrafficUpdateRequestV1(BaseModel):
        observations: List[TrafficObservationItemV1]

    class DiversionRequestV1(BaseModel):
        incident_id: str
        blocked_road_id: str

    class SimulateMovementRequestV1(BaseModel):
        unit_id: str
        destination_node: str = "INT-03"
        time_step_seconds: float = 15.0

    HAS_PYDANTIC = True

except ImportError:
    # Graceful fallback if pydantic is not installed
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs: Any):
            self.__dict__.update(kwargs)
        def dict(self) -> Dict[str, Any]:
            return self.__dict__

    RouteRequestV1 = BaseModel  # type: ignore
    RouteResponseV1 = BaseModel  # type: ignore
    EmergencyDispatchRequestV1 = BaseModel  # type: ignore
    RoadClosureRequestV1 = BaseModel  # type: ignore
    RoadClosureResponseV1 = BaseModel  # type: ignore
    TrafficUpdateRequestV1 = BaseModel  # type: ignore
    DiversionRequestV1 = BaseModel  # type: ignore
    SimulateMovementRequestV1 = BaseModel  # type: ignore
    HAS_PYDANTIC = False

