from fastapi import APIRouter
from app.schemas.orchestration import OrchestrationState, ScenarioRunRequest
from app.agents.coordinator import workflow_coordinator

router = APIRouter(prefix="/orchestration", tags=["Multi-Agent Orchestrator"])


@router.get("/state", response_model=OrchestrationState)
async def get_orchestration_state() -> OrchestrationState:
    """
    Member 5 Command Dashboard Status Endpoint.
    Retrieves current multi-agent workflow state, active incident, active routes, and agent decision log.
    """
    return workflow_coordinator.get_state()


@router.post("/run-scenario", response_model=OrchestrationState)
async def trigger_demo_scenario(req: ScenarioRunRequest) -> OrchestrationState:
    """
    One-Click Hackathon Demonstration Trigger.
    Executes the complete 8-step pipeline:
    Observe -> Detect -> Verify -> Classify -> Coordinate -> Optimize -> Divert -> Explain.
    """
    return workflow_coordinator.run_full_scenario(req)

