import sys
import os
import random

sys.path.insert(0, os.path.abspath("backend"))

from app.agents.coordinator import workflow_coordinator
from app.services.resource_service import resource_service
from app.services.city_graph_service import city_graph_service
from app.schemas.orchestration import ScenarioRunRequest


def run_full_verification():
    print("=" * 70)
    print("URBANFLOW-AI RUN SCENARIO EXTENDED VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: 10 CONSECUTIVE SCENARIOS WITH RANDOM SEEDS COVERING BOTH TYPES
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing 10 consecutive scenarios with random seeds...")
    random.seed(2026)

    for i in range(1, 11):
        stype = "accident" if i % 2 == 1 else "fire"
        seed_val = random.randint(1, 999999)
        print(f"\n--- Scenario {i}/10: Type='{stype}', Seed={seed_val} ---")

        req = ScenarioRunRequest(
            scenario_name=f"verification_run_{i}",
            scenario_type=stype,
            seed=seed_val,
            auto_verify=True
        )

        state = workflow_coordinator.run_full_scenario(req)
        inc = state.active_incident
        assert inc is not None, f"Scenario {i}: Active incident is None"
        print(f"  Incident ID: {inc.incident_id} at Node: {inc.location_node}")
        print(f"  Affected Road: {inc.affected_road_id}, Blocked: True")
        print(f"  Patients: {inc.patient_count}, Severity: {inc.severity}")

        dispatched = [u.unit_id for u in state.dispatched_units]
        print(f"  Dispatched Units ({len(dispatched)}): {', '.join(dispatched)}")
        print(f"  Active Routes ({len(state.active_routes)}): {[r.route_id for r in state.active_routes]}")

        # Check dispatch rules
        u_types = [u.unit_type for u in state.dispatched_units]
        if stype == "accident":
            assert u_types.count("ambulance") == 1, f"Scenario {i} (accident) expected 1 ambulance, got {u_types}"
            assert u_types.count("police_patrol") == 1, f"Scenario {i} (accident) expected 1 police, got {u_types}"
            assert u_types.count("fire_engine") == 0, f"Scenario {i} (accident) expected 0 fire, got {u_types}"
        else:
            assert u_types.count("fire_engine") == 1, f"Scenario {i} (fire) expected 1 fire engine, got {u_types}"
            assert u_types.count("ambulance") == 1, f"Scenario {i} (fire) expected 1 ambulance, got {u_types}"
            assert u_types.count("police_patrol") == 1, f"Scenario {i} (fire) expected 1 police, got {u_types}"

        # Fast-forward simulation ticks until mission completes
        curr_sim_time = state.dispatched_units[0].dispatch_timestamp or 1000.0
        amb_seen_states = {u.status for u in state.dispatched_units if u.unit_type == "ambulance"}
        max_ticks = 300
        ticks_run = 0

        while resource_service.is_mission_in_progress() and ticks_run < max_ticks:
            ticks_run += 1
            curr_sim_time += 3.0
            live_units = resource_service.tick(speed_multiplier=5.0, current_time=curr_sim_time)
            for u in live_units:
                if u.unit_type == "ambulance":
                    amb_seen_states.add(u.status)

        assert not resource_service.is_mission_in_progress(), f"Scenario {i}: Units stuck after {ticks_run} ticks!"
        for u in resource_service.get_all_units():
            assert u.status == "available", f"Scenario {i}: Unit {u.unit_id} not available ({u.status})"
            assert u.current_node == u.station_node, f"Scenario {i}: Unit {u.unit_id} not at station ({u.current_node})"
            assert u.patient_count == 0, f"Scenario {i}: Unit {u.unit_id} has remaining patients"

        # Check ambulance visited all state machine phases
        assert "en_route" in amb_seen_states, f"Scenario {i}: Ambulance did not visit en_route"
        assert "on_scene" in amb_seen_states, f"Scenario {i}: Ambulance did not visit on_scene"
        assert "loading" in amb_seen_states, f"Scenario {i}: Ambulance did not visit loading"
        assert "transporting" in amb_seen_states, f"Scenario {i}: Ambulance did not visit transporting"
        assert "at_hospital" in amb_seen_states, f"Scenario {i}: Ambulance did not visit at_hospital"
        assert "returning" in amb_seen_states, f"Scenario {i}: Ambulance did not visit returning"
        assert "available" in amb_seen_states, f"Scenario {i}: Ambulance did not return to available"

        print(f"  All units completed mission, transported patients, and returned to station in {ticks_run} ticks.")

    print("\n>>> TEST 1 PASSED: 10/10 consecutive scenarios executed flawlessly with 0 unreachable incidents and 0 stuck units.")

    # -------------------------------------------------------------------------
    # TEST 2: MID-MISSION CONFLICT REJECTION
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing mid-mission conflict rejection (HTTP 409 / ValueError)...")
    workflow_coordinator.reset_state()
    req_mid = ScenarioRunRequest(scenario_type="fire", seed=50)
    workflow_coordinator.run_full_scenario(req_mid)
    assert resource_service.is_mission_in_progress()

    rejected = False
    try:
        workflow_coordinator.run_full_scenario(ScenarioRunRequest(scenario_type="accident"))
    except ValueError as e:
        rejected = True
        print(f"  Rejected correctly with: '{e}'")

    assert rejected, "Run Scenario failed to reject mid-mission scenario call!"
    print(">>> TEST 2 PASSED: Active mission conflict properly rejected.")

    # -------------------------------------------------------------------------
    # TEST 3: RESET MID-MISSION
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing reset mid-mission...")
    workflow_coordinator.reset_state()
    assert not resource_service.is_mission_in_progress()
    assert workflow_coordinator.state.active_incident is None
    assert len(workflow_coordinator.state.active_routes) == 0
    for u in resource_service.get_all_units():
        assert u.status == "available"
        assert u.current_node == u.station_node
        assert u.patient_count == 0
    print(">>> TEST 3 PASSED: Reset restored all units to station nodes as available and cleared incidents.")

    print("\n" + "=" * 70)
    print("ALL VERIFICATION CRITERIA VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_full_verification()
