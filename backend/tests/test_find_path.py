<<<<<<< HEAD
﻿import os
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
=======
import os
import sys

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import unittest
import random
from app.services.city_graph_service import city_graph_service
from app.api.v1.routing import _compute_single_path, compare_paths, ComparePathsRequest, FindPathRequest
from app.core.config import settings


class TestFindPathAndComparison(unittest.TestCase):
    def setUp(self):
        # Reset graph to default state
        city_graph_service.initialize_default_city()

    def test_01_no_traffic_both_routes_match(self):
        """When there is no traffic and no road closures, both routes match."""
        # Ensure all roads are free flow and not blocked
        for edge in city_graph_service.edges.values():
            edge.is_blocked = False
            edge.is_diverted = False
            edge.current_congestion_level = "free_flow"
            edge.congestion_weight_multiplier = 1.0

        # Choose two nodes that are connected
        node_ids = list(city_graph_service.nodes.keys())
        self.assertGreater(len(node_ids), 5)

        opt = _compute_single_path(from_node=node_ids[0], to_node=node_ids[4], mode="optimised")
        base = _compute_single_path(from_node=node_ids[0], to_node=node_ids[4], mode="baseline")

        if opt.is_reachable and base.is_reachable:
            # Under uniform speed and 1.0 multiplier, travel times should be identical
            self.assertAlmostEqual(opt.estimated_travel_time_seconds, base.estimated_travel_time_seconds, delta=1.0)
            self.assertEqual(opt.node_sequence, base.node_sequence)

    def test_02_random_traffic_20_pairs_optimised_time_le_baseline(self):
        """
        With random traffic on, 20 random from/to pairs:
        optimised time is <= baseline time in every case (assert in a backend test; if ever greater, that's a bug).
        """
        # Randomize traffic with a known seed
        seed, blocked, congested, _ = city_graph_service.randomize_traffic_conditions(seed=42, num_blocked=3)
        self.assertGreaterEqual(len(blocked), 1)

        nodes = [nid for nid in city_graph_service.nodes.keys() if len(city_graph_service.adjacency.get(nid, [])) > 0]
        rng = random.Random(1337)

        tested = 0
        attempts = 0
        while tested < 20 and attempts < 200:
            attempts += 1
            u, v = rng.sample(nodes, 2)
            opt = _compute_single_path(from_node=u, to_node=v, mode="optimised", algorithm="astar")
            base = _compute_single_path(from_node=u, to_node=v, mode="baseline")

            if not opt.is_reachable or not base.is_reachable:
                continue

            # Core invariant: optimised travel time MUST be <= baseline travel time
            self.assertLessEqual(
                opt.estimated_travel_time_seconds,
                base.estimated_travel_time_seconds + 1e-4,
                f"Failed for pair {u} -> {v}: opt={opt.estimated_travel_time_seconds}s, base={base.estimated_travel_time_seconds}s"
            )
            tested += 1

        self.assertEqual(tested, 20, "Should have tested 20 reachable random pairs")

    def test_05_randomize_traffic_endpoint_seeds(self):
        """Test randomize traffic endpoint with None, 0, 42, and large seed."""
        import asyncio
        from app.api.v1.routing import randomize_traffic, RandomizeTrafficRequest

        async def run_calls():
            for s in [None, 0, 42, 987654321]:
                req = RandomizeTrafficRequest(seed=s)
                res = await randomize_traffic(req)
                self.assertEqual(res.status, "traffic_randomized")
                self.assertIsInstance(res.seed_used, int)
                self.assertGreater(len(res.blocked_roads), 0)
                self.assertGreater(res.congested_roads_count, 0)

        asyncio.run(run_calls())

    def test_06_congest_baseline_endpoint(self):
        """Test congesting the baseline route specifically between two nodes."""
        import asyncio
        from app.api.v1.routing import congest_baseline_route, CongestBaselineRequest

        nodes = list(city_graph_service.nodes.keys())
        u = nodes[0]
        v = nodes[5]

        async def run_congest():
            res = await congest_baseline_route(CongestBaselineRequest(from_node=u, to_node=v))
            self.assertEqual(res.status, "baseline_congested")
            self.assertGreater(len(res.congested_roads), 0)
            self.assertIsNotNone(res.blocked_road)

            # Re-evaluate baseline and optimised
            opt = _compute_single_path(u, v, mode="optimised")
            base = _compute_single_path(u, v, mode="baseline")
            self.assertTrue(base.has_blocked_segments)
            self.assertLess(opt.estimated_travel_time_seconds, base.estimated_travel_time_seconds)

        asyncio.run(run_congest())

    def test_03_baseline_blocked_road_flagged_and_penalised(self):
        """A blocked road on the baseline path is flagged and penalised with detour penalty."""
        # Reset graph
        for edge in city_graph_service.edges.values():
            edge.is_blocked = False
            edge.current_congestion_level = "free_flow"
            edge.congestion_weight_multiplier = 1.0

        # Find a 2-hop or 3-hop baseline path
        nodes = list(city_graph_service.nodes.keys())
        u = nodes[0]
        v = None
        target_road = None
        for n in nodes[1:10]:
            base = _compute_single_path(from_node=u, to_node=n, mode="baseline")
            if base.is_reachable and len(base.road_ids) >= 2:
                v = n
                target_road = base.road_ids[0]
                break

        self.assertIsNotNone(v, "Need a reachable pair with at least 2 segments")
        
        # Block the first road of the baseline path
        city_graph_service.set_road_blocked(target_road, True)

        # Baseline path should still be the distance shortest path, but flagged as blocked
        base_after = _compute_single_path(from_node=u, to_node=v, mode="baseline")
        self.assertTrue(base_after.has_blocked_segments)
        self.assertGreaterEqual(base_after.blocked_roads_count, 1)
        self.assertGreaterEqual(base_after.detour_penalty_applied_seconds, settings.BLOCKED_ROAD_DETOUR_PENALTY_SECONDS)

        # Optimised path should avoid the blocked road
        opt_after = _compute_single_path(from_node=u, to_node=v, mode="optimised")
        if opt_after.is_reachable:
            self.assertFalse(opt_after.has_blocked_segments)
            self.assertNotIn(target_road, opt_after.road_ids)
            self.assertLess(opt_after.estimated_travel_time_seconds, base_after.estimated_travel_time_seconds)

    def test_04_edge_cases(self):
        """Test edge cases: from == to, invalid nodes, unreachable."""
        nodes = list(city_graph_service.nodes.keys())
        u = nodes[0]

        # Same node
        same = _compute_single_path(from_node=u, to_node=u, mode="optimised")
        self.assertTrue(same.is_reachable)
        self.assertEqual(same.total_distance_meters, 0.0)
        self.assertEqual(same.estimated_travel_time_seconds, 0.0)

        # Invalid node
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            _compute_single_path(from_node="INVALID_XYZ", to_node=u, mode="optimised")

    def test_07_astar_matches_dijkstra_oracle_on_50_pairs(self):
        """Assert A* and Dijkstra return identical travel time cost on 50 random pairs."""
        nodes = [nid for nid in city_graph_service.nodes.keys() if len(city_graph_service.adjacency.get(nid, [])) > 0]
        rng = random.Random(42)

        tested = 0
        attempts = 0
        while tested < 50 and attempts < 1000:
            attempts += 1
            u, v = rng.sample(nodes, 2)
            opt_astar = _compute_single_path(from_node=u, to_node=v, mode="optimised", algorithm="astar")
            opt_dijkstra = _compute_single_path(from_node=u, to_node=v, mode="optimised", algorithm="dijkstra")

            if not opt_astar.is_reachable or not opt_dijkstra.is_reachable:
                continue

            self.assertAlmostEqual(
                opt_astar.estimated_travel_time_seconds,
                opt_dijkstra.estimated_travel_time_seconds,
                delta=1.0,
                msg=f"A* and Dijkstra cost differ for {u} -> {v}: A*={opt_astar.estimated_travel_time_seconds}s, Dijkstra={opt_dijkstra.estimated_travel_time_seconds}s"
            )
            tested += 1

        self.assertEqual(tested, 50, "Should test 50 pairs against Dijkstra oracle")


if __name__ == "__main__":
    unittest.main()
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
