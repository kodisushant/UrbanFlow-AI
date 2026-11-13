import os
import sys
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.city_graph_service import city_graph_service


@pytest.fixture(autouse=True)
def reset_grid():
    city_graph_service.initialize_default_city()
    yield
    city_graph_service.initialize_default_city()


class TestFindPathAndComparison:
    """Rigorous verification of Find Path (Optimised vs Baseline) mode."""

    def test_standby_no_traffic_both_routes_match(self):
        """With no congestion and no blocks, both routes match and time difference is zero."""
        comp = city_graph_service.compare_paths("INT-01", "INT-05")
        assert comp.reachable is True
        assert comp.optimised is not None
        assert comp.baseline is not None
        assert comp.optimised.node_ids == comp.baseline.node_ids
        assert comp.optimised.estimated_travel_time_seconds == comp.baseline.estimated_travel_time_seconds
        assert "identical" in comp.comparison.summary.lower()

    def test_find_path_dijkstra_matches_astar(self):
        """A* and Dijkstra both find the exact same optimal travel time."""
        opt_astar = city_graph_service.find_path("INT-01", "INT-10", mode="optimised", algorithm="astar")
        opt_dijkstra = city_graph_service.find_path("INT-01", "INT-10", mode="optimised", algorithm="dijkstra")

        assert opt_astar.reachable is True
        assert opt_dijkstra.reachable is True
        assert opt_astar.estimated_travel_time_seconds == opt_dijkstra.estimated_travel_time_seconds
        assert opt_astar.total_distance_meters == opt_dijkstra.total_distance_meters
        # A* explores fewer or equal nodes than Dijkstra
        assert opt_astar.nodes_explored <= opt_dijkstra.nodes_explored

    def test_blocked_road_penalised_on_baseline(self):
        """A blocked road on the baseline path is flagged and incurs detour penalty, while optimised avoids it."""
        # Find baseline path between INT-01 and INT-03
        base_pre = city_graph_service.find_path("INT-01", "INT-03", mode="baseline")
        assert len(base_pre.road_ids) > 0
        road_to_block = base_pre.road_ids[0]

        # Block this road
        city_graph_service.set_road_blocked(road_to_block, True)

        comp = city_graph_service.compare_paths("INT-01", "INT-03")
        assert comp.reachable is True
        # Baseline must hit the blocked road
        assert comp.baseline.blocked_roads_hit >= 1
        assert comp.baseline.has_blocked_segments is True
        assert comp.baseline.detour_penalty_seconds >= 300.0

        # Optimised must NOT traverse the blocked road
        assert road_to_block not in comp.optimised.road_ids
        assert comp.optimised.blocked_roads_hit == 0
        assert comp.optimised.has_blocked_segments is False

        # Optimised travel time must be strictly less than or equal to penalised baseline
        assert comp.optimised.estimated_travel_time_seconds <= comp.baseline.estimated_travel_time_seconds
        assert comp.comparison.blocked_roads_avoided >= 1

    def test_10_random_pairs_optimised_le_baseline(self):
        """With random traffic on, for 10 random from/to pairs: optimised time <= baseline time in every case."""
        city_graph_service.randomize_traffic(seed=999, min_blocks=3, max_blocks=4)

        pairs = [
            ("INT-01", "INT-10"),
            ("INT-02", "INT-15"),
            ("INT-03", "INT-18"),
            ("INT-04", "INT-12"),
            ("INT-05", "INT-20"),
            ("INT-06", "INT-14"),
            ("INT-07", "INT-19"),
            ("INT-08", "INT-16"),
            ("INT-09", "INT-17"),
            ("INT-11", "INT-13"),
        ]

        for orig, dest in pairs:
            comp = city_graph_service.compare_paths(orig, dest)
            if comp.reachable:
                opt_time = comp.optimised.estimated_travel_time_seconds
                base_time = comp.baseline.estimated_travel_time_seconds
                assert opt_time <= base_time, (
                    f"BUG: Optimised travel time ({opt_time}s) > Baseline travel time ({base_time}s) "
                    f"for {orig} -> {dest}!"
                )

    def test_edge_cases_same_node_and_invalid_nodes(self):
        """Edge cases: from == to, invalid node IDs."""
        # from == to
        same = city_graph_service.find_path("INT-03", "INT-03", mode="optimised")
        assert same.reachable is True
        assert same.total_distance_meters == 0.0
        assert same.estimated_travel_time_seconds == 0.0
        assert same.node_ids == ["INT-03"]

        # Invalid node
        with pytest.raises(ValueError):
            city_graph_service.find_path("NON-EXISTENT-NODE", "INT-03")

    def test_api_v1_endpoints(self):
        """Test the FastAPI endpoints via TestClient."""
        client = TestClient(app)

        # 1. Randomize traffic endpoint
        rand_resp = client.post("/api/v1/routing/randomize-traffic", json={"seed": 42, "min_blocks": 2, "max_blocks": 3})
        assert rand_resp.status_code == 200
        rand_data = rand_resp.json()
        assert rand_data["status"] == "success"
        assert len(rand_data["blocked_roads"]) >= 2

        # 2. Find Path endpoint (optimised)
        opt_resp = client.post("/api/v1/routing/find-path", json={
            "from_node": "INT-01",
            "to_node": "INT-04",
            "mode": "optimised",
            "algorithm": "astar"
        })
        assert opt_resp.status_code == 200
        opt_data = opt_resp.json()
        assert opt_data["mode"] == "optimised"
        assert opt_data["reachable"] is True
        assert opt_data["total_distance_meters"] > 0
        assert len(opt_data["segments"]) > 0

        # 3. Find Path endpoint (baseline)
        base_resp = client.post("/api/v1/routing/find-path", json={
            "from_node": "INT-01",
            "to_node": "INT-04",
            "mode": "baseline"
        })
        assert base_resp.status_code == 200
        base_data = base_resp.json()
        assert base_data["mode"] == "baseline"

        # 4. Compare endpoint
        comp_resp = client.post("/api/v1/routing/compare", json={
            "from_node": "INT-01",
            "to_node": "INT-04",
            "algorithm": "astar"
        })
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert "optimised" in comp_data
        assert "baseline" in comp_data
        assert "comparison" in comp_data
        assert comp_data["comparison"]["summary"] != ""
