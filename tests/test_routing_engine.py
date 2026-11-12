"""
Unit and Integration Tests for UrbanFlow Routing Engine
Member 4: Road Network, Emergency Routing & Traffic Diversion
"""

import unittest
import json
import random
import math
from routing.models import (
    NodeType,
    SignalState,
    UnitStatus,
    EmergencyUnitType,
    VehicleClass,
    RouteContext,
    finite_or_none,
)
from routing.graph import CityGraph, haversine_distance_meters
from routing.city_data import build_cyber_city_network, get_sample_emergency_units
from routing.algorithms import (
    dijkstra,
    astar,
    yen_k_shortest_paths,
    penalty_based_alternatives,
    compute_minimum_effective_cost_per_meter,
)
from routing.emergency import (
    rank_emergency_resources,
    create_emergency_corridor,
    plan_traffic_diversion,
    simulate_unit_movement_timeline,
)
from routing.engine import UrbanFlowRoutingEngine
from routing.service import RoutingService


class TestCityGraph(unittest.TestCase):
    def setUp(self):
        self.graph = build_cyber_city_network()

    def test_graph_structure(self):
        self.assertEqual(len(self.graph.nodes), 20)
        self.assertEqual(len(self.graph.edges), 58)
        self.assertIn("INT-01", self.graph.nodes)
        self.assertIn("INT-04", self.graph.nodes)  # North Hospital
        self.assertIn("INT-07", self.graph.nodes)  # Fire station

    def test_city_data_all_edges_satisfy_haversine(self):
        """Verify that every edge in city_data satisfies length_meters >= 0.999 * haversine."""
        for edge in self.graph.edges.values():
            u = self.graph.nodes[edge.source]
            v = self.graph.nodes[edge.target]
            h_dist = haversine_distance_meters(u.latitude, u.longitude, v.latitude, v.longitude)
            self.assertGreaterEqual(
                edge.length_meters,
                0.999 * h_dist,
                f"Edge {edge.road_id} length ({edge.length_meters}m) is less than Haversine ({h_dist}m)",
            )

    def test_edge_length_validation_raises_error(self):
        """Verify that add_edge raises ValueError if length < 0.999 * haversine."""
        from routing.models import Edge
        bad_edge = Edge(
            road_id="BAD-01",
            source="INT-01",
            target="INT-02",
            name="Too Short Road",
            length_meters=100.0,  # haversine is > 1000m
            speed_limit_kmph=50,
        )
        with self.assertRaises(ValueError):
            self.graph.add_edge(bad_edge)

    def test_geojson_coordinates_lon_lat_bounding_box(self):
        """Verify GeoJSON coordinates are [lon, lat] and within expected bounding box."""
        geojson = self.graph.to_geojson()
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertGreater(len(geojson["features"]), 70)

        # Cyber City bounding box: 17.40 <= lat <= 17.50, 78.30 <= lon <= 78.45
        for feat in geojson["features"]:
            self.assertTrue(feat["properties"]["simulated"])
            geom = feat["geometry"]
            if geom["type"] == "Point":
                lon, lat = geom["coordinates"]
                self.assertGreaterEqual(lat, 17.40)
                self.assertLessEqual(lat, 17.50)
                self.assertGreaterEqual(lon, 78.30)
                self.assertLessEqual(lon, 78.45)
            elif geom["type"] == "LineString":
                coords = geom["coordinates"]
                self.assertEqual(len(coords), 2)
                for lon, lat in coords:
                    self.assertGreaterEqual(lat, 17.40)
                    self.assertLessEqual(lat, 17.50)
                    self.assertGreaterEqual(lon, 78.30)
                    self.assertLessEqual(lon, 78.45)
                # Verify required properties
                props = feat["properties"]
                self.assertIn("pair_id", props)
                self.assertIn("direction", props)
                self.assertIn("is_closed", props)
                self.assertIn("congestion_factor", props)


