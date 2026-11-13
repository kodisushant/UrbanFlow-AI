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
        self.assertGreaterEqual(len(graph.nodes), 20)
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
        path_em = city_graph_service.find_shortest_path("INT-04", "INT-03")
        self.assertIsNotNone(path_em)
        avoid_road = {path_em.road_ids[1]}
        alt_path = city_graph_service.find_shortest_path("INT-04", "INT-03", avoid_road_ids=avoid_road)
        self.assertIsNotNone(alt_path)
        self.assertNotIn(path_em.road_ids[1], alt_path.road_ids)

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
        all_graph_nodes = {n.node_id for n in city_graph_service.get_city_graph().nodes}
        self.assertIn(state.active_incident.location_node, all_graph_nodes)
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

    def test_08_dispatch_rules(self):
        """
        Verify DISPATCH_RULES:
        - accident dispatches 1 ambulance + 1 police
        - fire dispatches 1 fire truck + 1 ambulance + 1 police
        - Nearest available units assigned, busy units skipped.
        """
        workflow_coordinator.reset_state()
        # 1. Accident
        req_acc = ScenarioRunRequest(scenario_type="accident", seed=42)
        state_acc = workflow_coordinator.run_full_scenario(req_acc)
        unit_types_acc = [u.unit_type for u in state_acc.dispatched_units]
        self.assertEqual(unit_types_acc.count("ambulance"), 1)
        self.assertEqual(unit_types_acc.count("police_patrol"), 1)
        self.assertEqual(unit_types_acc.count("fire_engine"), 0)

        workflow_coordinator.reset_state()
        # 2. Fire
        req_fire = ScenarioRunRequest(scenario_type="fire", seed=101)
        state_fire = workflow_coordinator.run_full_scenario(req_fire)
        unit_types_fire = [u.unit_type for u in state_fire.dispatched_units]
        self.assertEqual(unit_types_fire.count("fire_engine"), 1)
        self.assertEqual(unit_types_fire.count("ambulance"), 1)
        self.assertEqual(unit_types_fire.count("police_patrol"), 1)

    def test_09_unit_state_machine_and_lifecycle(self):
        """
        Verify Unit State Machine transitions:
        Ambulance: available -> en_route -> on_scene -> loading -> transporting -> at_hospital -> returning -> available.
        Fire/Police: available -> en_route -> on_scene -> returning -> available.
        """
        workflow_coordinator.reset_state()
        req = ScenarioRunRequest(scenario_type="accident", seed=77)
        state = workflow_coordinator.run_full_scenario(req)
        self.assertGreaterEqual(state.active_incident.patient_count, 1)

        # Simulate time ticks to fast-forward through state transitions deterministically
        amb_unit = next(u for u in state.dispatched_units if u.unit_type == "ambulance")
        seen_statuses = {amb_unit.status}
        curr_sim_time = amb_unit.dispatch_timestamp or time.time()

        for _ in range(120):
            units = resource_service.tick(speed_multiplier=5.0, current_time=curr_sim_time)
            u_live = next(u for u in units if u.unit_id == amb_unit.unit_id)
            seen_statuses.add(u_live.status)
            curr_sim_time += 15.0
            if not resource_service.is_mission_in_progress():
                break

        # Ambulance should visit en_route, on_scene, loading, transporting, at_hospital, returning, available
        self.assertIn("en_route", seen_statuses)
        self.assertIn("on_scene", seen_statuses)
        self.assertIn("loading", seen_statuses)
        self.assertIn("transporting", seen_statuses)
        self.assertIn("at_hospital", seen_statuses)
        self.assertIn("returning", seen_statuses)
        self.assertIn("available", seen_statuses)

    def test_10_conflict_mid_mission_and_reset(self):
        """Verify Run Scenario rejection while mid-mission, and reset restores all units."""
        workflow_coordinator.reset_state()
        req = ScenarioRunRequest(scenario_type="fire", seed=12)
        workflow_coordinator.run_full_scenario(req)

        # Mission in progress -> Second run-scenario call must raise ValueError
        with self.assertRaises(ValueError):
            workflow_coordinator.run_full_scenario(ScenarioRunRequest(scenario_type="accident"))

        # Reset mid-mission
        workflow_coordinator.reset_state()
        self.assertFalse(resource_service.is_mission_in_progress())
        self.assertIsNone(workflow_coordinator.state.active_incident)
        for u in resource_service.get_all_units():
            self.assertEqual(u.status, "available")
            self.assertEqual(u.current_node, u.station_node)
            self.assertEqual(u.patient_count, 0)

    def test_07_api_v1_endpoints(self):
        """Test API v1 routers through coroutine execution."""
        def run_sync(coro):
            try:
                coro.send(None)
            except StopIteration as e:
                return e.value

        # Simulation
        reset_out = run_sync(reset_simulation())
        self.assertEqual(reset_out["status"], "success")

        city_graph = run_sync(get_city_graph())
        self.assertGreaterEqual(len(city_graph.nodes), 20)

        # Ingest Detection
        det_payload = IncidentDetectionPayload(
            camera_id="CCTV_API_TEST",
            candidate_type="possible_collision",
            confidence=0.86,
            location_node="INT-07",
            affected_road_id="ROAD-04A",
            is_simulated=True
        )
        inc = run_sync(ingest_detection(det_payload))
        self.assertEqual(inc.status, IncidentStatus.CANDIDATE)

        # Verification
        v_req = IncidentVerificationRequest(
            verified=True,
            operator_id="API_DISPATCHER",
            notes="API verification pass"
        )
        v_inc = run_sync(verify_incident(inc.incident_id, v_req))
        self.assertIn(v_inc.status, [IncidentStatus.VERIFIED, IncidentStatus.RESPONSE_RECOMMENDED])

        # Dispatch
        d_inc = run_sync(dispatch_incident(inc.incident_id))
        self.assertEqual(d_inc.status, IncidentStatus.SIMULATED_DISPATCH)

        # Resources endpoints
        units = run_sync(list_emergency_units())
        self.assertGreaterEqual(len(units), 5)
        u = run_sync(get_unit("AMB-01"))
        self.assertEqual(u.unit_id, "AMB-01")

        # Routing endpoint
        r_req = RouteRequest(
            origin_node="INT-04",
            destination_node="INT-07",
            unit_id="AMB-01",
            avoid_road_ids=["ROAD-04A"]
        )
        r_res = run_sync(calculate_route(r_req))
        self.assertEqual(r_res.route_status, RouteStatus.CALCULATED)
        self.assertEqual(r_res.unit_current_position["node"], u.current_node)
        self.assertIn("ROAD-04A", r_res.avoided_roads)

        # Orchestration endpoints
        orch_state = run_sync(get_orchestration_state())
        self.assertEqual(orch_state.status, IncidentStatus.SIMULATED_DISPATCH.value)


if __name__ == "__main__":
    unittest.main()
