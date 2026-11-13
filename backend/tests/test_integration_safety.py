import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents.coordinator import workflow_coordinator

client = TestClient(app)


def setup_function():
    workflow_coordinator.reset_state()


def test_safety_unverified_dispatch_forbidden():
    """Safety requirement: Unverified candidate incident must NEVER trigger dispatch."""
    # 1. Trigger candidate detection
    det_resp = client.post(
        "/api/v1/simulation/detect-candidate",
        json={"location_node": "INT-03", "candidate_type": "possible_collision", "confidence": 0.85}
    )
    assert det_resp.status_code == 201
    inc_data = det_resp.json()
    inc_id = inc_data["incident_id"]
    assert inc_data["status"] == "candidate"

    # 2. Attempt dispatch directly while unverified
    disp_resp = client.post(f"/api/v1/incidents/{inc_id}/dispatch")
    assert disp_resp.status_code == 400
    assert "UNVERIFIED_DISPATCH_FORBIDDEN" in disp_resp.json()["detail"]["code"]


def test_safety_rejected_incident_cannot_dispatch():
    """Safety requirement: Operator-rejected incident must NEVER trigger dispatch."""
    # 1. Trigger candidate detection
    det_resp = client.post(
        "/api/v1/simulation/detect-candidate",
        json={"location_node": "INT-03", "candidate_type": "stationary_vehicle", "confidence": 0.50}
    )
    inc_id = det_resp.json()["incident_id"]

    # 2. Reject as false alarm
    rej_resp = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        json={"verified": False, "operator_id": "OP_TEST", "notes": "Stationary vehicle at red light, not an accident."}
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "resolved"

    # 3. Attempt dispatch on rejected incident
    disp_resp = client.post(f"/api/v1/incidents/{inc_id}/dispatch")
    assert disp_resp.status_code == 400
    assert "UNVERIFIED_DISPATCH_FORBIDDEN" in disp_resp.json()["detail"]["code"]


def test_full_workflow_observe_to_resolve():
    """Test full workflow: Observe -> Detect -> Verify -> Classify -> Coordinate -> Optimize -> Divert -> Resolve."""
    # 1. Get city graph
    graph_resp = client.get("/api/v1/simulation/city-graph")
    assert graph_resp.status_code == 200
    assert len(graph_resp.json()["nodes"]) == 20

    # 2. Detect candidate incident
    det_resp = client.post(
        "/api/v1/simulation/detect-candidate",
        json={"location_node": "INT-03", "road_id": "ROAD-03A", "candidate_type": "possible_collision", "confidence": 0.88}
    )
    assert det_resp.status_code == 201
    inc_id = det_resp.json()["incident_id"]

    # 3. Operator verifies
    ver_resp = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        json={"verified": True, "operator_id": "OP_LEAD_01", "notes": "CCTV confirmed 2-car collision."}
    )
    assert ver_resp.status_code == 200
    assert ver_resp.json()["status"] in ["verified", "response_recommended"]

    # 4. Operator dispatches
    disp_resp = client.post(f"/api/v1/incidents/{inc_id}/dispatch")
    assert disp_resp.status_code == 200
    assert disp_resp.json()["status"] == "simulated_dispatch"

    # 5. Check orchestration state
    state_resp = client.get("/api/v1/orchestration/state")
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["status"] == "simulated_dispatch"
    assert len(state["active_routes"]) >= 1
    assert state["signal_priority_corridor"]["active"] is True

    # 6. Operator resolves incident
    res_resp = client.post(
        f"/api/v1/incidents/{inc_id}/resolve",
        json={"operator_id": "OP_LEAD_01", "notes": "Scene cleared."}
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "resolved"

    # 7. Check state cleared
    state_after = client.get("/api/v1/orchestration/state").json()
    assert state_after["signal_priority_corridor"]["active"] is False
    assert len(state_after["active_routes"]) == 0
