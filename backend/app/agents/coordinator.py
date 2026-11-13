from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.schemas.orchestration import OrchestrationState, AgentActionRecord, ScenarioRunRequest
from app.schemas.incident import (
    IncidentRecord,
    IncidentStatus,
    IncidentDetectionPayload,
    IncidentVerificationRequest,
    ObservedVehicle,
)
from app.schemas.traffic import TrafficObservation, CongestionLevel
from app.schemas.resource import ResourceStatus, ResourceType
from app.services.incident_service import incident_service
from app.services.traffic_service import traffic_service
from app.services.resource_service import resource_service
from app.services.city_graph_service import city_graph_service
from app.agents.incident_agent import incident_agent
from app.agents.traffic_agent import traffic_agent
from app.agents.emergency_agent import emergency_agent
from app.agents.route_agent import route_agent


class WorkflowCoordinator:
    """
    Central multi-agent coordinator that manages the end-to-end scenario pipeline:
    1. Detection (Candidate) -> 2. Operator Verification -> 3. Response Recommendation ->
    4. Simulated Dispatch & Routing -> 5. Corridor Priority & Diversion Explanation
    """

    def __init__(self):
        self.state = OrchestrationState(
            workflow_id="WF-SCENARIO-DEMO-01",
            scenario_id="WF-SCENARIO-DEMO-01",
            stage="idle",
            status="idle",
            current_step=0,
            total_steps=5,
            explanation="System initialized in idle standby. Awaiting detection or scenario trigger."
        )

    def get_state(self) -> OrchestrationState:
        return self.state

    def reset_state(self):
        incident_service.reset()
        traffic_service.reset()
        resource_service.initialize_default_units()
        city_graph_service.initialize_default_city()
        self.state = OrchestrationState(
            workflow_id="WF-SCENARIO-DEMO-01",
            scenario_id="WF-SCENARIO-DEMO-01",
            stage="idle",
            status="idle",
            current_step=0,
            total_steps=5,
            explanation="System reset to Cyber City Metro Network baseline standby."
        )

    def log_agent_action(self, agent_name: str, action: str, summary: str, details: Dict[str, Any], role: str = "Decision Agent"):
        record = AgentActionRecord(
            agent_name=agent_name,
            role=role,
            action=action,
            reasoning=summary,
            summary=summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
            simulated=True,
            structured_output=details
        )
        self.state.agent_log.append(record)
        self.state.agent_logs.append(record)

    def handle_detection(self, payload: IncidentDetectionPayload) -> IncidentRecord:
        """Step 1: Ingest candidate detection from Member 2 CV."""
        incident = incident_service.create_candidate_incident(payload)
        self.state.active_incident = incident
        self.state.status = "candidate"
        self.state.stage = "incident_detected"
        self.state.current_step = 1

        # Incident agent performs preliminary triage
        sev_summary, rec_svc, structured_rep = incident_agent.analyze_candidate(incident)
        incident.structured_report = structured_rep
        incident.recommended_service = "ambulance & police_patrol"

        self.log_agent_action(
            agent_name="VisionAgent",
            role="CCTV Perception",
            action="Flagged candidate incident",
            summary=f"Relative deceleration detected on tracked vehicles; candidate {payload.candidate_type} flagged with heuristic score {payload.confidence:.2f}.",
            details={
                "incident_id": incident.incident_id,
                "camera_id": payload.camera_id,
                "confidence": payload.confidence,
                "location_node": incident.location_node,
            }
        )
        self.state.explanation = f"Candidate incident logged at {incident.location_node}. Awaiting operator verification."
        return incident

    def handle_verification(self, incident_id: str, req: IncidentVerificationRequest) -> IncidentRecord:
        """Step 2: Human-in-the-loop verification."""
        incident = incident_service.verify_incident(incident_id, req)
        self.state.active_incident = incident

        if req.verified:
            self.state.status = "verified"
            self.state.stage = "verified"
            self.state.current_step = 2

            self.log_agent_action(
                agent_name="IncidentAgent",
                role="Triage & Classification",
                action="Verified candidate incident",
                summary=f"Human operator {req.operator_id} confirmed collision at {incident.location_node}. Severity set to {incident.severity}.",
                details={"verified": True, "notes": req.notes}
            )
            # Proceed to recommend response
            self.recommend_response(incident)
        else:
            self.state.status = "resolved"
            self.state.stage = "resolved"
            self.state.explanation = f"Incident {incident_id} dismissed as false positive by operator {req.operator_id}."
            self.log_agent_action(
                agent_name="IncidentAgent",
                role="Triage & Classification",
                action="operator_rejection",
                summary=f"Incident {incident_id} rejected by operator {req.operator_id}.",
                details={"verified": False, "notes": req.notes}
            )
        return incident

    def recommend_response(self, incident: IncidentRecord) -> IncidentRecord:
        """Step 3: Response recommendation (moves status to response_recommended)."""
        incident_service.update_status(incident.incident_id, IncidentStatus.RESPONSE_RECOMMENDED)
        self.state.status = "response_recommended"
        self.state.stage = "response_recommended"
        self.state.current_step = 3

        # Traffic agent inspects surrounding corridor
        corridor_summary = traffic_agent.summarize_corridor([incident.affected_road_id or "ROAD-03A"])
        self.log_agent_action(
            agent_name="TrafficAgent",
            role="Congestion Analytics",
            action="Analyzed corridor congestion",
            summary=corridor_summary["summary"],
            details=corridor_summary
        )

        # Allocate primary unit (Ambulance)
        amb_unit, amb_reasoning = emergency_agent.coordinate_response(
            incident=incident,
            recommended_type="ambulance",
            avoid_road_ids={incident.affected_road_id} if incident.affected_road_id else None
        )

        assigned_ids = []
        if amb_unit:
            assigned_ids.append(amb_unit.unit_id)

        # Allocate secondary unit (Police patrol)
        pol_unit, _ = emergency_agent.coordinate_response(
            incident=incident,
            recommended_type="police_patrol",
            avoid_road_ids={incident.affected_road_id} if incident.affected_road_id else None
        )
        if pol_unit and pol_unit.unit_id not in assigned_ids:
            assigned_ids.append(pol_unit.unit_id)

        incident.assigned_unit_ids = assigned_ids
        self.state.recommended_service = "ambulance & police_patrol"

        self.log_agent_action(
            agent_name="EmergencyAgent",
            role="Resource Dispatch",
            action=f"Recommended {' & '.join(assigned_ids)}",
            summary=f"Medic One ALS and Patrol Alpha allocated from respective stations for optimal proximity.",
            details={"assigned_units": assigned_ids}
        )

        self.state.explanation = f"Response recommended for {incident.incident_id}. Ready for simulated dispatch."
        return incident

    def execute_dispatch(self, incident_id: str) -> OrchestrationState:
        """Step 4 & 5: Simulated dispatch, routing, green corridor and traffic diversion."""
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        # Update unit status to DISPATCHED
        dispatched_units = []
        for uid in incident.assigned_unit_ids:
            unit = resource_service.update_unit_status(uid, "dispatched", incident_id)
            if unit:
                dispatched_units.append(unit)

        self.state.dispatched_units = dispatched_units

        # Update incident status to SIMULATED_DISPATCH
        incident_service.update_status(incident_id, IncidentStatus.SIMULATED_DISPATCH)
        self.state.status = "simulated_dispatch"
        self.state.stage = "active_emergency_response"
        self.state.current_step = 4

        # Flag affected road as blocked if present
        blocked_roads = []
        if incident.affected_road_id:
            city_graph_service.set_road_blocked(incident.affected_road_id, True)
            blocked_roads.append(incident.affected_road_id)
            for pair in [f"{incident.affected_road_id[:-1]}B", f"{incident.affected_road_id[:-1]}A"]:
                if city_graph_service.get_edge(pair):
                    city_graph_service.set_road_blocked(pair, True)
                    blocked_roads.append(pair)

        # Route agent calculates primary emergency route
        routes = []
        for unit in dispatched_units:
            route_res = route_agent.plan_emergency_route(
                unit=unit,
                incident=incident,
                avoid_road_ids=set(blocked_roads),
                algorithm="astar"
            )
            if route_res:
                routes.append(route_res)
                self.state.signal_priority_nodes.extend(route_res.signal_priority_nodes)
                self.state.diverted_roads.extend(route_res.diverted_roads)
                self.log_agent_action(
                    agent_name="RouteAgent",
                    role="Graph Optimization",
                    action=f"Computed A* Emergency Corridor for {unit.unit_id}",
                    summary=f"Avoided blocked road segments {', '.join(route_res.avoided_roads)}. ETA: {route_res.estimated_travel_time_minutes} min.",
                    details={
                        "route_id": route_res.route_id,
                        "eta_seconds": route_res.eta_seconds,
                        "signal_nodes": route_res.signal_priority_nodes,
                        "avoided_roads": route_res.avoided_roads
                    }
                )

        self.state.active_routes = routes

        # Green corridor signals
        unique_signal_nodes = list(dict.fromkeys(self.state.signal_priority_nodes))
        self.state.signal_priority_corridor = {
            "corridor_nodes": unique_signal_nodes,
            "active": True
        }

        self.log_agent_action(
            agent_name="TrafficAgent",
            role="Signal & Corridor Control",
            action="Activated Green Corridor",
            summary=f"Preempted signals at {', '.join(unique_signal_nodes[:4])} for emergency wave.",
            details={"corridor_nodes": unique_signal_nodes}
        )

        # Plan diversion route for civilian traffic
        diversion_route = None
        if blocked_roads:
            # Plan civilian detour around blocked road
            civ_unit = resource_service.get_unit("AMB-02")
            if civ_unit:
                diversion_route = route_agent.plan_emergency_route(
                    unit=civ_unit,
                    incident=incident,
                    avoid_road_ids=set(blocked_roads),
                    algorithm="dijkstra"
                )

        self.state.traffic_diversions = {
            "diverted_road_ids": list(set(blocked_roads)),
            "diversion_route": diversion_route
        }

        self.state.current_step = 5
        self.state.explanation = (
            f"Active emergency response in progress. Unit {dispatched_units[0].call_sign if dispatched_units else 'Units'} "
            f"dispatched to {incident.location_node}. Emergency green wave and civilian diversion activated."
        )

        return self.state

    def run_full_scenario(self, req: ScenarioRunRequest) -> OrchestrationState:
        """
        One-click demo scenario execution:
        Triggers the complete 8-step pipeline from simulated CCTV event to diversion.
        """
        self.reset_state()

        # 1. Ingest heavy traffic observation on ROAD-03A
        traffic_service.ingest_observation(TrafficObservation(
            road_id="ROAD-03A",
            vehicle_count=50,
            average_speed_kmph=0.0,
            source="cctv_camera_01"
        ))

        # 2. Candidate Detection at INT-03 (Cyber Gateway Hub)
        node = city_graph_service.get_node("INT-03")
        lat = node.latitude if node else 17.4485
        lon = node.longitude if node else 78.3740

        detection = IncidentDetectionPayload(
            camera_id="cctv_camera_01",
            source="cctv_camera_01",
            candidate_type="possible_collision",
            type="possible_collision",
            confidence=0.85,
            heuristic_score=0.85,
            location_node="INT-03",
            affected_road_id="ROAD-03A",
            road_id="ROAD-03A",
            evidence_image_url="assets/evidence/INC-CCTV-001_frame_426.jpg",
            evidence_urls=[
                "assets/evidence/INC-CCTV-001_frame_426.jpg",
                "assets/evidence/INC-CCTV-001_crop_14_19.jpg"
            ],
            observed_vehicles=[
                ObservedVehicle(vehicle_class="car", bbox=[120, 240, 200, 310], speed_kmph=0.0, is_stopped=True),
                ObservedVehicle(vehicle_class="truck", bbox=[180, 250, 320, 380], speed_kmph=0.0, is_stopped=True)
            ],
            is_simulated=True
        )

        incident = self.handle_detection(detection)

        # 3. Handle verification
        if req.auto_verify:
            v_req = IncidentVerificationRequest(
                verified=True,
                operator_id=req.operator_id or "OP-CHIEF-01",
                notes=req.operator_notes or "Verified by Command Center Operator via CCTV evidence snapshot."
            )
            self.handle_verification(incident.incident_id, v_req)

            # 4 & 5. Dispatch and route
            self.execute_dispatch(incident.incident_id)

        return self.state


workflow_coordinator = WorkflowCoordinator()
