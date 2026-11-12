import math
import heapq
from typing import Dict, List, Tuple, Optional, Set
from app.schemas.city import IntersectionNode, RoadSegment, CityGraph, SignalState
from app.schemas.traffic import CongestionLevel
from app.schemas.route import RoutePath


class CityGraphService:
    """
    In-memory deterministic city graph service modeling road networks,
    dynamic congestion weights, closures, signal states, and pathfinding (Dijkstra/A*).
    """

    def __init__(self):
        self.nodes: Dict[str, IntersectionNode] = {}
        self.edges: Dict[str, RoadSegment] = {}
        # Adjacency map: node_id -> List[Tuple[neighbor_node_id, road_id]]
        self.adjacency: Dict[str, List[Tuple[str, str]]] = {}
        self.initialize_default_city()

    def initialize_default_city(self):
        """Seed a deterministic 20-node urban grid network with 32 road segments."""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()

        # Grid of 20 intersection nodes (4 rows x 5 columns)
        base_lat = 17.3850
        base_lon = 78.4867
        lat_step = 0.0050  # ~550m
        lon_step = 0.0050  # ~530m

        node_labels = [
            "North Gate", "Hospital Junction", "Market Cross", "Financial Hub", "Tech Park",
            "University Rd", "Central Plaza", "Civic Center", "Station Square", "East Terminal",
            "West End", "Commercial Strip", "Metro Depot", "Industrial Belt", "South Suburb",
            "Riverfront West", "Harbor View", "Parkway Central", "Bridge Crossing", "Outer Bypass"
        ]

        idx = 1
        for r in range(4):
            for c in range(5):
                node_id = f"NODE-{idx:02d}"
                lat = round(base_lat + (r * lat_step), 4)
                lon = round(base_lon + (c * lon_step), 4)
                name = node_labels[idx - 1] if idx - 1 < len(node_labels) else f"Junction {idx}"
                self.nodes[node_id] = IntersectionNode(
                    node_id=node_id,
                    name=name,
                    latitude=lat,
                    longitude=lon,
                    is_signalized=True,
                    signal_state=SignalState.NORMAL
                )
                self.adjacency[node_id] = []
                idx += 1

        # Seed horizontal and vertical road segments
        road_count = 1

        def add_bidirectional_segment(src: str, dst: str, name: str, length_m: float, speed_kmph: float = 50.0):
            nonlocal road_count
            time_sec = int(length_m / (speed_kmph * (1000 / 3600)))
            
            # Forward edge
            fwd_id = f"ROAD-{road_count:02d}"
            fwd_edge = RoadSegment(
                road_id=fwd_id,
                name=name,
                source_node=src,
                target_node=dst,
                length_meters=length_m,
                speed_limit_kmph=speed_kmph,
                base_travel_time_seconds=max(time_sec, 10),
                current_congestion_level=CongestionLevel.FREE_FLOW,
                congestion_weight_multiplier=1.0,
                is_blocked=False,
                is_diverted=False
            )
            self.edges[fwd_id] = fwd_edge
            self.adjacency[src].append((dst, fwd_id))
            road_count += 1

            # Reverse edge
            rev_id = f"ROAD-{road_count:02d}"
            rev_edge = RoadSegment(
                road_id=rev_id,
                name=f"{name} (Return)",
                source_node=dst,
                target_node=src,
                length_meters=length_m,
                speed_limit_kmph=speed_kmph,
                base_travel_time_seconds=max(time_sec, 10),
                current_congestion_level=CongestionLevel.FREE_FLOW,
                congestion_weight_multiplier=1.0,
                is_blocked=False,
                is_diverted=False
            )
            self.edges[rev_id] = rev_edge
            self.adjacency[dst].append((src, rev_id))
            road_count += 1

        # Connect grid horizontally
        for r in range(4):
            for c in range(4):
                n1 = f"NODE-{(r * 5 + c + 1):02d}"
                n2 = f"NODE-{(r * 5 + c + 2):02d}"
                add_bidirectional_segment(n1, n2, f"Corridor-{r+1} Segment {c+1}", 550.0, 50.0)

        # Connect grid vertically
        for r in range(3):
            for c in range(5):
                n1 = f"NODE-{(r * 5 + c + 1):02d}"
                n2 = f"NODE-{((r + 1) * 5 + c + 1):02d}"
                add_bidirectional_segment(n1, n2, f"Avenue-{c+1} Segment {r+1}", 500.0, 45.0)

    def get_city_graph(self) -> CityGraph:
        """Return full city graph model."""
        return CityGraph(
            city_name="Metropolis SmartGrid",
            nodes=list(self.nodes.values()),
            edges=list(self.edges.values())
        )

    def get_node(self, node_id: str) -> Optional[IntersectionNode]:
        return self.nodes.get(node_id)

    def get_edge(self, road_id: str) -> Optional[RoadSegment]:
        return self.edges.get(road_id)

    def update_road_congestion(self, road_id: str, level: CongestionLevel, multiplier: float):
        if road_id in self.edges:
            self.edges[road_id].current_congestion_level = level
            self.edges[road_id].congestion_weight_multiplier = max(1.0, multiplier)

    def set_road_blocked(self, road_id: str, is_blocked: bool):
        if road_id in self.edges:
            self.edges[road_id].is_blocked = is_blocked

    def set_road_diverted(self, road_id: str, is_diverted: bool):
        if road_id in self.edges:
            self.edges[road_id].is_diverted = is_diverted

    def set_signal_priority(self, node_ids: List[str]):
        """Clear all active priority signals and set specified nodes to priority green."""
        for n in self.nodes.values():
            n.signal_state = SignalState.NORMAL
        for nid in node_ids:
            if nid in self.nodes:
                self.nodes[nid].signal_state = SignalState.PRIORITY_GREEN

    def _euclidean_distance(self, n1: str, n2: str) -> float:
        node_a = self.nodes.get(n1)
        node_b = self.nodes.get(n2)
        if not node_a or not node_b:
            return 0.0
        # Approximate meter distance from coordinate degrees
        dx = (node_a.longitude - node_b.longitude) * 111320 * math.cos(math.radians(node_a.latitude))
        dy = (node_a.latitude - node_b.latitude) * 110540
        return math.sqrt(dx * dx + dy * dy)

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
        if origin_node not in self.nodes or destination_node not in self.nodes:
            return None

        if origin_node == destination_node:
            return RoutePath(
                node_sequence=[origin_node],
                road_ids=[],
                estimated_travel_time_seconds=0,
                distance_meters=0.0
            )

        avoid_roads = avoid_road_ids or set()

        # Priority queue holds (priority, current_cost, current_node, path_nodes, path_roads, total_dist)
        pq: List[Tuple[float, float, str, List[str], List[str], float]] = []
        heapq.heappush(pq, (0.0, 0.0, origin_node, [origin_node], [], 0.0))
        best_cost: Dict[str, float] = {origin_node: 0.0}

        while pq:
            priority, cost, current, path_nodes, path_roads, total_dist = heapq.heappop(pq)

            if current == destination_node:
                return RoutePath(
                    node_sequence=path_nodes,
                    road_ids=path_roads,
                    estimated_travel_time_seconds=int(round(cost)),
                    distance_meters=round(total_dist, 1)
                )

            if cost > best_cost.get(current, float("inf")):
                continue

            for neighbor, road_id in self.adjacency.get(current, []):
                if neighbor in path_nodes:  # Avoid simple cycles
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
                        # Estimated travel time in seconds assuming max speed 60 km/h (16.67 m/s)
                        heuristic = self._euclidean_distance(neighbor, destination_node) / 16.67
                    new_priority = new_cost + heuristic

                    heapq.heappush(
                        pq,
                        (new_priority, new_cost, neighbor, path_nodes + [neighbor], path_roads + [road_id], new_dist)
                    )

        return None


city_graph_service = CityGraphService()
