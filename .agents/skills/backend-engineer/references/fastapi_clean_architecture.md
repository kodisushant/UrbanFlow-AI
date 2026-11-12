# FastAPI Clean Architecture & Implementation Patterns

This reference provides production-ready code templates for FastAPI development, following Pydantic v2 and modern async patterns.

---

## 1. Modular Router Template

```python
# app/api/v1/incidents.py
from fastapi import APIRouter, Depends, status, HTTPException
from typing import List
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    service: IncidentService = Depends()
) -> IncidentResponse:
    """Create a verified or candidate incident report."""
    incident = await service.register_incident(payload)
    return incident

@router.get("/", response_model=List[IncidentResponse])
async def list_active_incidents(
    service: IncidentService = Depends()
) -> List[IncidentResponse]:
    """Retrieve all active incidents awaiting resolution or dispatch."""
    return await service.get_active()
```

---

## 2. Pydantic v2 Schema Template

```python
# app/schemas/incident.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime

class IncidentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    incident_type: Literal["accident", "road_blockage", "debris", "congestion_spike"]
    location_node: str = Field(..., description="Graph intersection node ID")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from vision pipeline")

class IncidentCreate(IncidentBase):
    pass

class IncidentResponse(IncidentBase):
    id: str
    status: Literal["candidate", "verified", "dispatched", "cleared"] = "candidate"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## 3. Automated Endpoint Test Template

```python
# tests/test_incidents.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_and_fetch_incident():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create incident
        payload = {
            "title": "Stalled Vehicle at Junction 4",
            "incident_type": "accident",
            "location_node": "node_42",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "confidence": 0.88
        }
        res = await client.post("/api/v1/incidents/", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] is not None
        assert data["confidence"] == 0.88

        # Test validation error
        bad_payload = payload.copy()
        bad_payload["confidence"] = 2.5  # Invalid > 1.0
        bad_res = await client.post("/api/v1/incidents/", json=bad_payload)
        assert bad_res.status_code == 422
```

