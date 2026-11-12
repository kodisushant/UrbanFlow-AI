from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ResourceType(str, Enum):
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    POLICE_CRUISER = "police_cruiser"


class ResourceStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    RETURNING = "returning"


class EmergencyUnit(BaseModel):
    unit_id: str = Field(..., description="Unique unit identifier e.g., AMB-01")
    name: str = Field(..., description="Display callsign e.g., Medic-1")
    unit_type: ResourceType
    status: ResourceStatus = ResourceStatus.AVAILABLE
    station_node: str = Field(..., description="Home station graph node ID")
    current_node: str = Field(..., description="Current graph node position")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    capabilities: List[str] = Field(default_factory=list)
    speed_kmph: float = Field(default=50.0, gt=0.0)
    assigned_incident_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

