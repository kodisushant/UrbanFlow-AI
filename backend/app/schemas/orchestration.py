from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.schemas.incident import IncidentRecord
from app.schemas.resource import EmergencyUnit
from app.schemas.route import RouteResult


class AgentActionRecord(BaseModel):
    agent_name: str
    role: str = "Decision Agent"
    action: str
    reasoning: str = ""
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    simulated: bool = True
    structured_output: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_agent_text(self):
        if not self.reasoning and self.summary:
            self.reasoning = self.summary
        elif not self.summary and self.reasoning:
            self.summary = self.reasoning
        return self

    model_config = ConfigDict(from_attributes=True)


class OrchestrationState(BaseModel):
    workflow_id: str = "WF-SCENARIO-DEMO-01"
    scenario_id: Optional[str] = "WF-SCENARIO-DEMO-01"
    stage: str = "idle"
    status: str = "idle"
    current_step: int = 0
    total_steps: int = 5
    active_incident: Optional[IncidentRecord] = None
    active_routes: List[RouteResult] = Field(default_factory=list)
    traffic_diversions: Dict[str, Any] = Field(
        default_factory=lambda: {"diverted_road_ids": [], "diversion_route": None}
    )
    signal_priority_corridor: Dict[str, Any] = Field(
        default_factory=lambda: {"corridor_nodes": [], "active": False}
    )
    signal_priority_nodes: List[str] = Field(default_factory=list)
    diverted_roads: List[str] = Field(default_factory=list)
    dispatched_units: List[EmergencyUnit] = Field(default_factory=list)
    agent_logs: List[AgentActionRecord] = Field(default_factory=list)
    agent_log: List[AgentActionRecord] = Field(default_factory=list)
    recommended_service: Optional[str] = None
    explanation: str = "System ready. Awaiting detection or scenario trigger."
    simulated: bool = True

    @model_validator(mode="after")
    def sync_aliases(self):
        if not self.scenario_id and self.workflow_id:
            self.scenario_id = self.workflow_id
        if not self.workflow_id and self.scenario_id:
            self.workflow_id = self.scenario_id
        if not self.status and self.stage:
            self.status = self.stage
        if not self.stage and self.status:
            self.stage = self.status
        if not self.agent_logs and self.agent_log:
            self.agent_logs = self.agent_log
        elif not self.agent_log and self.agent_logs:
            self.agent_log = self.agent_logs
        return self

    model_config = ConfigDict(from_attributes=True)


class ScenarioRunRequest(BaseModel):
    scenario_name: str = Field(default="Cyber City Emergency Response")
    auto_verify: bool = Field(default=True, description="Automatically trigger operator verification for 1-click demo")
    operator_id: str = Field(default="AUTO_DISPATCHER_01")
    operator_notes: Optional[str] = Field(default="Automated live verification for demonstration run.")
