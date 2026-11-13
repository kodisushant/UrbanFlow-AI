from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.schemas.incident import (
    IncidentRecord,
    IncidentDetectionPayload,
    IncidentVerificationRequest,
)
from app.services.incident_service import incident_service
from app.agents.coordinator import workflow_coordinator

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentResolutionRequest(BaseModel):
    operator_id: str = Field(default="OP_COMMAND_01", min_length=1)
    notes: Optional[str] = Field(default="Incident resolved and scene cleared by operator.")


@router.post("/detection", response_model=IncidentRecord, status_code=status.HTTP_201_CREATED)
async def ingest_detection(payload: IncidentDetectionPayload) -> IncidentRecord:
    """
    Member 2 Computer Vision Ingestion Endpoint.
    Receives candidate incident detection from CCTV vision pipeline or simulated trigger.
    """
    return workflow_coordinator.handle_detection(payload)


@router.get("", response_model=List[IncidentRecord])
@router.get("/", response_model=List[IncidentRecord], include_in_schema=False)
async def list_incidents() -> List[IncidentRecord]:
    """Retrieve all logged incident records."""
    return incident_service.get_all()


@router.get("/{incident_id}", response_model=IncidentRecord)
async def get_incident(incident_id: str) -> IncidentRecord:
    """Retrieve details of a specific incident."""
    incident = incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INCIDENT_NOT_FOUND", "message": f"Incident '{incident_id}' not found."}
        )
    return incident


@router.post("/{incident_id}/verify", response_model=IncidentRecord)
async def verify_incident(incident_id: str, payload: IncidentVerificationRequest) -> IncidentRecord:
    """
    Human-in-the-Loop Operator Verification Endpoint.
    Transitions incident from 'candidate' to 'verified' or 'resolved' (if rejected).
    """
    try:
        return workflow_coordinator.handle_verification(incident_id, payload)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INCIDENT_NOT_FOUND", "message": f"Incident '{incident_id}' not found."}
        )


@router.post("/{incident_id}/dispatch", response_model=IncidentRecord)
async def dispatch_incident(incident_id: str) -> IncidentRecord:
    """
    Trigger dispatch and emergency routing for a verified incident.
    Enforces strict safety: unverified or rejected incidents cannot be dispatched.
    """
    try:
        workflow_coordinator.execute_dispatch(incident_id)
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found after dispatch.")
        return incident
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNVERIFIED_DISPATCH_FORBIDDEN", "message": str(ve)}
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INCIDENT_NOT_FOUND", "message": f"Incident '{incident_id}' not found."}
        )


@router.post("/{incident_id}/resolve", response_model=IncidentRecord)
async def resolve_incident(
    incident_id: str,
    payload: Optional[IncidentResolutionRequest] = None
) -> IncidentRecord:
    """
    Operator Incident Resolution Endpoint.
    Marks an incident as resolved, removes road closures, resets corridors, and returns units.
    """
    req = payload or IncidentResolutionRequest()
    try:
        return workflow_coordinator.handle_resolution(
            incident_id=incident_id,
            operator_id=req.operator_id,
            notes=req.notes or ""
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INCIDENT_NOT_FOUND", "message": f"Incident '{incident_id}' not found."}
        )
