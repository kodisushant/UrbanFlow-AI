import unittest
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.incident import IncidentStatus
from app.schemas.route import RouteStatus, SimulationStatus


class TestUrbanFlowBackend(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Reset state before each test
        self.client.post("/api/v1/simulation/reset")

    def test_health_and_root(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

        root_res = self.client.get("/")
        self.assertEqual(root_res.status_code, 200)
        self.assertIn("documentation", root_res.json())

    def test_city_graph_and_simulation(self):
        res = self.client.get("/api/v1/simulation/city-graph")
        self.assertEqual(res.status_code, 200)
        graph = res.json()
        self.assertEqual(len(graph["nodes"]), 20)
        self.assertGreater(len(graph["edges"]), 20)

        reset_res = self.client.post("/api/v1/simulation/reset")
        self.assertEqual(reset_res.status_code, 200)
        self.assertEqual(reset_res.json()["status"], "success")

    def test_incident_lifecycle_and_verification(self):
        """
        Test user requirements:
        1. Incident lifecycle: candidate -> verified -> response_recommended -> simulated_dispatch -> resolved
        2. Verification request body: verified, operator_id, notes
        """
        # Step 1: Member 2 Detection Ingestion -> Candidate
        detection_payload = {
            "camera_id": "CCTV_TEST_01",
            "candidate_type": "possible_collision",
            "confidence": 0.85,
            "location_node": "NODE-07",
            "affected_road_id": "ROAD-04",
            "evidence_image_url": "/static/evidence/cam01.jpg",
            "observed_vehicles": [
                {"vehicle_class": "car", "bbox": [10, 20, 100, 120], "speed_kmph": 0.0, "is_stopped": True}
            ],
            "is_simulated": True
        }
        create_res = self.client.post("/api/v1/incidents/detection", json=detection_payload)
        self.assertEqual(create_res.status_code, 201)
        inc_data = create_res.json()
        inc_id = inc_data["incident_id"]
        self.assertEqual(inc_data["status"], IncidentStatus.CANDIDATE.value)
        self.assertEqual(inc_data["location_node"], "NODE-07")

        # Step 2: Verification with request body (verified, operator_id, notes)
        verify_payload = {
            "verified": True,
            "operator_id": "OP_AGENT_42",
            "notes": "Confirmed rear-end collision from CCTV feed."
        }
        verify_res = self.client.post(f"/api/v1/incidents/{inc_id}/verify", json=verify_payload)
        self.assertEqual(verify_res.status_code, 200)
        verified_data = verify_res.json()
        
        # Verify status reached response_recommended via coordinator
        self.assertIn(
            verified_data["status"],
            [IncidentStatus.VERIFIED.value, IncidentStatus.RESPONSE_RECOMMENDED.value]
        )
        self.assertTrue(verified_data["verification_info"]["verified"])
        self.assertEqual(verified_data["verification_info"]["operator_id"], "OP_AGENT_42")
        self.assertEqual(verified_data["verification_info"]["notes"], "Confirmed rear-end collision from CCTV feed.")

        # Step 3: Simulated dispatch
        dispatch_res = self.client.post(f"/api/v1/incidents/{inc_id}/dispatch")
        self.assertEqual(dispatch_res.status_code, 200)
        dispatched_data = dispatch_res.json()
        self.assertEqual(dispatched_data["status"], IncidentStatus.SIMULATED_DISPATCH.value)
        self.assertGreater(len(dispatched_data["assigned_unit_ids"]), 0)

    def test_extended_routing_response(self):
        """
        Test user requirement:
        Extend the routing response to include unit position, ETA, route status,
        avoided roads, signal-priority nodes, and simulation status.
        """
        route_req = {
            "origin_node": "NODE-02",
            "destination_node": "NODE-07",
            "unit_id": "AMB-01",
            "avoid_road_ids": ["ROAD-04"],
            "algorithm": "astar"
        }
        res = self.client.post("/api/v1/routing/calculate", json=route_req)
        self.assertEqual(res.status_code, 200)
        route_data = res.json()

        # Check required extended fields
        self.assertIn("unit_current_position", route_data)
        self.assertEqual(route_data["unit_current_position"]["node"], "NODE-02")
        self.assertIn("latitude", route_data["unit_current_position"])
        self.assertIn("longitude", route_data["unit_current_position"])
        
        self.assertIn("eta_seconds", route_data)
        self.assertGreater(route_data["eta_seconds"], 0)

        self.assertIn("route_status", route_data)
        self.assertEqual(route_data["route_status"], RouteStatus.CALCULATED.value)

        self.assertIn("avoided_roads", route_data)
        self.assertIn("ROAD-04", route_data["avoided_roads"])

        self.assertIn("signal_priority_nodes", route_data)
        self.assertGreater(len(route_data["signal_priority_nodes"]), 0)

        self.assertIn("simulation_status", route_data)
        self.assertEqual(route_data["simulation_status"], SimulationStatus.IDLE.value)

        self.assertIn("primary_route", route_data)
        self.assertGreaterEqual(len(route_data["primary_route"]["node_sequence"]), 2)
        self.assertIn("explanation", route_data)

    def test_traffic_ingestion_and_forecast(self):
        obs_payload = {
            "road_id": "ROAD-03",
            "vehicle_count": 52,
            "average_speed_kmph": 11.2,
            "source": "cctv_simulation",
            "is_simulated": True
        }
        res = self.client.post("/api/v1/traffic/observations", json=obs_payload)
        self.assertEqual(res.status_code, 201)
        fc = res.json()
        self.assertEqual(fc["road_id"], "ROAD-03")
        self.assertEqual(fc["current_congestion_level"], "severe")
        self.assertGreater(fc["congestion_weight_multiplier"], 1.0)

        # Query forecast
        fc_res = self.client.get("/api/v1/traffic/forecast/ROAD-03")
        self.assertEqual(fc_res.status_code, 200)
        self.assertEqual(fc_res.json()["current_congestion_level"], "severe")

    def test_emergency_resources_registry(self):
        res = self.client.get("/api/v1/resources/")
        self.assertEqual(res.status_code, 200)
        units = res.json()
        self.assertGreaterEqual(len(units), 5)

        # Get specific unit
        u_res = self.client.get("/api/v1/resources/AMB-01")
        self.assertEqual(u_res.status_code, 200)
        self.assertEqual(u_res.json()["unit_id"], "AMB-01")

    def test_one_click_end_to_end_scenario(self):
        """
        Test complete 8-step pipeline execution via /api/v1/orchestration/run-scenario.
        """
        run_payload = {
            "scenario_name": "junction_4_collision",
            "auto_verify": True,
            "operator_id": "DISPATCH_SUPERVISOR_01",
            "operator_notes": "Live test verification."
        }
        res = self.client.post("/api/v1/orchestration/run-scenario", json=run_payload)
        self.assertEqual(res.status_code, 200)
        state = res.json()

        self.assertEqual(state["status"], IncidentStatus.SIMULATED_DISPATCH.value)
        self.assertIsNotNone(state["active_incident"])
        self.assertGreater(len(state["dispatched_units"]), 0)
        self.assertGreater(len(state["active_routes"]), 0)
        self.assertGreater(len(state["signal_priority_nodes"]), 0)
        self.assertGreaterEqual(len(state["agent_log"]), 4)

        # Check that agent actions logged properly
        agent_names = [a["agent_name"] for a in state["agent_log"]]
        self.assertIn("IncidentAgent", agent_names)
        self.assertIn("TrafficAgent", agent_names)
        self.assertIn("EmergencyCoordinationAgent", agent_names)
        self.assertIn("RouteOptimizationAgent", agent_names)
        self.assertIn("Coordinator", agent_names)


if __name__ == "__main__":
    unittest.main()
