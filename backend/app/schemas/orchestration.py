from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.incident import IncidentRecord
from app.schemas.resource import EmergencyUnit
from app.schemas.route import RouteResult


class AgentActionRecord(BaseModel):
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    summary: str
    structured_output: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class OrchestrationState(BaseModel):
    scenario_id: str
    status: str = Field(
        default="idle",
        description="idle | incident_detected | verified | response_recommended | simulated_dispatch | resolved"
    )
    current_step: int = 0
    total_steps: int = 5
    active_incident: Optional[IncidentRecord] = None
    recommended_service: Optional[str] = None
    dispatched_units: List[EmergencyUnit] = Field(default_factory=list)
    active_routes: List[RouteResult] = Field(default_factory=list)
    signal_priority_nodes: List[str] = Field(default_factory=list)
    diverted_roads: List[str] = Field(default_factory=list)
    agent_log: List[AgentActionRecord] = Field(default_factory=list)
    explanation: str = Field(default="System ready. Awaiting detection or scenario trigger.")

    model_config = ConfigDict(from_attributes=True)


class ScenarioRunRequest(BaseModel):
    scenario_name: str = Field(default="junction_4_collision")
    auto_verify: bool = Field(default=True, description="Automatically trigger operator verification for 1-click demo")
    operator_id: str = Field(default="AUTO_DISPATCHER_01")
    operator_notes: Optional[str] = Field(default="Automated live verification for demonstration run.")
