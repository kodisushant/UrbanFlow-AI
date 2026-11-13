import random
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
from app.services.resource_service import resource_service, DISPATCH_RULES
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
            active_incident=None,
            active_routes=[],
            dispatched_units=[],
            signal_priority_nodes=[],
            diverted_roads=[],
            traffic_diversions={"diverted_road_ids": [], "diversion_route": None},
            signal_priority_corridor={"corridor_nodes": [], "active": False},
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

        # Allocate units based on DISPATCH_RULES
        scen_type = incident.scenario_type or ("fire" if "fire" in incident.incident_type.lower() else "accident")
        rules = DISPATCH_RULES.get(scen_type, DISPATCH_RULES["accident"])
        assigned_ids = []
        for req_type, count in rules.items():
            nearest = resource_service.find_nearest_available_units(
                target_node=incident.location_node,
                required_type=req_type,
                count=count,
                avoid_road_ids={incident.affected_road_id} if incident.affected_road_id else None
            )
            for u in nearest:
                if u.unit_id not in assigned_ids:
                    assigned_ids.append(u.unit_id)

        incident.assigned_unit_ids = assigned_ids
        self.state.recommended_service = " & ".join(rules.keys())

        self.log_agent_action(
            agent_name="EmergencyAgent",
            role="Resource Dispatch",
            action=f"Recommended {' & '.join(assigned_ids)}",
            summary=f"Allocated {len(assigned_ids)} nearest available units for {scen_type} emergency: {', '.join(assigned_ids)}.",
            details={"assigned_units": assigned_ids, "scenario_type": scen_type}
        )

        self.state.explanation = f"Response recommended for {incident.incident_id}. Ready for simulated dispatch."
        return incident

    def execute_dispatch(self, incident_id: str) -> OrchestrationState:
        """Step 4 & 5: Simulated dispatch, routing, green corridor and traffic diversion."""
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        scen_type = incident.scenario_type or ("fire" if "fire" in incident.incident_type.lower() else "accident")
        rules = DISPATCH_RULES.get(scen_type, DISPATCH_RULES["accident"])

        # Flag affected road as blocked if present
        blocked_roads = []
        if incident.affected_road_id:
            city_graph_service.set_road_blocked(incident.affected_road_id, True)
            blocked_roads.append(incident.affected_road_id)
            for pair in [f"{incident.affected_road_id[:-1]}B", f"{incident.affected_road_id[:-1]}A"]:
                if city_graph_service.get_edge(pair):
                    city_graph_service.set_road_blocked(pair, True)
                    blocked_roads.append(pair)

        # Allocate units using DISPATCH_RULES if not already assigned
        dispatched_units = []
        if incident.assigned_unit_ids:
            for uid in incident.assigned_unit_ids:
                u = resource_service.get_unit(uid)
                if u:
                    dispatched_units.append(u)
        else:
            for req_type, count in rules.items():
                units = resource_service.find_nearest_available_units(
                    target_node=incident.location_node,
                    required_type=req_type,
                    count=count,
                    avoid_road_ids=set(blocked_roads)
                )
                if len(units) < count:
                    self.log_agent_action(
                        agent_name="EmergencyAgent",
                        role="Dispatch Warning",
                        action="Partial Resource Warning",
                        summary=f"Requested {count} {req_type} units for {scen_type}, but only {len(units)} available. Proceeding with partial response.",
                        details={"required_type": req_type, "needed": count, "found": len(units)}
                    )
                dispatched_units.extend(units)
            incident.assigned_unit_ids = [u.unit_id for u in dispatched_units]

        self.state.dispatched_units = dispatched_units

        # Update incident status to SIMULATED_DISPATCH
        incident_service.update_status(incident_id, IncidentStatus.SIMULATED_DISPATCH)
        self.state.status = "simulated_dispatch"
        self.state.stage = "active_emergency_response"
        self.state.current_step = 4

        # Route agent calculates primary emergency route for each unit
        routes = []
        for unit in dispatched_units:
            route_res = route_agent.plan_emergency_route(
                unit=unit,
                incident=incident,
                avoid_road_ids=set(blocked_roads),
                algorithm="astar"
            )
            if route_res:
                route_res.unit_type = unit.unit_type
                route_res.unit_id = unit.unit_id
                routes.append(route_res)

                # Store route geometry and dispatch timestamp on unit for simulated movement
                coords_list = [
                    [c["latitude"], c["longitude"]]
                    for c in route_res.coordinates
                ] if route_res.coordinates else []

                resource_service.dispatch_unit_with_route(
                    unit_id=unit.unit_id,
                    incident_id=incident.incident_id,
                    target_node=incident.location_node,
                    route_geometry=coords_list,
                    eta_seconds=route_res.eta_seconds,
                    total_distance_meters=route_res.total_distance_meters
                )

                self.state.signal_priority_nodes.extend(route_res.signal_priority_nodes)
                self.state.diverted_roads.extend(route_res.diverted_roads)
                self.log_agent_action(
                    agent_name="RouteAgent",
                    role="Graph Optimization",
                    action=f"Computed A* Emergency Corridor for {unit.unit_id}",
                    summary=f"Avoided blocked road segments {', '.join(route_res.avoided_roads)}. ETA: {route_res.estimated_travel_time_minutes} min.",
                    details={
                        "route_id": route_res.route_id,
                        "unit_type": unit.unit_type,
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
            f"Active emergency response in progress. Units {', '.join([u.call_sign for u in dispatched_units])} "
            f"dispatched to {incident.location_node} ({scen_type.upper()}). Emergency green wave and civilian diversion activated."
        )

        return self.state

    def run_full_scenario(self, req: ScenarioRunRequest) -> OrchestrationState:
        """
        One-click demo scenario execution:
        Picks a validated random incident node and scenario type (accident or fire),
        computes routes for all required units, and auto-dispatches.
        """
        if resource_service.is_mission_in_progress():
            busy_units = [u.unit_id for u in resource_service.get_all_units() if u.status not in ["available", "stationed"]]
            raise ValueError(f"Active mission in progress with units: {', '.join(busy_units)}. Please wait for completion or click Reset.")

        self.reset_state()

        rng = random.Random(req.seed) if req.seed is not None else random.Random()
        scen_type = req.scenario_type or rng.choice(["accident", "fire"])
        if scen_type not in ["accident", "fire"]:
            scen_type = "accident"

        rules = DISPATCH_RULES[scen_type]
        required_types = list(rules.keys())

        # Exclude nodes within 1 hop of all stations so demo isn't trivial
        all_stations = {u.station_node for u in resource_service.get_all_units()}
        station_1_hops = set(all_stations)
        for s in all_stations:
            for nxt, _ in city_graph_service.adjacency.get(s, []):
                station_1_hops.add(nxt)
            for u_id, nbrs in city_graph_service.adjacency.items():
                if any(target == s for target, _ in nbrs):
                    station_1_hops.add(u_id)

        eligible = [n for n in city_graph_service.nodes.keys() if n not in station_1_hops]
        if not eligible:
            eligible = [n for n in city_graph_service.nodes.keys() if n not in all_stations]

        rng.shuffle(eligible)
        chosen_node = None
        for cand in eligible:
            reachable = True
            for rtype in required_types:
                norm_type = resource_service.normalize_unit_type(rtype)
                candidate_stations = [
                    u.station_node for u in resource_service.get_all_units()
                    if resource_service.normalize_unit_type(u.unit_type) == norm_type
                ]
                can_reach = any(
                    city_graph_service.find_shortest_path(st, cand, algorithm="astar", allow_destination_access=True) is not None
                    for st in candidate_stations
                )
                if not can_reach:
                    reachable = False
                    break
            if reachable:
                chosen_node = cand
                break

        if not chosen_node:
            chosen_node = eligible[0] if eligible else "INT-03"

        touching_roads = []
        for rid, edge in city_graph_service.edges.items():
            if edge.source_node == chosen_node or edge.target_node == chosen_node:
                touching_roads.append(rid)
        affected_road_id = rng.choice(touching_roads) if touching_roads else None

        node_obj = city_graph_service.get_node(chosen_node)
        lat = node_obj.latitude if node_obj else 17.4485
        lon = node_obj.longitude if node_obj else 78.3740

        patient_count = rng.randint(1, 3)
        candidate_type = "structure_fire" if scen_type == "fire" else "multi_vehicle_collision"

        # 1. Ingest observation on affected road
        if affected_road_id:
            traffic_service.ingest_observation(TrafficObservation(
                road_id=affected_road_id,
                vehicle_count=50,
                average_speed_kmph=0.0,
                source="cctv_camera_01"
            ))

        # 2. Candidate Detection at chosen node
        detection = IncidentDetectionPayload(
            camera_id="cctv_camera_01",
            source="cctv_camera_01",
            candidate_type=candidate_type,
            type=candidate_type,
            confidence=0.92 if scen_type == "fire" else 0.88,
            location_node=chosen_node,
            affected_road_id=affected_road_id,
            road_id=affected_road_id,
            patient_count=patient_count,
            scenario_type=scen_type,
            evidence_urls=[
                "assets/evidence/INC-CCTV-001_frame_426.jpg",
                "assets/evidence/INC-CCTV-001_crop_14_19.jpg"
            ],
            observed_vehicles=[
                ObservedVehicle(vehicle_class="car", bbox=[120, 240, 200, 310], speed_kmph=0.0, is_stopped=True)
            ],
            is_simulated=True
        )

        incident = self.handle_detection(detection)

        # 3. Auto-verify and Auto-dispatch for 1-click Run Scenario
        v_req = IncidentVerificationRequest(
            verified=True,
            operator_id=req.operator_id or "OP-CHIEF-01",
            notes=req.operator_notes or f"Verified by Command Center Operator via CCTV evidence snapshot ({scen_type.title()} emergency confirmed)."
        )
        self.handle_verification(incident.incident_id, v_req)
        self.execute_dispatch(incident.incident_id)

        return self.state


workflow_coordinator = WorkflowCoordinator()
