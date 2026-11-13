import os
import sys
import json
import math
import heapq
from typing import Dict, List, Tuple, Optional, Set, Any
from app.schemas.city import IntersectionNode, RoadSegment, CityGraph, SignalState
from app.schemas.traffic import CongestionLevel
from app.schemas.route import RoutePath

# Ensure repository root is on sys.path to import routing module
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from routing.city_data import build_cyber_city_network
except ImportError:
    build_cyber_city_network = None


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
        """Seed the Cyber City urban road network with real OpenStreetMap road graph."""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self.node_aliases.clear()

        json_path = os.path.join(ROOT_DIR, "data", "city_graph.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for node_dict in data.get("nodes", []):
                nid = node_dict.get("node_id") or node_dict.get("id")
                self.nodes[nid] = IntersectionNode(
                    node_id=nid,
                    name=node_dict.get("name", nid),
                    latitude=float(node_dict.get("latitude", node_dict.get("lat"))),
                    longitude=float(node_dict.get("longitude", node_dict.get("lon"))),
                    is_signalized=node_dict.get("is_signalized", True),
                    signal_state=node_dict.get("signal_state", "normal"),
                    node_type=node_dict.get("node_type"),
                    simulated=True
                )
                self.adjacency[nid] = []

            for edge_dict in data.get("edges", []):
                eid = edge_dict.get("road_id") or edge_dict.get("id")
                source = edge_dict.get("source_node") or edge_dict.get("source")
                target = edge_dict.get("target_node") or edge_dict.get("target")
                length_m = float(edge_dict.get("length_meters") or edge_dict.get("length_m", 100.0))
                time_sec = int(edge_dict.get("base_travel_time_seconds", max(int(length_m / (edge_dict.get("speed_limit_kmph", 50.0) / 3.6)), 5)))

                seg = RoadSegment(
                    road_id=eid,
                    name=edge_dict.get("name", eid),
                    source_node=source,
                    target_node=target,
                    source=source,
                    target=target,
                    length_meters=length_m,
                    length_m=length_m,
                    speed_limit_kmph=float(edge_dict.get("speed_limit_kmph", 50.0)),
                    base_travel_time_seconds=max(time_sec, 5),
                    current_congestion_level=edge_dict.get("current_congestion_level", "free_flow"),
                    congestion_weight_multiplier=float(edge_dict.get("congestion_weight_multiplier", edge_dict.get("congestion_factor", 1.0))),
                    is_blocked=edge_dict.get("is_blocked", False),
                    is_diverted=edge_dict.get("is_diverted", False),
                    geometry=edge_dict.get("geometry", [])
                )
                self.edges[eid] = seg
                if source not in self.adjacency:
                    self.adjacency[source] = []
                self.adjacency[source].append((target, eid))
        elif build_cyber_city_network:
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
                    source=edge.source,
                    target=edge.target,
                    length_meters=edge.length_meters,
                    length_m=edge.length_meters,
                    speed_limit_kmph=edge.speed_limit_kmph,
                    base_travel_time_seconds=max(time_sec, 5),
                    current_congestion_level="free_flow",
                    congestion_weight_multiplier=edge.congestion_factor,
                    is_blocked=edge.is_closed,
                    is_diverted=False,
                    geometry=[]
                )
                self.edges[eid] = seg
                if edge.source not in self.adjacency:
                    self.adjacency[edge.source] = []
                self.adjacency[edge.source].append((edge.target, eid))

        # Build alias mappings: NODE-01 <-> INT-01
        for idx in range(1, 21):
            int_id = f"INT-{idx:02d}"
            node_id = f"NODE-{idx:02d}"
            self.node_aliases[node_id] = int_id
            self.node_aliases[int_id] = int_id

        # Calculate max speed across graph for admissible A* heuristic
        max_speed = max((e.speed_limit_kmph for e in self.edges.values()), default=60.0)
        self.max_speed_mps = (max_speed * 1000.0 / 3600.0) if max_speed > 0 else (60.0 / 3.6)

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

    def _build_geometry_coordinates(self, path_nodes: List[str], path_roads: List[str]) -> List[List[float]]:
        """Extract ordered [lat, lon] coordinates along traversed edges respecting traversal direction."""
        coords: List[List[float]] = []
        for i, r_id in enumerate(path_roads):
            u_id = path_nodes[i]
            v_id = path_nodes[i + 1]
            edge = self.edges.get(r_id)
            u_node = self.nodes.get(u_id)
            v_node = self.nodes.get(v_id)

            edge_geom = [list(pt) for pt in edge.geometry] if edge and edge.geometry else []
            if edge_geom:
                if u_node:
                    d_start = (edge_geom[0][0] - u_node.latitude) ** 2 + (edge_geom[0][1] - u_node.longitude) ** 2
                    d_end = (edge_geom[-1][0] - u_node.latitude) ** 2 + (edge_geom[-1][1] - u_node.longitude) ** 2
                    if d_end < d_start:
                        edge_geom.reverse()
                for pt in edge_geom:
                    if not coords or abs(coords[-1][0] - pt[0]) > 1e-6 or abs(coords[-1][1] - pt[1]) > 1e-6:
                        coords.append([pt[0], pt[1]])
            else:
                if u_node and (not coords or abs(coords[-1][0] - u_node.latitude) > 1e-6 or abs(coords[-1][1] - u_node.longitude) > 1e-6):
                    coords.append([u_node.latitude, u_node.longitude])
                if v_node:
                    coords.append([v_node.latitude, v_node.longitude])

        if not coords and path_nodes:
            for n in path_nodes:
                if n in self.nodes:
                    coords.append([self.nodes[n].latitude, self.nodes[n].longitude])
        return coords

    def find_shortest_distance_path(self, origin_node: str, destination_node: str) -> Optional[Tuple[List[str], List[str], float, int]]:
        """
        Baseline shortest path by DISTANCE ONLY, completely ignoring congestion and road closures.
        What a basic navigator without live traffic data does.
        Returns: (path_nodes, path_roads, total_distance_meters, nodes_explored)
        """
        orig = self._resolve_node_id(origin_node)
        dest = self._resolve_node_id(destination_node)

        if orig not in self.nodes or dest not in self.nodes:
            return None

        if orig == dest:
            return ([orig], [], 0.0, 1)

        pq: List[Tuple[float, float, str, List[str], List[str]]] = []
        heapq.heappush(pq, (0.0, 0.0, orig, [orig], []))
        best_dist: Dict[str, float] = {orig: 0.0}
        nodes_explored = 0

        while pq:
            _, dist, current, path_nodes, path_roads = heapq.heappop(pq)
            nodes_explored += 1

            if current == dest:
                return (path_nodes, path_roads, dist, nodes_explored)

            if dist > best_dist.get(current, float("inf")):
                continue

            for neighbor, road_id in self.adjacency.get(current, []):
                if neighbor in path_nodes:
                    continue
                edge = self.edges.get(road_id)
                if not edge:
                    continue

                new_dist = dist + edge.length_meters
                if new_dist < best_dist.get(neighbor, float("inf")):
                    best_dist[neighbor] = new_dist
                    heuristic = self._euclidean_distance(neighbor, dest)
                    heapq.heappush(
                        pq,
                        (new_dist + heuristic, new_dist, neighbor, path_nodes + [neighbor], path_roads + [road_id])
                    )

        return None

    def find_shortest_path_with_stats(
        self,
        origin_node: str,
        destination_node: str,
        avoid_road_ids: Optional[Set[str]] = None,
        algorithm: str = "astar",
        allow_destination_access: bool = False
    ) -> Optional[Tuple[List[str], List[str], float, float, int]]:
        """
        Optimised pathfinding using travel time as cost (length / speed_limit x congestion_multiplier).
        Excludes blocked roads and specified avoid_road_ids.
        A* uses admissible heuristic: straight_line_distance / max_speed_on_graph.
        Returns: (path_nodes, path_roads, total_travel_time_seconds, total_distance_meters, nodes_explored)
        """
        orig = self._resolve_node_id(origin_node)
        dest = self._resolve_node_id(destination_node)

        if orig not in self.nodes or dest not in self.nodes:
            return None

        if orig == dest:
            return ([orig], [], 0.0, 0.0, 1)

        avoid_roads = set()
        if avoid_road_ids:
            for r in avoid_road_ids:
                avoid_roads.add(r)
                avoid_roads.add(f"{r}A")
                avoid_roads.add(f"{r}B")

        pq: List[Tuple[float, float, str, List[str], List[str], float]] = []
        heapq.heappush(pq, (0.0, 0.0, orig, [orig], [], 0.0))
        best_cost: Dict[str, float] = {orig: 0.0}
        nodes_explored = 0

        while pq:
            priority, cost, current, path_nodes, path_roads, total_dist = heapq.heappop(pq)
            nodes_explored += 1

            if current == dest:
                return (path_nodes, path_roads, cost, total_dist, nodes_explored)

            if cost > best_cost.get(current, float("inf")):
                continue

            for neighbor, road_id in self.adjacency.get(current, []):
                if neighbor in path_nodes:
                    continue

                edge = self.edges.get(road_id)
                if not edge:
                    continue

                is_dest_step = (neighbor == dest)
                is_avoided = (edge.is_blocked or road_id in avoid_roads)
                if is_avoided and not (allow_destination_access and is_dest_step):
                    continue

                speed_mps = (edge.speed_limit_kmph * 1000.0 / 3600.0) if edge.speed_limit_kmph > 0 else 13.89
                base_time = edge.length_meters / speed_mps
                edge_travel_time = base_time * max(1.0, edge.congestion_weight_multiplier)
                new_cost = cost + edge_travel_time
                new_dist = total_dist + edge.length_meters

                if new_cost < best_cost.get(neighbor, float("inf")):
                    best_cost[neighbor] = new_cost
                    heuristic = 0.0
                    if algorithm.lower() == "astar":
                        max_speed = getattr(self, "max_speed_mps", 22.22)
                        heuristic = self._euclidean_distance(neighbor, dest) / max_speed
                    new_priority = new_cost + heuristic

                    heapq.heappush(
                        pq,
                        (new_priority, new_cost, neighbor, path_nodes + [neighbor], path_roads + [road_id], new_dist)
                    )

        return None

    def randomize_traffic_conditions(self, seed: Optional[int] = None, num_blocked: Optional[int] = None) -> Tuple[int, List[str], int, List[Dict[str, Any]]]:
        """
        Randomize congestion levels and block 2-4 roads for realistic comparison.
        Returns: (seed_used, blocked_road_ids, congested_count, congested_roads_details)
        """
        import random
        if seed is None:
            seed = random.randint(1000, 999999)
        rng = random.Random(seed)

        if num_blocked is None:
            num_blocked = rng.randint(2, 4)

        edge_list = list(self.edges.values())
        # Reset all edges first
        for edge in edge_list:
            edge.is_blocked = False
            edge.is_diverted = False
            edge.current_congestion_level = "free_flow"
            edge.congestion_weight_multiplier = 1.0

        levels = [
            ("free_flow", 1.0),
            ("moderate", 1.5),
            ("heavy", 2.2),
            ("severe", 3.0),
        ]
        congested_count = 0
        congested_details = []
        for edge in edge_list:
            level, mult = rng.choices(levels, weights=[0.45, 0.25, 0.18, 0.12])[0]
            edge.current_congestion_level = level
            edge.congestion_weight_multiplier = mult
            if level != "free_flow":
                congested_count += 1
                congested_details.append({
                    "road_id": edge.road_id,
                    "level": level,
                    "multiplier": mult,
                })

        # Pick roads to block (ensure we pick actual road IDs)
        candidate_edges = [e for e in edge_list if e.source_node != e.target_node]
        blocked_edges = rng.sample(candidate_edges, min(num_blocked, len(candidate_edges)))
        blocked_ids = []
        for e in blocked_edges:
            e.is_blocked = True
            blocked_ids.append(e.road_id)

        return (seed, blocked_ids, congested_count, congested_details)

    def congest_path(self, from_node: str, to_node: str) -> Tuple[List[str], Optional[str]]:
        """
        Demo scenario helper: "Congest the baseline route"
        Applies heavy congestion (2.5x - 3.5x) and blocks one road strictly along
        the distance-shortest baseline path between from_node and to_node.
        Returns: (congested_road_ids, blocked_road_id)
        """
        res = self.find_shortest_distance_path(from_node, to_node)
        if not res or not res[1]:
            return ([], None)

        _, path_roads, _, _ = res
        congested_roads = []
        blocked_road = None

        # Choose one road in the middle of the path to block if path has >= 2 roads, else the only road
        block_idx = max(0, len(path_roads) // 2) if len(path_roads) > 1 else 0

        for idx, road_id in enumerate(path_roads):
            edge = self.get_edge(road_id)
            if not edge:
                continue
            if idx == block_idx:
                edge.is_blocked = True
                edge.current_congestion_level = "severe"
                edge.congestion_weight_multiplier = 3.5
                blocked_road = edge.road_id
            else:
                edge.is_blocked = False
                edge.current_congestion_level = "heavy"
                edge.congestion_weight_multiplier = 2.5
            congested_roads.append(edge.road_id)

        return (congested_roads, blocked_road)

    def find_shortest_path(
        self,
        origin_node: str,
        destination_node: str,
        avoid_road_ids: Optional[Set[str]] = None,
        algorithm: str = "astar",
        allow_destination_access: bool = True
    ) -> Optional[RoutePath]:
        """
        Deterministic pathfinding using Dijkstra or A*.
        Avoids roads flagged as blocked or explicitly passed in avoid_road_ids.
        Weights edges by travel time: length / speed_limit x congestion_weight_multiplier.
        A* uses admissible heuristic: straight_line_distance / max_speed_on_graph.
        Blocked roads are excluded for passing traffic, but reachable as a destination when allow_destination_access=True.
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
                coords = []
                for i, r_id in enumerate(path_roads):
                    u_id = path_nodes[i]
                    v_id = path_nodes[i + 1]
                    edge = self.edges.get(r_id)
                    u_node = self.nodes.get(u_id)
                    v_node = self.nodes.get(v_id)

                    edge_geom = [list(pt) for pt in edge.geometry] if edge and edge.geometry else []
                    if edge_geom:
                        # Ensure geometry orientation matches traversal u_id -> v_id
                        if u_node:
                            d_start = (edge_geom[0][0] - u_node.latitude) ** 2 + (edge_geom[0][1] - u_node.longitude) ** 2
                            d_end = (edge_geom[-1][0] - u_node.latitude) ** 2 + (edge_geom[-1][1] - u_node.longitude) ** 2
                            if d_end < d_start:
                                edge_geom.reverse()
                        for pt in edge_geom:
                            if not coords or abs(coords[-1]["latitude"] - pt[0]) > 1e-6 or abs(coords[-1]["longitude"] - pt[1]) > 1e-6:
                                coords.append({"latitude": pt[0], "longitude": pt[1]})
                    else:
                        if u_node and (not coords or abs(coords[-1]["latitude"] - u_node.latitude) > 1e-6 or abs(coords[-1]["longitude"] - u_node.longitude) > 1e-6):
                            coords.append({"latitude": u_node.latitude, "longitude": u_node.longitude})
                        if v_node:
                            coords.append({"latitude": v_node.latitude, "longitude": v_node.longitude})

                if not coords:
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
                if not edge:
                    continue

                is_dest_step = (neighbor == dest)
                is_avoided = (edge.is_blocked or road_id in avoid_roads)
                if is_avoided and not (allow_destination_access and is_dest_step):
                    continue

                # Cost: length / speed limit x congestion multiplier
                speed_mps = (edge.speed_limit_kmph * 1000.0 / 3600.0) if edge.speed_limit_kmph > 0 else 13.89
                base_time = edge.length_meters / speed_mps
                edge_travel_time = base_time * max(1.0, edge.congestion_weight_multiplier)
                new_cost = cost + edge_travel_time
                new_dist = total_dist + edge.length_meters

                if new_cost < best_cost.get(neighbor, float("inf")):
                    best_cost[neighbor] = new_cost
                    heuristic = 0.0
                    if algorithm.lower() == "astar":
                        # Admissible heuristic: straight-line distance / max speed on graph
                        max_speed = getattr(self, "max_speed_mps", 22.22)
                        heuristic = self._euclidean_distance(neighbor, dest) / max_speed
                    new_priority = new_cost + heuristic

                    heapq.heappush(
                        pq,
                        (new_priority, new_cost, neighbor, path_nodes + [neighbor], path_roads + [road_id], new_dist)
                    )

        return None


city_graph_service = CityGraphService()
