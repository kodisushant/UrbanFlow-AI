import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.schemas.incident import (
    IncidentDetectionPayload,
    IncidentVerificationRequest,
    IncidentStatus,
)
from app.schemas.traffic import TrafficObservation
from app.schemas.route import RouteRequest, RouteStatus
from app.api.v1.incidents import ingest_detection, verify_incident, dispatch_incident
from app.api.v1.traffic import ingest_observation
from app.api.v1.resources import list_emergency_units, get_unit
from app.api.v1.routing import calculate_route
from app.api.v1.simulation import get_city_graph, reset_simulation
from app.api.v1.orchestration import get_orchestration_state

async def run_checks():
    print("Checking reset_simulation...")
    reset_out = await reset_simulation()
    print("reset_simulation OK")

    print("Checking get_city_graph...")
    city_graph = await get_city_graph()
    print(f"get_city_graph OK: {len(city_graph.nodes)} nodes")

    print("Checking ingest_detection...")
    det_payload = IncidentDetectionPayload(
        camera_id="CCTV_API_TEST",
        candidate_type="possible_collision",
        confidence=0.86,
        location_node="INT-07",
        affected_road_id="ROAD-04A",
        is_simulated=True
    )
    inc = await ingest_detection(det_payload)
    print(f"ingest_detection OK: {inc.incident_id}")

    print("Checking verify_incident...")
    v_req = IncidentVerificationRequest(
        verified=True,
        operator_id="API_DISPATCHER",
        notes="API verification pass"
    )
    v_inc = await verify_incident(inc.incident_id, v_req)
    print(f"verify_incident OK: {v_inc.status}")

    print("Checking dispatch_incident...")
    d_inc = await dispatch_incident(inc.incident_id)
    print(f"dispatch_incident OK: {d_inc.status}")

    print("Checking list_emergency_units...")
    units = await list_emergency_units()
    print(f"list_emergency_units OK: {len(units)} units")

    print("Checking get_unit...")
    u = await get_unit("AMB-01")
    print(f"get_unit OK: {u.unit_id}")

    print("Checking calculate_route...")
    r_req = RouteRequest(
        origin_node="INT-04",
        destination_node="INT-07",
        unit_id="AMB-01",
        avoid_road_ids=["ROAD-04A"]
    )
    r_res = await calculate_route(r_req)
    print(f"calculate_route OK: {r_res.route_id}")

    print("Checking ingest_observation...")
    obs = TrafficObservation(road_id="ROAD-01A", vehicle_count=30, average_speed_kmph=35.0)
    fc = await ingest_observation(obs)
    print(f"ingest_observation OK: {fc.road_id}")

    print("Checking get_orchestration_state...")
    orch_state = await get_orchestration_state()
    print(f"get_orchestration_state OK: {orch_state.status}")

    print("ALL ASYNC CHECKS COMPLETED!")

if __name__ == "__main__":
    asyncio.run(run_checks())
