import os
import sys
import json
import math
import heapq
import time
import random
from typing import Dict, List, Tuple, Optional, Set, Any
from app.schemas.city import IntersectionNode, RoadSegment, CityGraph, SignalState
from app.schemas.traffic import CongestionLevel
from app.schemas.route import (
    RoutePath,
    PathSegmentDetail,
    FindPathResult,
    PathComparison,
    ComparePathResult,
    RandomizeTrafficResult,
)

# Ensure repository root is on sys.path to import routing module
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from routing.city_data import build_cyber_city_network
except ImportError:
    build_cyber_city_network = None

BLOCKAGE_DETOUR_PENALTY_SECONDS = 300.0  # 5 minutes detour penalty for hitting a blocked road


class CityGraphService:
    """
    In-memory deterministic city graph service modeling road networks,
    dynamic congestion weights, closures, signal states, and pathfinding (Dijkstra/A*).
    Backed by Member 4's 20-node, 58-segment Cyber City road network.
    """

    def __init__(self):
        self.nodes: Dict[str, IntersectionNode] = {}
        self.edges: Dict[str, RoadSegment] = {}
        # Adjacency map: node_id -> List[Tuple[neighbor_node_id, road_id]]
        self.adjacency: Dict[str, List[Tuple[str, str]]] = {}
        # Node alias map for cross-compatibility (NODE-01 -> INT-01)
        self.node_aliases: Dict[str, str] = {}
        self.initialize_default_city()

    def _resolve_node_id(self, node_id: str) -> str:
        """Resolve node ID, converting NODE-xx aliases to INT-xx if needed."""
        if not node_id:
            return node_id
        clean = node_id.strip()
        if clean in self.nodes:
            return clean
        if clean in self.node_aliases:
            return self.node_aliases[clean]
        if clean.startswith("NODE-"):
            num = clean.split("-")[-1]
            candidate = f"INT-{num}"
            if candidate in self.nodes:
                return candidate
        return clean

    def initialize_default_city(self):
        """Seed the Cyber City urban road network with 20 intersection nodes and 58 segments."""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self.node_aliases.clear()

        # Build network from Member 4's authoritative city data if available
        if build_cyber_city_network:
            g = build_cyber_city_network()
            for nid, node in g.nodes.items():
                self.nodes[nid] = IntersectionNode(
                    node_id=nid,
                    name=node.name,
                    latitude=node.latitude,
                    longitude=node.longitude,
                    is_signalized=True,
                    signal_state="normal",
                    node_type=node.node_type.value if hasattr(node.node_type, "value") else str(node.node_type),
                    simulated=True
                )
                self.adjacency[nid] = []

            for eid, edge in g.edges.items():
                time_sec = int(edge.base_travel_time_seconds)
                seg = RoadSegment(
                    road_id=eid,
                    name=edge.name,
                    source_node=edge.source,
                    target_node=edge.target,
                    length_meters=edge.length_meters,
                    speed_limit_kmph=edge.speed_limit_kmph,
                    base_travel_time_seconds=max(time_sec, 5),
                    current_congestion_level="free_flow",
                    congestion_weight_multiplier=edge.congestion_factor,
                    is_blocked=edge.is_closed,
                    is_diverted=False
                )
                self.edges[eid] = seg
                self.adjacency[edge.source].append((edge.target, eid))
        elif os.path.exists(os.path.join(ROOT_DIR, "data", "city_graph.json")):
            with open(os.path.join(ROOT_DIR, "data", "city_graph.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            for node_dict in data.get("nodes", []):
                nid = node_dict["node_id"]
                self.nodes[nid] = IntersectionNode(
                    node_id=nid,
                    name=node_dict.get("name", nid),
                    latitude=float(node_dict["latitude"]),
                    longitude=float(node_dict["longitude"]),
                    is_signalized=node_dict.get("is_signalized", True),
                    signal_state=node_dict.get("signal_state", "normal"),
                    node_type=node_dict.get("node_type"),
                    simulated=True
                )
                self.adjacency[nid] = []

            for edge_dict in data.get("edges", []):
                eid = edge_dict["road_id"]
                seg = RoadSegment(
                    road_id=eid,
                    name=edge_dict.get("name", eid),
                    source_node=edge_dict["source_node"],
                    target_node=edge_dict["target_node"],
                    length_meters=float(edge_dict["length_meters"]),
                    speed_limit_kmph=float(edge_dict.get("speed_limit_kmph", 50.0)),
                    base_travel_time_seconds=int(edge_dict.get("base_travel_time_seconds", 30)),
                    current_congestion_level=edge_dict.get("current_congestion_level", "free_flow"),
                    congestion_weight_multiplier=float(edge_dict.get("congestion_weight_multiplier", 1.0)),
                    is_blocked=edge_dict.get("is_blocked", False),
                    is_diverted=edge_dict.get("is_diverted", False)
                )
                self.edges[eid] = seg
                if edge_dict["source_node"] in self.adjacency:
                    self.adjacency[edge_dict["source_node"]].append((edge_dict["target_node"], eid))

        # Build alias mappings: NODE-01 <-> INT-01
        for idx in range(1, 21):
            int_id = f"INT-{idx:02d}"
            node_id = f"NODE-{idx:02d}"
            self.node_aliases[node_id] = int_id
            self.node_aliases[int_id] = int_id

    def get_city_graph(self) -> CityGraph:
        """Return full city graph model."""
        return CityGraph(
            city_name="Cyber City Metro Network",
            nodes=list(self.nodes.values()),
            edges=list(self.edges.values())
        )

    def get_node(self, node_id: str) -> Optional[IntersectionNode]:
        resolved = self._resolve_node_id(node_id)
        return self.nodes.get(resolved)

    def get_edge(self, road_id: str) -> Optional[RoadSegment]:
        if road_id in self.edges:
            return self.edges[road_id]
        # Check forward/return suffix variations
        for suffix in ["A", "B"]:
            cand = f"{road_id}{suffix}"
            if cand in self.edges:
                return self.edges[cand]
        return None

    def update_road_congestion(self, road_id: str, level: str, multiplier: float):
        for candidate in [road_id, f"{road_id}A", f"{road_id}B"]:
            if candidate in self.edges:
                self.edges[candidate].current_congestion_level = level
                self.edges[candidate].congestion_weight_multiplier = max(1.0, multiplier)

    def set_road_blocked(self, road_id: str, is_blocked: bool):
        for candidate in [road_id, f"{road_id}A", f"{road_id}B"]:
            if candidate in self.edges:
                self.edges[candidate].is_blocked = is_blocked

    def set_road_diverted(self, road_id: str, is_diverted: bool):
        for candidate in [road_id, f"{road_id}A", f"{road_id}B"]:
            if candidate in self.edges:
                self.edges[candidate].is_diverted = is_diverted

    def set_signal_priority(self, node_ids: List[str]):
        """Clear all active priority signals and set specified nodes to priority green."""
        for n in self.nodes.values():
            n.signal_state = "normal"
        for raw_id in node_ids:
            nid = self._resolve_node_id(raw_id)
            if nid in self.nodes:
                self.nodes[nid].signal_state = "priority_green"

    def _euclidean_distance(self, n1: str, n2: str) -> float:
        node_a = self.get_node(n1)
        node_b = self.get_node(n2)
        if not node_a or not node_b:
            return 0.0
        # Haversine distance for geometric precision
        r = 6371000.0
        phi1 = math.radians(node_a.latitude)
        phi2 = math.radians(node_b.latitude)
        dphi = math.radians(node_b.latitude - node_a.latitude)
        dlam = math.radians(node_b.longitude - node_a.longitude)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    @property
    def max_speed_mps(self) -> float:
        """Maximum speed limit across all edges in m/s (used for admissible A* heuristic)."""
        if not self.edges:
            return 22.22  # ~80 km/h default
        return max((e.speed_limit_kmph * 1000.0) / 3600.0 for e in self.edges.values())

    def find_shortest_path(
        self,
        origin_node: str,
        destination_node: str,
        avoid_road_ids: Optional[Set[str]] = None,
        algorithm: str = "astar"
    ) -> Optional[RoutePath]:
        """
        Deterministic pathfinding using Dijkstra or A*.
        Avoids roads flagged as blocked or explicitly passed in avoid_road_ids.
        Weights edges by base_travel_time * congestion_weight_multiplier.
        """
        orig = self._resolve_node_id(origin_node)
        dest = self._resolve_node_id(destination_node)

        if orig not in self.nodes or dest not in self.nodes:
            return None

        if orig == dest:
            orig_node = self.nodes.get(orig)
            coords = [{"latitude": orig_node.latitude, "longitude": orig_node.longitude}] if orig_node else []
            return RoutePath(
                node_sequence=[orig],
                road_ids=[],
                estimated_travel_time_seconds=0,
                distance_meters=0.0,
                coordinates=coords
            )

        avoid_roads = set()
        if avoid_road_ids:
            for r in avoid_road_ids:
                avoid_roads.add(r)
                avoid_roads.add(f"{r}A")
                avoid_roads.add(f"{r}B")

        # Priority queue holds (priority, current_cost, current_node, path_nodes, path_roads, total_dist)
        pq: List[Tuple[float, float, str, List[str], List[str], float]] = []
        heapq.heappush(pq, (0.0, 0.0, orig, [orig], [], 0.0))
        best_cost: Dict[str, float] = {orig: 0.0}

        while pq:
            priority, cost, current, path_nodes, path_roads, total_dist = heapq.heappop(pq)

            if current == dest:
                coords = [
                    {"latitude": self.nodes[n].latitude, "longitude": self.nodes[n].longitude}
                    for n in path_nodes
                    if n in self.nodes
                ]
                return RoutePath(
                    node_sequence=path_nodes,
                    road_ids=path_roads,
                    estimated_travel_time_seconds=int(round(cost)),
                    distance_meters=round(total_dist, 1),
                    coordinates=coords
                )

            if cost > best_cost.get(current, float("inf")):
                continue

            for neighbor, road_id in self.adjacency.get(current, []):
                if neighbor in path_nodes:
                    continue

                edge = self.edges.get(road_id)
                if not edge or edge.is_blocked or road_id in avoid_roads:
                    continue

                speed_mps = (edge.speed_limit_kmph * 1000.0) / 3600.0
                edge_travel_time = (edge.length_meters / max(speed_mps, 0.1)) * max(1.0, edge.congestion_weight_multiplier)
                new_cost = cost + edge_travel_time
                new_dist = total_dist + edge.length_meters

                if new_cost < best_cost.get(neighbor, float("inf")):
                    best_cost[neighbor] = new_cost
                    heuristic = 0.0
                    if algorithm.lower() == "astar":
                        heuristic = self._euclidean_distance(neighbor, dest) / self.max_speed_mps
                    new_priority = new_cost + heuristic

                    heapq.heappush(
                        pq,
                        (new_priority, new_cost, neighbor, path_nodes + [neighbor], path_roads + [road_id], new_dist)
                    )

        return None

    # -------------------------------------------------------------------------
    # Member 4 Route Optimization: Find Path (Optimised vs Baseline) & Comparison
    # -------------------------------------------------------------------------

    def find_path(
        self,
        from_node: str,
        to_node: str,
        mode: str = "optimised",
        algorithm: str = "astar",
    ) -> FindPathResult:
        """
        Calculates either:
        1. 'optimised': Cost = travel time (length / speed_limit * congestion_multiplier).
           Blocked roads are strictly excluded.
           Heuristic: admissible straight-line distance / max speed limit.
        2. 'baseline': Shortest path by DISTANCE ONLY, ignoring congestion and closures.
           Then evaluated under actual real conditions (congestion multipliers + detour penalty if blocked).
        """
        orig = self._resolve_node_id(from_node)
        dest = self._resolve_node_id(to_node)

        if orig not in self.nodes:
            raise ValueError(f"Origin node '{from_node}' not found in city graph.")
        if dest not in self.nodes:
            raise ValueError(f"Destination node '{to_node}' not found in city graph.")

        mode_clean = mode.strip().lower()
        algo_clean = algorithm.strip().lower()
        if algo_clean not in ["astar", "dijkstra"]:
            algo_clean = "astar"

        # Edge case: from == to
        if orig == dest:
            n = self.nodes[orig]
            return FindPathResult(
                mode=mode_clean,
                algorithm=algo_clean if mode_clean == "optimised" else "shortest_distance",
                from_node=orig,
                to_node=dest,
                reachable=True,
                total_distance_meters=0.0,
                total_distance_km=0.0,
                estimated_travel_time_seconds=0.0,
                estimated_travel_time_minutes=0.0,
                nodes_explored=1,
                compute_ms=0.05,
                node_ids=[orig],
                road_ids=[],
                coordinates=[{"latitude": n.latitude, "longitude": n.longitude}],
                congested_segments_count=0,
                blocked_roads_hit=0,
                has_blocked_segments=False,
                detour_penalty_seconds=0.0,
                segments=[],
                summary="Origin is destination.",
            )

        t_start = time.perf_counter()

        if mode_clean == "optimised":
            # -------------------------------------------------------------
            # OPTIMISED ROUTE: Minimizes travel time under live conditions
            # Blocked roads are completely excluded.
            # -------------------------------------------------------------
            max_spd = self.max_speed_mps

            # pq entry: (priority, g_cost, counter, current_node, path_nodes, path_roads)
            pq: List[Tuple[float, float, int, str, List[str], List[str]]] = []
            h_start = (self._euclidean_distance(orig, dest) / max_spd) if algo_clean == "astar" else 0.0
            counter = 0
            heapq.heappush(pq, (h_start, 0.0, counter, orig, [orig], []))

            best_g: Dict[str, float] = {orig: 0.0}
            nodes_explored = 0
            found_path_nodes: Optional[List[str]] = None
            found_path_roads: Optional[List[str]] = None

            while pq:
                f, current_g, _, curr, p_nodes, p_roads = heapq.heappop(pq)
                nodes_explored += 1

                if curr == dest:
                    found_path_nodes = p_nodes
                    found_path_roads = p_roads
                    break

                if current_g > best_g.get(curr, float("inf")):
                    continue

                for neighbor, road_id in self.adjacency.get(curr, []):
                    edge = self.edges.get(road_id)
                    if not edge or edge.is_blocked:
                        continue  # Excluded!

                    speed_mps = (edge.speed_limit_kmph * 1000.0) / 3600.0
                    edge_time = (edge.length_meters / max(speed_mps, 0.1)) * max(1.0, edge.congestion_weight_multiplier)
                    new_g = current_g + edge_time

                    if new_g < best_g.get(neighbor, float("inf")):
                        best_g[neighbor] = new_g
                        h = (self._euclidean_distance(neighbor, dest) / max_spd) if algo_clean == "astar" else 0.0
                        counter += 1
                        heapq.heappush(
                            pq,
                            (new_g + h, new_g, counter, neighbor, p_nodes + [neighbor], p_roads + [road_id])
                        )

            compute_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

            if not found_path_nodes:
                return FindPathResult(
                    mode="optimised",
                    algorithm=algo_clean,
                    from_node=orig,
                    to_node=dest,
                    reachable=False,
                    nodes_explored=nodes_explored,
                    compute_ms=compute_ms,
                    summary=f"Destination {dest} is unreachable from {orig} due to active road blockages.",
                )

            # Build detailed segments
            segments: List[PathSegmentDetail] = []
            total_dist = 0.0
            total_time = 0.0
            congested_count = 0

            for rid in (found_path_roads or []):
                e = self.edges[rid]
                speed_mps = (e.speed_limit_kmph * 1000.0) / 3600.0
                seg_time = (e.length_meters / max(speed_mps, 0.1)) * max(1.0, e.congestion_weight_multiplier)
                total_dist += e.length_meters
                total_time += seg_time
                if e.congestion_weight_multiplier > 1.2 or e.current_congestion_level != "free_flow":
                    congested_count += 1

                segments.append(
                    PathSegmentDetail(
                        road_id=e.road_id,
                        name=e.name,
                        from_node=e.source_node,
                        to_node=e.target_node,
                        length_meters=round(e.length_meters, 1),
                        speed_limit_kmph=e.speed_limit_kmph,
                        congestion_level=e.current_congestion_level,
                        congestion_multiplier=round(e.congestion_weight_multiplier, 2),
                        is_blocked=False,
                        travel_time_seconds=round(seg_time, 1),
                    )
                )

            coords = [
                {"latitude": self.nodes[n].latitude, "longitude": self.nodes[n].longitude}
                for n in found_path_nodes
                if n in self.nodes
            ]

            mins = round(total_time / 60.0, 2)
            summary = (
                f"Optimised {algo_clean.upper()} path: {round(total_dist / 1000.0, 2)} km in "
                f"{mins:.1f} min ({round(total_time, 1)}s), {len(segments)} segments."
            )

            return FindPathResult(
                mode="optimised",
                algorithm=algo_clean,
                from_node=orig,
                to_node=dest,
                reachable=True,
                total_distance_meters=round(total_dist, 1),
                total_distance_km=round(total_dist / 1000.0, 2),
                estimated_travel_time_seconds=round(total_time, 1),
                estimated_travel_time_minutes=mins,
                nodes_explored=nodes_explored,
                compute_ms=compute_ms,
                node_ids=found_path_nodes,
                road_ids=found_path_roads or [],
                coordinates=coords,
                congested_segments_count=congested_count,
                blocked_roads_hit=0,
                has_blocked_segments=False,
                detour_penalty_seconds=0.0,
                segments=segments,
                summary=summary,
            )

        else:
            # -------------------------------------------------------------
            # BASELINE ROUTE: Shortest path by DISTANCE ONLY
            # Ignores congestion and blocks during navigation search.
            # Then evaluates the path under real current conditions.
            # -------------------------------------------------------------
            pq_base: List[Tuple[float, float, int, str, List[str], List[str]]] = []
            h_start = self._euclidean_distance(orig, dest)
            counter = 0
            heapq.heappush(pq_base, (h_start, 0.0, counter, orig, [orig], []))

            best_dist: Dict[str, float] = {orig: 0.0}
            nodes_explored = 0
            found_path_nodes: Optional[List[str]] = None
            found_path_roads: Optional[List[str]] = None

            while pq_base:
                f, current_dist, _, curr, p_nodes, p_roads = heapq.heappop(pq_base)
                nodes_explored += 1

                if curr == dest:
                    found_path_nodes = p_nodes
                    found_path_roads = p_roads
                    break

                if current_dist > best_dist.get(curr, float("inf")):
                    continue

                for neighbor, road_id in self.adjacency.get(curr, []):
                    edge = self.edges.get(road_id)
                    if not edge:
                        continue
                    # Distance ONLY weight (ignoring closures and congestion)
                    new_dist = current_dist + edge.length_meters

                    if new_dist < best_dist.get(neighbor, float("inf")):
                        best_dist[neighbor] = new_dist
                        h = self._euclidean_distance(neighbor, dest)
                        counter += 1
                        heapq.heappush(
                            pq_base,
                            (new_dist + h, new_dist, counter, neighbor, p_nodes + [neighbor], p_roads + [road_id])
                        )

            compute_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

            if not found_path_nodes:
                return FindPathResult(
                    mode="baseline",
                    algorithm="shortest_distance",
                    from_node=orig,
                    to_node=dest,
                    reachable=False,
                    nodes_explored=nodes_explored,
                    compute_ms=compute_ms,
                    summary=f"No physical road path connects {orig} and {dest}.",
                )

            # Evaluate baseline path under REAL conditions
            segments: List[PathSegmentDetail] = []
            total_dist = 0.0
            total_time = 0.0
            congested_count = 0
            blocked_count = 0
            detour_penalty = 0.0

            for rid in (found_path_roads or []):
                e = self.edges[rid]
                speed_mps = (e.speed_limit_kmph * 1000.0) / 3600.0
                base_time = (e.length_meters / max(speed_mps, 0.1)) * max(1.0, e.congestion_weight_multiplier)

                if e.is_blocked:
                    blocked_count += 1
                    detour_penalty += BLOCKAGE_DETOUR_PENALTY_SECONDS
                    seg_time = base_time + BLOCKAGE_DETOUR_PENALTY_SECONDS
                    is_seg_blocked = True
                else:
                    seg_time = base_time
                    is_seg_blocked = False

                total_dist += e.length_meters
                total_time += seg_time

                if e.congestion_weight_multiplier > 1.2 or e.current_congestion_level != "free_flow":
                    congested_count += 1

                segments.append(
                    PathSegmentDetail(
                        road_id=e.road_id,
                        name=e.name,
                        from_node=e.source_node,
                        to_node=e.target_node,
                        length_meters=round(e.length_meters, 1),
                        speed_limit_kmph=e.speed_limit_kmph,
                        congestion_level=e.current_congestion_level,
                        congestion_multiplier=round(e.congestion_weight_multiplier, 2),
                        is_blocked=is_seg_blocked,
                        travel_time_seconds=round(seg_time, 1),
                    )
                )

            coords = [
                {"latitude": self.nodes[n].latitude, "longitude": self.nodes[n].longitude}
                for n in found_path_nodes
                if n in self.nodes
            ]

            mins = round(total_time / 60.0, 2)
            summary_parts = [
                f"Baseline shortest-distance route: {round(total_dist / 1000.0, 2)} km in {mins:.1f} min ({round(total_time, 1)}s)"
            ]
            if blocked_count > 0:
                summary_parts.append(f"⚠️ Hits {blocked_count} blocked road(s) (+{int(detour_penalty / 60)} min detour penalty)")
            if congested_count > 0:
                summary_parts.append(f"crosses {congested_count} congested road(s)")

            return FindPathResult(
                mode="baseline",
                algorithm="shortest_distance",
                from_node=orig,
                to_node=dest,
                reachable=True,
                total_distance_meters=round(total_dist, 1),
                total_distance_km=round(total_dist / 1000.0, 2),
                estimated_travel_time_seconds=round(total_time, 1),
                estimated_travel_time_minutes=mins,
                nodes_explored=nodes_explored,
                compute_ms=compute_ms,
                node_ids=found_path_nodes,
                road_ids=found_path_roads or [],
                coordinates=coords,
                congested_segments_count=congested_count,
                blocked_roads_hit=blocked_count,
                has_blocked_segments=(blocked_count > 0),
                detour_penalty_seconds=round(detour_penalty, 1),
                segments=segments,
                summary=". ".join(summary_parts) + ".",
            )

    def compare_paths(
        self,
        from_node: str,
        to_node: str,
        algorithm: str = "astar",
    ) -> ComparePathResult:
        """
        Calculates both Optimised and Baseline routes, returning both plus side-by-side comparison.
        """
        orig = self._resolve_node_id(from_node)
        dest = self._resolve_node_id(to_node)

        opt_result = self.find_path(orig, dest, mode="optimised", algorithm=algorithm)
        base_result = self.find_path(orig, dest, mode="baseline", algorithm=algorithm)

        if not opt_result.reachable:
            return ComparePathResult(
                from_node=orig,
                to_node=dest,
                algorithm=algorithm,
                reachable=False,
                optimised=opt_result,
                baseline=base_result,
                comparison=None,
                error_message=f"No viable open path from {orig} to {dest} (blocked roads disconnect the network).",
            )

        time_saved_s = max(0.0, base_result.estimated_travel_time_seconds - opt_result.estimated_travel_time_seconds)
        time_saved_m = round(time_saved_s / 60.0, 2)
        base_time = max(1.0, base_result.estimated_travel_time_seconds)
        time_saved_pct = round((time_saved_s / base_time) * 100.0, 1)

        dist_diff_m = round(opt_result.total_distance_meters - base_result.total_distance_meters, 1)
        dist_diff_km = round(dist_diff_m / 1000.0, 2)

        congested_avoided = max(0, base_result.congested_segments_count - opt_result.congested_segments_count)
        blocked_avoided = base_result.blocked_roads_hit

        # Check if identical routes
        is_same_route = (opt_result.node_ids == base_result.node_ids)
        if is_same_route and time_saved_s < 1.0 and base_result.blocked_roads_hit == 0:
            summary = "Optimised and baseline routes are identical: traffic is free-flowing with zero closures on this corridor."
        else:
            parts = []
            if time_saved_m >= 0.1:
                parts.append(f"Optimised route is {time_saved_m:.1f} min ({time_saved_pct:.0f}%) faster")
            elif time_saved_s > 0.5:
                parts.append(f"Optimised route is {time_saved_s:.0f}s faster")
            else:
                parts.append("Optimised route travel time is comparable to baseline")

            if blocked_avoided > 0:
                parts.append(f"avoids {blocked_avoided} blocked road{'s' if blocked_avoided != 1 else ''} (+{int(blocked_avoided * BLOCKAGE_DETOUR_PENALTY_SECONDS / 60)}m detour penalty on baseline)")

            if congested_avoided > 0:
                parts.append(f"bypasses {congested_avoided} congested road segment{'s' if congested_avoided != 1 else ''}")

            summary = ". ".join(parts) + "."

        comparison = PathComparison(
            time_saved_seconds=round(time_saved_s, 1),
            time_saved_minutes=time_saved_m,
            time_saved_percent=time_saved_pct,
            distance_difference_meters=dist_diff_m,
            distance_difference_km=dist_diff_km,
            congested_segments_avoided=congested_avoided,
            blocked_roads_avoided=blocked_avoided,
            summary=summary,
        )

        return ComparePathResult(
            from_node=orig,
            to_node=dest,
            algorithm=algorithm,
            reachable=True,
            optimised=opt_result,
            baseline=base_result,
            comparison=comparison,
        )

    def randomize_traffic(
        self,
        seed: Optional[int] = None,
        min_blocks: int = 2,
        max_blocks: int = 4,
    ) -> Dict[str, Any]:
        """
        Sets randomized congestion levels on all road segments and randomly blocks 2-4 roads.
        Deterministic when seed is provided.
        """
        rng = random.Random(seed) if seed is not None else random.Random()

        # Reset all closures first
        for edge in self.edges.values():
            edge.is_blocked = False

        # Assign randomized congestion
        congested_count = 0
        for edge in self.edges.values():
            r = rng.random()
            if r < 0.40:
                level = "free_flow"
                mult = 1.0
            elif r < 0.65:
                level = "moderate"
                mult = 1.6
                congested_count += 1
            elif r < 0.85:
                level = "heavy"
                mult = 2.5
                congested_count += 1
            else:
                level = "severe"
                mult = 3.5
                congested_count += 1

            edge.current_congestion_level = level
            edge.congestion_weight_multiplier = mult

        # Randomly select 2-4 roads to block
        k = rng.randint(min_blocks, max_blocks)
        all_roads = list(self.edges.keys())
        blocked = rng.sample(all_roads, min(k, len(all_roads)))

        for r in blocked:
            self.set_road_blocked(r, True)

        return {
            "status": "success",
            "seed": seed,
            "blocked_roads": blocked,
            "congested_roads_count": congested_count,
            "total_roads": len(self.edges),
        }


city_graph_service = CityGraphService()
