import os
import sys
import json
import math
import heapq
from typing import Dict, List, Tuple, Optional, Set
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

                edge_travel_time = edge.base_travel_time_seconds * edge.congestion_weight_multiplier
                new_cost = cost + edge_travel_time
                new_dist = total_dist + edge.length_meters

                if new_cost < best_cost.get(neighbor, float("inf")):
                    best_cost[neighbor] = new_cost
                    heuristic = 0.0
                    if algorithm.lower() == "astar":
                        # Assume emergency speed ~16.67 m/s (60 km/h)
                        heuristic = self._euclidean_distance(neighbor, dest) / 16.67
                    new_priority = new_cost + heuristic

                    heapq.heappush(
                        pq,
                        (new_priority, new_cost, neighbor, path_nodes + [neighbor], path_roads + [road_id], new_dist)
                    )

        return None


city_graph_service = CityGraphService()
