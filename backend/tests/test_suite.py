import asyncio
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.city_graph_service import city_graph_service
from app.services.resource_service import resource_service
from app.services.incident_service import incident_service
from app.services.traffic_service import traffic_service
from app.agents.coordinator import workflow_coordinator
from app.agents.incident_agent import incident_agent
from app.agents.traffic_agent import traffic_agent
from app.agents.emergency_agent import emergency_agent
from app.agents.route_agent import route_agent

from app.schemas.incident import (
    IncidentDetectionPayload,
    IncidentVerificationRequest,
    IncidentStatus,
    ObservedVehicle,
)
from app.schemas.traffic import TrafficObservation, CongestionLevel
from app.schemas.resource import ResourceType, ResourceStatus
from app.schemas.route import RouteRequest, RouteStatus, SimulationStatus
from app.schemas.orchestration import ScenarioRunRequest

# API router handlers
from app.api.v1.incidents import ingest_detection, verify_incident, dispatch_incident, list_incidents, get_incident
from app.api.v1.traffic import ingest_observation, get_road_forecast, get_network_traffic_overview
from app.api.v1.resources import list_emergency_units, get_unit, update_unit_status, UnitStatusUpdate
from app.api.v1.routing import calculate_route, list_active_routes
from app.api.v1.simulation import get_city_graph, reset_simulation
from app.api.v1.orchestration import get_orchestration_state, trigger_demo_scenario


