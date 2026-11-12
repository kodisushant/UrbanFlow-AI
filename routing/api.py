"""
UrbanFlow AI - FastAPI APIRouter for Member 1 Backend Integration
Member 4: Road Network, Emergency Routing & Traffic Diversion

Mount in Member 1's main FastAPI app:
    from routing.api import router as routing_router
    app.include_router(routing_router)
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from .service import RoutingService

try:
    from fastapi import APIRouter, HTTPException, Query, Path
    from .schemas import (
        RouteRequestV1,
        EmergencyDispatchRequestV1,
        RoadClosureRequestV1,
        TrafficUpdateRequestV1,
        DiversionRequestV1,
        SimulateMovementRequestV1,
    )

    router = APIRouter(prefix="/routing", tags=["routing"])
    _service = RoutingService()

    @router.post("/route", summary="Compute primary and alternative routes")
    def post_route(req: RouteRequestV1) -> Dict[str, Any]:
        try:
            return _service.compute_route(
                origin_node=req.origin_node,
                destination_node=req.destination_node,
                algorithm=req.algorithm,
                num_alternatives=req.num_alternatives,
                is_emergency=req.is_emergency,
                unit_id=req.unit_id,
                incident_id=req.incident_id,
                excluded_roads=req.excluded_roads,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/emergency/dispatch", summary="Dispatch emergency unit & establish green corridor")
    def post_dispatch_emergency(req: EmergencyDispatchRequestV1) -> Dict[str, Any]:
        try:
            return _service.dispatch_emergency(
                corridor_id=req.corridor_id,
                unit_id=req.unit_id,
                incident_id=req.incident_id,
                target_node=req.target_node,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/closures", summary="Close road segment(s) and compute diversion")
    def post_closures(req: RoadClosureRequestV1) -> Dict[str, Any]:
        try:
            return _service.close_road(
                road_id=req.road_id,
                reason=req.reason,
                direction=req.direction,
                incident_id=req.incident_id,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/closures/{road_id}", summary="Reopen road segment(s)")
    def delete_closure(
        road_id: str = Path(..., description="Road ID to reopen"),
        direction: str = Query("both", description="'forward' or 'both'"),
    ) -> Dict[str, Any]:
        try:
            return _service.reopen_road(road_id=road_id, direction=direction)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/traffic", summary="Apply live/forecast traffic observations")
    def post_traffic(req: TrafficUpdateRequestV1) -> Dict[str, Any]:
        obs = [item.dict() if hasattr(item, "dict") else item for item in req.observations]
        return _service.update_traffic(observations=obs)

    @router.post("/diversion", summary="Calculate civilian traffic diversion plan")
    def post_diversion(req: DiversionRequestV1) -> Dict[str, Any]:
        try:
            return _service.compute_diversion(
                incident_id=req.incident_id,
                blocked_road_id=req.blocked_road_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/simulate", summary="Simulate emergency vehicle movement timeline")
    def post_simulate(req: SimulateMovementRequestV1) -> Dict[str, Any]:
        try:
            return _service.simulate_movement(
                unit_id=req.unit_id,
                destination_node=req.destination_node,
                time_step_seconds=req.time_step_seconds,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/graph", summary="Get city road network GeoJSON for Mapbox/Leaflet")
    def get_graph() -> Dict[str, Any]:
        return _service.get_graph_geojson()

    HAS_FASTAPI = True

except ImportError:
    router = None  # type: ignore
    HAS_FASTAPI = False

    def get_api_router() -> Any:
        raise ImportError("FastAPI is not installed. Install with 'pip install fastapi' to use the APIRouter.")