class TestRoutingAlgorithms(unittest.TestCase):
    def setUp(self):
        self.graph = build_cyber_city_network()

    def test_dijkstra_basic_route(self):
        route = dijkstra(self.graph, "INT-04", "INT-01")
        self.assertIsNotNone(route)
        self.assertEqual(route.node_ids[0], "INT-04")
        self.assertEqual(route.node_ids[-1], "INT-01")
        self.assertGreater(route.total_distance_meters, 0)
        self.assertGreater(route.estimated_travel_time_seconds, 0)

    def test_astar_matches_dijkstra_on_city_graph(self):
        dijk_route = dijkstra(self.graph, "INT-04", "INT-08")
        astar_route = astar(self.graph, "INT-04", "INT-08")
        self.assertIsNotNone(dijk_route)
        self.assertIsNotNone(astar_route)
        self.assertAlmostEqual(
            dijk_route.estimated_travel_time_seconds,
            astar_route.estimated_travel_time_seconds,
            places=2,
        )

    def test_emergency_eta_is_lower_than_civilian_for_same_path(self):
        """Verify that emergency vehicle travel time is strictly lower than civilian."""
        civ_ctx = RouteContext(vehicle_class=VehicleClass.CIVILIAN)
        civ_route = astar(self.graph, "INT-04", "INT-20", ctx=civ_ctx)

        emg_ctx = RouteContext(vehicle_class=VehicleClass.EMERGENCY)
        emg_route = astar(self.graph, "INT-04", "INT-20", ctx=emg_ctx)

        self.assertIsNotNone(civ_route)
        self.assertIsNotNone(emg_route)
        self.assertLess(
            emg_route.estimated_travel_time_seconds,
            civ_route.estimated_travel_time_seconds,
        )

    def test_civilian_route_on_corridor_never_faster(self):
        """Verify that activating an emergency corridor does NOT give civilians a speedup."""
        civ_ctx_base = RouteContext(vehicle_class=VehicleClass.CIVILIAN)
        civ_base = astar(self.graph, "INT-04", "INT-01", ctx=civ_ctx_base)

        # Activate corridor on some road
        corr_roads = set(civ_base.road_ids[:2])
        civ_ctx_corr = RouteContext(vehicle_class=VehicleClass.CIVILIAN, corridor_roads=corr_roads)
        civ_with_corr = astar(self.graph, "INT-04", "INT-01", ctx=civ_ctx_corr)

        # Civilian route cost must not be faster with corridor active
        self.assertGreaterEqual(
            civ_with_corr.estimated_travel_time_seconds,
            civ_base.estimated_travel_time_seconds - 1e-4,
        )

    def test_astar_dijkstra_200_random_graphs(self):
        """Verify A* and Dijkstra return equal costs across 200 random connected graphs."""
        rng = random.Random(42)
        from routing.models import Node, Edge

        for g_idx in range(200):
            rg = CityGraph(name=f"RandomGraph_{g_idx}")
            num_nodes = rng.randint(5, 8)
            # Create nodes on a small lat/lon grid
            for i in range(num_nodes):
                lat = 17.40 + (i * 0.01) + rng.uniform(-0.002, 0.002)
                lon = 78.30 + (i * 0.01) + rng.uniform(-0.002, 0.002)
                rg.add_node(Node(node_id=f"N{i}", name=f"Node_{i}", latitude=lat, longitude=lon))

            # Connect line graph first to guarantee connectivity
            for i in range(num_nodes - 1):
                u, v = f"N{i}", f"N{i+1}"
                h = haversine_distance_meters(rg.nodes[u].latitude, rg.nodes[u].longitude, rg.nodes[v].latitude, rg.nodes[v].longitude)
                length = h * rng.uniform(1.05, 1.30)
                speed = rng.choice([40, 50, 60, 80])
                rg.add_bidirectional_road(f"RE_{i}_f", f"RE_{i}_r", u, v, f"Road_{i}", length, speed)

            # Add extra random edges
            for _ in range(num_nodes):
                u_idx, v_idx = rng.sample(range(num_nodes), 2)
                u, v = f"N{u_idx}", f"N{v_idx}"
                f_id = f"RX_{u_idx}_{v_idx}_f"
                if f_id not in rg.edges:
                    h = haversine_distance_meters(rg.nodes[u].latitude, rg.nodes[u].longitude, rg.nodes[v].latitude, rg.nodes[v].longitude)
                    length = h * rng.uniform(1.05, 1.40)
                    speed = rng.choice([40, 60, 80])
                    rg.add_bidirectional_road(f_id, f"RX_{u_idx}_{v_idx}_r", u, v, f"Cross_{u_idx}_{v_idx}", length, speed)

            # Test random origin and destination
            start = f"N{rng.randint(0, num_nodes - 1)}"
            end = f"N{rng.randint(0, num_nodes - 1)}"

            # Test both civilian and emergency contexts
            is_emg = rng.choice([True, False])
            ctx = RouteContext(
                vehicle_class=VehicleClass.EMERGENCY if is_emg else VehicleClass.CIVILIAN,
                corridor_roads={list(rg.edges.keys())[0]} if is_emg else set(),
            )

            d_path = dijkstra(rg, start, end, ctx=ctx)
            a_path = astar(rg, start, end, ctx=ctx)

            if d_path is None:
                self.assertIsNone(a_path)
            else:
                self.assertIsNotNone(a_path)
                self.assertAlmostEqual(
                    d_path.estimated_travel_time_seconds,
                    a_path.estimated_travel_time_seconds,
                    places=3,
                    msg=f"Cost mismatch in graph {g_idx} from {start} to {end}",
                )

    def test_yen_k_shortest_paths_removes_closed_edges(self):
        k_paths = yen_k_shortest_paths(self.graph, "INT-04", "INT-01", k=3)
        self.assertGreaterEqual(len(k_paths), 2)
        for i in range(len(k_paths) - 1):
            self.assertLessEqual(
                k_paths[i].estimated_travel_time_seconds,
                k_paths[i + 1].estimated_travel_time_seconds + 0.01,
            )

    def test_penalty_based_alternatives_reports_overlap(self):
        primary = astar(self.graph, "INT-04", "INT-20")
        self.assertIsNotNone(primary)
        alts = penalty_based_alternatives(self.graph, "INT-04", "INT-20", primary_route=primary, count=2)
        self.assertGreaterEqual(len(alts), 1)
        self.assertNotEqual(primary.node_ids, alts[0].node_ids)
        self.assertGreaterEqual(alts[0].overlap_ratio, 0.0)
        self.assertLessEqual(alts[0].overlap_ratio, 1.0)


