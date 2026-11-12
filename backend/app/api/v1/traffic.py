from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.schemas.traffic import TrafficObservation, TrafficForecast
from app.services.traffic_service import traffic_service

router = APIRouter(prefix="/traffic", tags=["Traffic Intelligence"])


@router.post("/observations", response_model=TrafficForecast, status_code=status.HTTP_201_CREATED)
async def ingest_observation(obs: TrafficObservation) -> TrafficForecast:
    """
    Member 3 Traffic Observation Ingestion Endpoint.
    Ingests road segment observations and returns updated congestion and 15m/30m forecast.
    """
    return traffic_service.ingest_observation(obs)


@router.get("/forecast/{road_id}", response_model=TrafficForecast)
async def get_road_forecast(road_id: str) -> TrafficForecast:
    """Retrieve current congestion and 15–30 minute forecast for a specific road."""
    fc = traffic_service.get_forecast(road_id)
    if not fc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROAD_NOT_FOUND", "message": f"Road segment '{road_id}' not found in city grid."}
        )
    return fc


@router.get("/overview", response_model=List[Dict[str, Any]])
async def get_network_traffic_overview() -> List[Dict[str, Any]]:
    """Retrieve congestion overview across all road segments in the city."""
    return traffic_service.get_all_road_statuses()

