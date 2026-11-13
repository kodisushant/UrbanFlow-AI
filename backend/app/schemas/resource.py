from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class EmergencyUnit(BaseModel):
    unit_id: str = Field(..., description="Unique unit identifier e.g., AMB-01")
    name: str = Field(default="Emergency Responder", description="Display callsign e.g., Medic One ALS")
    call_sign: Optional[str] = Field(default=None, description="Frontend alias for name")
    unit_type: str = Field(default="ambulance", description="ambulance | fire_engine | police_patrol")
    status: str = Field(default="available", description="available | stationed | dispatched | on_scene | returning")
    station_node: str = Field(..., description="Home station graph node ID e.g., INT-04")
    current_node: str = Field(..., description="Current graph node position e.g., INT-20")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    capabilities: List[str] = Field(default_factory=list)
    speed_kmph: float = Field(default=55.0, gt=0.0)
    eta_seconds: Optional[int] = None
    assigned_incident_id: Optional[str] = None
    route_geometry: List[List[float]] = Field(default_factory=list, description="Ordered [[lat, lon], ...] along route")
    dispatch_timestamp: Optional[float] = None
    total_route_distance_meters: Optional[float] = None
    total_route_duration_seconds: Optional[float] = None
    target_node: Optional[str] = None
    home_hospital_node: Optional[str] = None
    patient_count: int = 0
    phase_start_time: Optional[float] = None
    phase_duration_seconds: Optional[float] = None
    subphase_index: int = 0
    subphase_name: Optional[str] = None

    @model_validator(mode="after")
    def sync_names_and_types(self):
        if not self.call_sign and self.name:
            self.call_sign = self.name
        elif not self.name and self.call_sign:
            self.name = self.call_sign
        return self

    model_config = ConfigDict(from_attributes=True)


class ResourceType(str, Enum):
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_engine"
    FIRE_ENGINE = "fire_engine"
    POLICE_CRUISER = "police_patrol"
    POLICE_PATROL = "police_patrol"
    POLICE = "police_patrol"


class ResourceStatus(str, Enum):
    AVAILABLE = "available"
    STATIONED = "stationed"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    LOADING = "loading"
    TRANSPORTING = "transporting"
    AT_HOSPITAL = "at_hospital"
    RETURNING = "returning"
    MAINTENANCE = "maintenance"