class TestUrbanFlowComprehensive(unittest.TestCase):

    def setUp(self):
        workflow_coordinator.reset_state()

    def test_01_city_graph_and_pathfinding(self):
        """Test CityGraphService nodes, edges, Dijkstra, and A*."""
        graph = city_graph_service.get_city_graph()
        self.assertEqual(len(graph.nodes), 20)
        self.assertGreater(len(graph.edges), 20)

        # Primary route from NODE-01 to NODE-15
        path_astar = city_graph_service.find_shortest_path("NODE-01", "NODE-15", algorithm="astar")
        self.assertIsNotNone(path_astar)
        self.assertIn(path_astar.node_sequence[0], ["NODE-01", "INT-01"])
        self.assertIn(path_astar.node_sequence[-1], ["NODE-15", "INT-15"])
        self.assertGreater(path_astar.estimated_travel_time_seconds, 0)
        self.assertGreater(path_astar.distance_meters, 0.0)

        # Dijkstra algorithm yields equivalent optimal travel cost
        path_dijkstra = city_graph_service.find_shortest_path("NODE-01", "NODE-15", algorithm="dijkstra")
        self.assertIsNotNone(path_dijkstra)
        self.assertEqual(path_dijkstra.estimated_travel_time_seconds, path_astar.estimated_travel_time_seconds)

        # Test road avoidance / closure
        avoid_first = {path_astar.road_ids[0]}
        alt_path = city_graph_service.find_shortest_path("NODE-01", "NODE-15", avoid_road_ids=avoid_first)
        self.assertIsNotNone(alt_path)
        self.assertNotIn(path_astar.road_ids[0], alt_path.road_ids)

    def test_02_resource_registry_and_matching(self):
        """Test Emergency Resource registry and deterministic allocation."""
        units = resource_service.get_all_units()
        self.assertGreaterEqual(len(units), 5)

        # Match closest ambulance to NODE-07
        best_amb = resource_service.find_best_unit("NODE-07", ResourceType.AMBULANCE)
        self.assertIsNotNone(best_amb)
        self.assertEqual(best_amb.unit_type, ResourceType.AMBULANCE)
        self.assertEqual(best_amb.status, ResourceStatus.AVAILABLE)

        # Match police
        best_police = resource_service.find_best_unit("NODE-07", ResourceType.POLICE_CRUISER)
        self.assertIsNotNone(best_police)
        self.assertEqual(best_police.unit_type, ResourceType.POLICE_CRUISER)

    def test_03_traffic_intelligence_and_forecasting(self):
        """Test TrafficService observation ingestion and deterministic forecasting."""
        obs = TrafficObservation(
            road_id="ROAD-02",
            vehicle_count=50,
            average_speed_kmph=14.0,
            source="sensor_array_2"
        )
        fc = traffic_service.ingest_observation(obs)
        self.assertEqual(fc.road_id, "ROAD-02")
        self.assertEqual(fc.current_congestion_level, CongestionLevel.HEAVY)
        self.assertGreater(fc.congestion_weight_multiplier, 1.0)
        self.assertIn("auto-regressive", fc.limitations_note)

        # Road overview
        overview = traffic_service.get_all_road_statuses()
        self.assertGreater(len(overview), 20)

    def test_04_incident_lifecycle_progression(self):
        """
        Verify user requirement 1 & 2:
        Lifecycle: candidate -> verified -> response_recommended -> simulated_dispatch -> resolved
        Verification request body: verified, operator_id, notes
        """
        # Step 1: Candidate
        detection = IncidentDetectionPayload(
            camera_id="CAM-SOUTH-12",
            candidate_type="possible_collision",
            confidence=0.87,
            location_node="NODE-12",
            affected_road_id="ROAD-15",
            observed_vehicles=[
                ObservedVehicle(vehicle_class="car", bbox=[20, 30, 80, 90], speed_kmph=0.0, is_stopped=True)
            ],
            is_simulated=True
        )
        inc = incident_service.create_candidate_incident(detection)
        self.assertEqual(inc.status, IncidentStatus.CANDIDATE)
        self.assertEqual(inc.location_node, "NODE-12")

        # Step 2: Operator Verification with request body
        v_req = IncidentVerificationRequest(
            verified=True,
            operator_id="DISPATCH_SUPERVISOR_99",
            notes="Vehicle fender-bender confirmed."
        )
        v_inc = incident_service.verify_incident(inc.incident_id, v_req)
        self.assertEqual(v_inc.status, IncidentStatus.VERIFIED)
        self.assertEqual(v_inc.verification_info.operator_id, "DISPATCH_SUPERVISOR_99")
        self.assertEqual(v_inc.verification_info.notes, "Vehicle fender-bender confirmed.")

        # Step 3: Response Recommended
        r_inc = incident_service.update_status(inc.incident_id, IncidentStatus.RESPONSE_RECOMMENDED)
        self.assertEqual(r_inc.status, IncidentStatus.RESPONSE_RECOMMENDED)

        # Step 4: Simulated Dispatch
        d_inc = incident_service.update_status(inc.incident_id, IncidentStatus.SIMULATED_DISPATCH)
        self.assertEqual(d_inc.status, IncidentStatus.SIMULATED_DISPATCH)

        # Step 5: Resolved
        res_inc = incident_service.update_status(inc.incident_id, IncidentStatus.RESOLVED)
        self.assertEqual(res_inc.status, IncidentStatus.RESOLVED)

    def test_05_extended_route_planning(self):
        """
        Verify user requirement 3:
        Routing response includes unit position, ETA, route status, avoided roads,
        signal-priority nodes, and simulation status.
        """
        unit = resource_service.get_unit("AMB-01")
        detection = IncidentDetectionPayload(
            camera_id="CAM-07",
            candidate_type="accident",
            confidence=0.9,
            location_node="NODE-07",
            affected_road_id="ROAD-04"
        )
        incident = incident_service.create_candidate_incident(detection)

        route_res = route_agent.plan_emergency_route(
            unit=unit,
            incident=incident,
            avoid_road_ids={"ROAD-04"},
            algorithm="astar"
        )
        self.assertIsNotNone(route_res)
        self.assertIn("node", route_res.unit_current_position)
        self.assertEqual(route_res.unit_current_position["node"], unit.current_node)
        self.assertGreater(route_res.eta_seconds, 0)
        self.assertEqual(route_res.route_status, RouteStatus.ACTIVE_DISPATCH)
        self.assertEqual(route_res.simulation_status, SimulationStatus.RUNNING)
        self.assertIn("ROAD-04", route_res.avoided_roads)
        self.assertGreater(len(route_res.signal_priority_nodes), 0)
        self.assertGreater(len(route_res.diverted_roads), 0)
        self.assertIn("ASTAR", route_res.explanation)

    def test_06_coordinator_full_scenario(self):
        """
        Verify user requirement 4 & 5:
        Modular agents coordinated by central orchestrator, executing the 8-step pipeline deterministically.
        """
        req = ScenarioRunRequest(
            scenario_name="main_collision_junction_4",
            auto_verify=True,
            operator_id="OP_LEAD_01",
            operator_notes="Scenario test verification"
        )
        state = workflow_coordinator.run_full_scenario(req)
        self.assertEqual(state.status, IncidentStatus.SIMULATED_DISPATCH.value)
        self.assertIsNotNone(state.active_incident)
        self.assertIn(state.active_incident.location_node, ["INT-03", "NODE-07", "INT-07"])
        self.assertGreater(len(state.dispatched_units), 0)
        self.assertGreater(len(state.active_routes), 0)
        self.assertGreater(len(state.signal_priority_nodes), 0)
        self.assertGreaterEqual(len(state.agent_log), 5)

        # Check agent log coverage
        logged_agents = {a.agent_name for a in state.agent_log}
        self.assertIn("VisionAgent", logged_agents)
        self.assertIn("IncidentAgent", logged_agents)
        self.assertIn("TrafficAgent", logged_agents)
        self.assertTrue("EmergencyAgent" in logged_agents or "EmergencyCoordinationAgent" in logged_agents)
        self.assertTrue("RouteAgent" in logged_agents or "RouteOptimizationAgent" in logged_agents)

    def test_07_api_v1_endpoints_async(self):
        """Test API v1 routers through async coroutine execution."""
        async def run_api_checks():
            # Simulation
            reset_out = await reset_simulation()
            self.assertEqual(reset_out["status"], "success")

            city_graph = await get_city_graph()
            self.assertEqual(len(city_graph.nodes), 20)

            # Ingest Detection
            det_payload = IncidentDetectionPayload(
                camera_id="CCTV_API_TEST",
                candidate_type="possible_collision",
                confidence=0.86,
                location_node="NODE-07",
                affected_road_id="ROAD-04",
                is_simulated=True
            )
            inc = await ingest_detection(det_payload)
            self.assertEqual(inc.status, IncidentStatus.CANDIDATE)

            # Verification
            v_req = IncidentVerificationRequest(
                verified=True,
                operator_id="API_DISPATCHER",
                notes="API verification pass"
            )
            v_inc = await verify_incident(inc.incident_id, v_req)
            self.assertIn(v_inc.status, [IncidentStatus.VERIFIED, IncidentStatus.RESPONSE_RECOMMENDED])

            # Dispatch
            d_inc = await dispatch_incident(inc.incident_id)
            self.assertEqual(d_inc.status, IncidentStatus.SIMULATED_DISPATCH)

            # Resources endpoints
            units = await list_emergency_units()
            self.assertGreaterEqual(len(units), 5)
            u = await get_unit("AMB-01")
            self.assertEqual(u.unit_id, "AMB-01")

            # Routing endpoint
            r_req = RouteRequest(
                origin_node="INT-04",
                destination_node="INT-07",
                unit_id="AMB-01",
                avoid_road_ids=["ROAD-04"]
            )
            r_res = await calculate_route(r_req)
            self.assertEqual(r_res.route_status, RouteStatus.CALCULATED)
            self.assertEqual(r_res.unit_current_position["node"], u.current_node)
            self.assertIn("ROAD-04", r_res.avoided_roads)

            # Orchestration endpoints
            orch_state = await get_orchestration_state()
            self.assertEqual(orch_state.status, IncidentStatus.SIMULATED_DISPATCH.value)

        asyncio.run(run_api_checks())


if __name__ == "__main__":
    unittest.main()
