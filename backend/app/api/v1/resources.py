from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.schemas.resource import EmergencyUnit, ResourceStatus
from app.services.resource_service import resource_service

router = APIRouter(prefix="/resources", tags=["Emergency Resources"])


class UnitStatusUpdate(BaseModel):
    status: ResourceStatus


@router.get("/", response_model=List[EmergencyUnit])
async def list_emergency_units() -> List[EmergencyUnit]:
    """Retrieve all emergency response units and their real-time status."""
    return resource_service.get_all_units()


@router.get("/{unit_id}", response_model=EmergencyUnit)
async def get_unit(unit_id: str) -> EmergencyUnit:
    """Retrieve details and location of a specific emergency unit."""
    unit = resource_service.get_unit(unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "UNIT_NOT_FOUND", "message": f"Emergency unit '{unit_id}' not found."}
        )
    return unit


@router.patch("/{unit_id}/status", response_model=EmergencyUnit)
async def update_unit_status(unit_id: str, payload: UnitStatusUpdate) -> EmergencyUnit:
    """Update status of an emergency unit."""
    unit = resource_service.update_unit_status(unit_id, payload.status)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "UNIT_NOT_FOUND", "message": f"Emergency unit '{unit_id}' not found."}
        )
    return unit

