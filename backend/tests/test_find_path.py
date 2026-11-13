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