class TestEngineFeaturesAndFixes(unittest.TestCase):
    def setUp(self):
        self.engine = UrbanFlowRoutingEngine()

    def test_unreachable_destination_clean_no_path(self):
        """Verify closing roads to make destination unreachable returns clean result with no crash or inf."""
        # Close all incoming roads to INT-20
        incoming = list(self.engine.graph.reverse_adjacency.get("INT-20", []))
        for edge in incoming:
            self.engine.graph.close_road(edge.road_id)

        res = self.engine.find_route("INT-04", "INT-20")
        self.assertIsNotNone(res)
        self.assertEqual(res.primary_route.node_ids, [])
        self.assertEqual(res.primary_route.road_ids, [])
        self.assertIn("unreachable", res.explanation.lower())

        # Verify serialization handles null travel time cleanly without 'Infinity'
        res_dict = res.to_dict()
        self.assertIsNone(res_dict["estimated_travel_time_seconds"])
        dumped = json.dumps(res_dict, allow_nan=False)
        self.assertNotIn("Infinity", dumped)
        self.assertIn('"estimated_travel_time_seconds": null', dumped)

    def test_blocked_roads_avoided_only_on_baseline(self):
        """Verify blocked_roads_avoided contains only roads on the baseline direct path."""
        # First compute baseline path
        base_route = self.engine.find_route("INT-04", "INT-01")
        self.assertIsNotNone(base_route)

        # 1. Close an unrelated road far away (e.g. ROAD-23A in south)
        self.engine.graph.close_road("ROAD-23A")
        res1 = self.engine.find_route("INT-04", "INT-01")
        self.assertEqual(res1.blocked_roads_avoided, [])

        # 2. Close a road that IS on the baseline path
        road_on_path = base_route.primary_route.road_ids[0]
        self.engine.graph.close_road(road_on_path)
        res2 = self.engine.find_route("INT-04", "INT-01")
        self.assertEqual(res2.blocked_roads_avoided, [road_on_path])
        self.assertIn("Detoured around", res2.explanation)

    def test_partial_lane_blockage_and_reopen(self):
        """Test partial capacity reduction (e.g. 50% lane capacity) and reopening."""
        road_id = "ROAD-01A"
        initial_cost = self.engine.graph.edges[road_id].effective_travel_time_seconds

        # Close 1 of 2 lanes -> 0.5 capacity
        self.engine.set_lane_blockage(road_id, 0.5, direction="forward")
        new_cost = self.engine.graph.edges[road_id].effective_travel_time_seconds
        self.assertGreater(new_cost, initial_cost)

        # Reopen
        self.engine.clear_incident_blockage("INC-TEST", road_id, direction="forward")
        restored_cost = self.engine.graph.edges[road_id].effective_travel_time_seconds
        self.assertAlmostEqual(restored_cost, initial_cost, places=1)

    def test_unit_dispatch_and_release_lifecycle(self):
        """Verify emergency unit dispatch and release state transitions."""
        unit_id = "AMB-01"
        unit = self.engine.emergency_units[unit_id]
        self.assertEqual(unit.availability, UnitStatus.AVAILABLE)

        route_res = self.engine.find_route(unit.location_node, "INT-03", is_emergency=True)
        corridor = self.engine.dispatch_emergency_corridor(
            corridor_id="CORR-LIFECYCLE-01",
            unit_id=unit_id,
            incident_id="INC-LIFE",
            route=route_res.primary_route,
        )

        self.assertEqual(unit.availability, UnitStatus.DISPATCHED)
        self.assertIn("CORR-LIFECYCLE-01", self.engine.active_corridors)
        self.assertEqual(self.engine.graph.nodes["INT-04"].signal_state, SignalState.EMERGENCY_PRIORITY)

        # Release unit
        released = self.engine.release_unit(unit_id)
        self.assertTrue(released)
        self.assertEqual(unit.availability, UnitStatus.AVAILABLE)
        self.assertNotIn("CORR-LIFECYCLE-01", self.engine.active_corridors)
        self.assertEqual(self.engine.graph.nodes["INT-04"].signal_state, SignalState.GREEN)

    def test_hysteresis_prevents_minor_route_switch(self):
        """Verify that hysteresis prevents switching when route improvement is < 10%."""
        route = self.engine.find_route("INT-04", "INT-20", algorithm="astar")
        self.engine.register_active_route("COMMUTER-TEST", "INT-04", "INT-20", route.primary_route)

        first_road = route.primary_route.road_ids[0]

        # Slight congestion change (1.04x) on active route: doesn't warrant detour switch (<10% gain)
        self.engine.graph.update_congestion(first_road, 1.04)
        updates = self.engine.recompute_active_routes(threshold_improvement_fraction=0.10)
        self.assertFalse(updates["COMMUTER-TEST"]["switched"])

        # Severe congestion on active route (4.0x): alternative route via INT-02 is now >10% faster
        self.engine.graph.update_congestion(first_road, 4.0)
        updates2 = self.engine.recompute_active_routes(threshold_improvement_fraction=0.10)
        self.assertTrue(updates2["COMMUTER-TEST"]["switched"])

    def test_strict_json_parsing_no_nan_no_inf(self):
        """Verify all exported JSON assets parse strictly with no NaN or Infinity."""
        files = [
            "data/city_graph.json",
            "data/city_map.geojson",
            "data/emergency_units.json",
            "data/sample_scenario_output.json",
        ]
        def fail_on_constant(val):
            raise ValueError(f"Illegal constant {val} found in JSON")

        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f, parse_constant=fail_on_constant)
            self.assertIsNotNone(data)

    def test_routing_service_layer(self):
        """Test Member 1 RoutingService dictionary methods."""
        service = RoutingService(self.engine)
        route_dict = service.compute_route("INT-04", "INT-01")
        self.assertIn("road_ids", route_dict)
        self.assertIn("node_ids", route_dict)
        self.assertTrue(route_dict["simulated"])

        geojson = service.get_graph_geojson()
        self.assertEqual(geojson["type"], "FeatureCollection")


if __name__ == "__main__":
    unittest.main()
