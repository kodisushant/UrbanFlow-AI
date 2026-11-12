from typing import Optional, Dict, Any
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
            scenario_id="urbanflow_baseline",
            status="idle",
            current_step=0,
            total_steps=5,
            explanation="System initialized in idle standby. Awaiting detection or scenario run."
        )

    def get_state(self) -> OrchestrationState:
        return self.state

    def reset_state(self):
        incident_service.reset()
        traffic_service.reset()
        resource_service.initialize_default_units()
        city_graph_service.initialize_default_city()
        self.state = OrchestrationState(
            scenario_id="urbanflow_baseline",
            status="idle",
            current_step=0,
            total_steps=5,
            explanation="System reset to default Metropolis SmartGrid standby."
        )

    def log_agent_action(self, agent_name: str, action: str, summary: str, details: Dict[str, Any]):
        record = AgentActionRecord(
            agent_name=agent_name,
            timestamp=datetime.now(timezone.utc),
            action=action,
            summary=summary,
            structured_output=details
        )
        self.state.agent_log.append(record)

    def handle_detection(self, payload: IncidentDetectionPayload) -> IncidentRecord:
        """Step 1: Ingest candidate detection from Member 2 CV."""
        incident = incident_service.create_candidate_incident(payload)
        self.state.active_incident = incident
        self.state.status = IncidentStatus.CANDIDATE.value
        self.state.current_step = 1

        # Incident agent performs preliminary triage
        sev_summary, rec_svc, structured_rep = incident_agent.analyze_candidate(incident)
        incident.structured_report = structured_rep
        incident.recommended_service = rec_svc.value

        self.log_agent_action(
            agent_name="IncidentAgent",
            action="evaluate_candidate_detection",
            summary=f"Logged candidate {payload.candidate_type} with confidence {payload.confidence:.1%}. {sev_summary}",
            details={
                "incident_id": incident.incident_id,
                "camera_id": payload.camera_id,
                "confidence": payload.confidence,
                "preliminary_service": rec_svc.value
            }
        )
        self.state.explanation = f"Candidate incident logged at {incident.location_node}. Awaiting operator verification."
        return incident

    def handle_verification(self, incident_id: str, req: IncidentVerificationRequest) -> IncidentRecord:
        """Step 2: Human-in-the-loop verification."""
        incident = incident_service.verify_incident(incident_id, req)
        self.state.active_incident = incident

        if req.verified:
            self.state.status = IncidentStatus.VERIFIED.value
            self.state.current_step = 2

            self.log_agent_action(
                agent_name="Coordinator",
                action="operator_verification",
                summary=f"Incident {incident_id} verified by operator {req.operator_id}.",
                details={"verified": True, "notes": req.notes}
            )
            # Proceed to recommend response
            self.recommend_response(incident)
        else:
            self.state.status = IncidentStatus.RESOLVED.value
            self.state.explanation = f"Incident {incident_id} dismissed as false positive by operator {req.operator_id}."
            self.log_agent_action(
                agent_name="Coordinator",
                action="operator_rejection",
                summary=f"Incident {incident_id} rejected by operator {req.operator_id}.",
                details={"verified": False, "notes": req.notes}
            )
        return incident

    def recommend_response(self, incident: IncidentRecord) -> IncidentRecord:
        """Step 3: Response recommendation (moves status to response_recommended)."""
        incident_service.update_status(incident.incident_id, IncidentStatus.RESPONSE_RECOMMENDED)
        self.state.status = IncidentStatus.RESPONSE_RECOMMENDED.value
        self.state.current_step = 3

        # Traffic agent inspects surrounding corridor
        corridor_summary = traffic_agent.summarize_corridor([incident.affected_road_id or "ROAD-01"])
        self.log_agent_action(
            agent_name="TrafficAgent",
            action="assess_corridor_congestion",
            summary=corridor_summary["summary"],
            details=corridor_summary
        )

        rec_type = ResourceType(incident.recommended_service or "ambulance")
        # Emergency agent allocates unit
        unit, reasoning = emergency_agent.coordinate_response(
            incident=incident,
            recommended_type=rec_type,
            avoid_road_ids={incident.affected_road_id} if incident.affected_road_id else None
        )

        if unit:
            incident.assigned_unit_ids = [unit.unit_id]
            self.state.recommended_service = rec_type.value
            self.log_agent_action(
                agent_name="EmergencyCoordinationAgent",
                action="allocate_unit",
                summary=reasoning,
                details={"unit_id": unit.unit_id, "type": unit.unit_type.value, "station": unit.station_node}
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
            unit = resource_service.update_unit_status(uid, ResourceStatus.DISPATCHED, incident_id)
            if unit:
                dispatched_units.append(unit)

        self.state.dispatched_units = dispatched_units

        # Update incident status to SIMULATED_DISPATCH
        incident_service.update_status(incident_id, IncidentStatus.SIMULATED_DISPATCH)
        self.state.status = IncidentStatus.SIMULATED_DISPATCH.value
        self.state.current_step = 4

        # Flag affected road as blocked if present
        if incident.affected_road_id:
            city_graph_service.set_road_blocked(incident.affected_road_id, True)

        # Route agent calculates primary and alternative paths
        routes = []
        for unit in dispatched_units:
            route_res = route_agent.plan_emergency_route(
                unit=unit,
                incident=incident,
                avoid_road_ids={incident.affected_road_id} if incident.affected_road_id else set(),
                algorithm="astar"
            )
            if route_res:
                routes.append(route_res)
                self.state.signal_priority_nodes.extend(route_res.signal_priority_nodes)
                self.state.diverted_roads.extend(route_res.diverted_roads)
                self.log_agent_action(
                    agent_name="RouteOptimizationAgent",
                    action="calculate_emergency_corridor",
                    summary=route_res.explanation,
                    details={
                        "route_id": route_res.route_id,
                        "eta_seconds": route_res.eta_seconds,
                        "signal_nodes": route_res.signal_priority_nodes,
                        "avoided_roads": route_res.avoided_roads
                    }
                )

        self.state.active_routes = routes
        self.state.current_step = 5
        self.state.explanation = (
            f"Active emergency response in progress. Unit {dispatched_units[0].name if dispatched_units else 'Units'} "
            f"dispatched to {incident.location_node}. Emergency green wave activated."
        )

        self.log_agent_action(
            agent_name="Coordinator",
            action="simulated_dispatch_complete",
            summary="Full end-to-end coordination completed. Multi-agent decisions synchronized to dashboard.",
            details={"dispatched_count": len(dispatched_units), "routes_count": len(routes)}
        )

        return self.state

    def run_full_scenario(self, req: ScenarioRunRequest) -> OrchestrationState:
        """
        One-click demo scenario execution:
        Triggers the complete 8-step pipeline from simulated CCTV event to diversion.
        """
        self.reset_state()

        # 1. Ingest heavy traffic observation on ROAD-03 & ROAD-04
        traffic_service.ingest_observation(TrafficObservation(
            road_id="ROAD-03",
            vehicle_count=45,
            average_speed_kmph=15.0,
            source="traffic_sensor_array_3"
        ))

        # 2. Simulate Member 2 CCTV Candidate Collision Detection at NODE-07 (Central Plaza) on ROAD-04
        detection = IncidentDetectionPayload(
            camera_id="CCTV_CAM_NORTH_07",
            candidate_type="possible_collision",
            confidence=0.89,
            location_node="NODE-07",
            affected_road_id="ROAD-04",
            evidence_image_url="/static/evidence/cam07_collision_frame.jpg",
            observed_vehicles=[
                ObservedVehicle(vehicle_class="car", bbox=[100, 150, 200, 250], speed_kmph=0.0, is_stopped=True),
                ObservedVehicle(vehicle_class="truck", bbox=[180, 160, 310, 290], speed_kmph=0.0, is_stopped=True)
            ],
            is_simulated=True
        )

        incident = self.handle_detection(detection)

        # 3. Handle verification
        if req.auto_verify:
            v_req = IncidentVerificationRequest(
                verified=True,
                operator_id=req.operator_id,
                notes=req.operator_notes or "Auto-verified for live hackathon demonstration."
            )
            self.handle_verification(incident.incident_id, v_req)

            # 4 & 5. Dispatch and route
            self.execute_dispatch(incident.incident_id)

        return self.state


workflow_coordinator = WorkflowCoordinator()

