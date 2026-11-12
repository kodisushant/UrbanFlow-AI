"""
UrbanFlow AI - City Road Network Graph Representation
Member 4: Road Network, Emergency Routing & Traffic Diversion
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any, Set
from .models import Node, Edge, NodeType, SignalState, finite_or_none, RouteContext


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth (in meters).
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


class CityGraph:
    """
    Weighted directed graph modeling the urban road network.
    Nodes = Intersections & Key Facilities (Hospitals, Fire/Police Stations).
    Edges = Road segments with physical geometry, speed limit, lanes, congestion, and closure status.
    """

    def __init__(self, name: str = "UrbanFlow City Network"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}  # Indexed by road_id
        self.adjacency: Dict[str, List[Edge]] = {}  # source_node_id -> outgoing edges
        self.reverse_adjacency: Dict[str, List[Edge]] = {}  # target_node_id -> incoming edges
        self.pair_map: Dict[str, str] = {}  # road_id -> reverse road_id (if bidirectional)

    # -------------------------------------------------------------------------
    # Graph Construction & Geometric Validation
    # -------------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = []
        if node.node_id not in self.reverse_adjacency:
            self.reverse_adjacency[node.node_id] = []

    def add_edge(self, edge: Edge, validate_geometry: bool = True) -> None:
        """
        Add a directed edge.
        Validates that road length is physically admissible: length_meters >= 0.999 * haversine.
        """
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Both source '{edge.source}' and target '{edge.target}' must exist in nodes.")

        if validate_geometry:
            u = self.nodes[edge.source]
            v = self.nodes[edge.target]
            h_dist = haversine_distance_meters(u.latitude, u.longitude, v.latitude, v.longitude)
            if edge.length_meters < 0.999 * h_dist:
                raise ValueError(
                    f"Edge '{edge.road_id}' length ({edge.length_meters:.1f} m) is shorter than Euclidean "
                    f"haversine distance ({h_dist:.1f} m) between '{edge.source}' and '{edge.target}'. "
                    f"Road segment length must be >= 0.999 * haversine."
                )

        self.edges[edge.road_id] = edge
        self.adjacency[edge.source].append(edge)
        self.reverse_adjacency[edge.target].append(edge)

    def add_bidirectional_road(
        self,
        forward_id: str,
        reverse_id: str,
        node_a: str,
        node_b: str,
        name: str,
        length_meters: float,
        speed_limit_kmph: float,
        lanes: int = 2,
        pair_id: Optional[str] = None,
    ) -> Tuple[Edge, Edge]:
        """Convenience method to add a two-way street connecting two intersections."""
        pid = pair_id or f"PAIR-{forward_id[:7]}"
        forward_edge = Edge(
            road_id=forward_id,
            source=node_a,
            target=node_b,
            name=name,
            length_meters=length_meters,
            speed_limit_kmph=speed_limit_kmph,
            lanes=lanes,
            is_one_way=False,
            pair_id=pid,
            direction="forward",
        )
        reverse_edge = Edge(
            road_id=reverse_id,
            source=node_b,
            target=node_a,
            name=name,
            length_meters=length_meters,
            speed_limit_kmph=speed_limit_kmph,
            lanes=lanes,
            is_one_way=False,
            pair_id=pid,
            direction="reverse",
        )
        self.add_edge(forward_edge)
        self.add_edge(reverse_edge)
        self.pair_map[forward_id] = reverse_id
        self.pair_map[reverse_id] = forward_id
        return forward_edge, reverse_edge

    def validate(self) -> None:
        """Validates all nodes and edges for geometric consistency."""
        for edge in self.edges.values():
            u = self.nodes[edge.source]
            v = self.nodes[edge.target]
            h_dist = haversine_distance_meters(u.latitude, u.longitude, v.latitude, v.longitude)
            if edge.length_meters < 0.999 * h_dist:
                raise ValueError(
                    f"Validation failed: Edge '{edge.road_id}' length {edge.length_meters:.1f}m < "
                    f"0.999 * haversine {h_dist:.1f}m."
                )

    def get_reverse_edge(self, road_id: str) -> Optional[Edge]:
        """Returns the reverse edge object of a bidirectional road, if present."""
        rev_id = self.pair_map.get(road_id)
        if rev_id and rev_id in self.edges:
            return self.edges[rev_id]
        return None

    # -------------------------------------------------------------------------
    # Spatial Lookups & Metrics
    # -------------------------------------------------------------------------

    def find_nearest_node(self, latitude: float, longitude: float) -> Optional[Node]:
        """Find the nearest intersection or facility to a given coordinate."""
        if not self.nodes:
            return None
        nearest = None
        min_dist = float("inf")
        for node in self.nodes.values():
            dist = haversine_distance_meters(latitude, longitude, node.latitude, node.longitude)
            if dist < min_dist:
                min_dist = dist
                nearest = node
        return nearest

    def distance_between_nodes(self, node_a_id: str, node_b_id: str) -> float:
        """Great-circle distance in meters between two nodes."""
        node_a = self.nodes[node_a_id]
        node_b = self.nodes[node_b_id]
        return haversine_distance_meters(node_a.latitude, node_a.longitude, node_b.latitude, node_b.longitude)

    # -------------------------------------------------------------------------
    # Closures, Partial Lane Reductions & Congestion Updates
    # -------------------------------------------------------------------------

    def close_road(
        self,
        road_id: str,
        reason: str = "accident_blockage",
        direction: str = "both",
    ) -> List[str]:
        """
        Close road segment(s).
        Parameters:
            road_id: ID of the primary road segment to close.
            reason: Reason for closure (e.g. 'multi_vehicle_collision').
            direction: 'forward' (only road_id) or 'both' (road_id and its reverse pair).
        Returns:
            List of closed road IDs.
        """
        closed_ids: List[str] = []
        if road_id in self.edges:
            self.edges[road_id].is_closed = True
            self.edges[road_id].closure_reason = reason
            closed_ids.append(road_id)

        if direction.lower() == "both":
            rev_edge = self.get_reverse_edge(road_id)
            if rev_edge and not rev_edge.is_closed:
                rev_edge.is_closed = True
                rev_edge.closure_reason = reason
                closed_ids.append(rev_edge.road_id)

        return closed_ids

    def reopen_road(self, road_id: str, direction: str = "both") -> List[str]:
        """
        Reopen a previously closed road segment and restore lane capacity.
        Parameters:
            road_id: ID of the primary road segment to reopen.
            direction: 'forward' or 'both'.
        Returns:
            List of reopened road IDs.
        """
        reopened_ids: List[str] = []
        if road_id in self.edges:
            edge = self.edges[road_id]
            edge.is_closed = False
            edge.closure_reason = None
            edge.capacity_fraction = 1.0
            edge.congestion_factor = 1.0
            reopened_ids.append(road_id)

        if direction.lower() == "both":
            rev_edge = self.get_reverse_edge(road_id)
            if rev_edge:
                rev_edge.is_closed = False
                rev_edge.closure_reason = None
                rev_edge.capacity_fraction = 1.0
                rev_edge.congestion_factor = 1.0
                reopened_ids.append(rev_edge.road_id)

        return reopened_ids

    def set_lane_blockage(
        self,
        road_id: str,
        remaining_capacity_fraction: float,
        direction: str = "forward",
    ) -> List[str]:
        """
        Simulate partial road obstruction (e.g., 1 of 2 lanes blocked -> 0.5 capacity).
        Maps capacity reduction into congestion factor: factor = max(1.0, 1.0 / capacity).
        """
        cap = max(0.05, min(1.0, float(remaining_capacity_fraction)))
        target_ids = [road_id]
        if direction.lower() == "both":
            rev = self.get_reverse_edge(road_id)
            if rev:
                target_ids.append(rev.road_id)

        modified: List[str] = []
        for rid in target_ids:
            if rid in self.edges:
                edge = self.edges[rid]
                edge.capacity_fraction = cap
                # Capacity reduction proportionally slows traffic: factor = 1.0 / capacity
                edge.congestion_factor = max(edge.congestion_factor, round(1.0 / cap, 2))
                modified.append(rid)
        return modified

    def update_congestion(self, road_id: str, congestion_factor: float) -> bool:
        """
        Update the congestion multiplier for a road segment.
        1.0 = Free flow, 1.6 = Moderate, 2.5 = Heavy, 4.5 = Gridlock.
        """
        if road_id in self.edges:
            self.edges[road_id].congestion_factor = max(1.0, float(congestion_factor))
            return True
        return False

    def bulk_update_traffic_observations(self, observations: List[Dict[str, Any]]) -> int:
        """
        Apply a list of traffic observations (format from Member 3 / Member 1).
        """
        count = 0
        level_map = {
            "free_flow": 1.0,
            "normal": 1.0,
            "moderate": 1.6,
            "heavy": 2.5,
            "severe": 3.5,
            "gridlock": 4.5,
        }
        for obs in observations:
            rid = obs.get("road_id")
            if not rid or rid not in self.edges:
                continue

            factor = obs.get("congestion_factor")
            if factor is None:
                level = str(obs.get("congestion_level", "")).lower()
                factor = level_map.get(level, 1.0)

            self.update_congestion(rid, factor)
            count += 1
        return count

    def set_signal_state(self, node_id: str, state: SignalState) -> bool:
        """Set simulated traffic light state at an intersection."""
        if node_id in self.nodes:
            self.nodes[node_id].signal_state = state
            return True
        return False

    # -------------------------------------------------------------------------
    # Serialization for Member 1 (API) & Member 5 (Frontend / Map)
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert full graph topology to dictionary."""
        return {
            "name": self.name,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
            "simulated": True,
        }

    def to_geojson(self) -> Dict[str, Any]:
        """
        Convert road graph to standard GeoJSON FeatureCollection (RFC 7946).
        Coordinates are strictly [longitude, latitude].
        Closed roads have effective_travel_time_seconds: null.
        """
        features: List[Dict[str, Any]] = []

        # 1. Point features for nodes/intersections
        for node in self.nodes.values():
            features.append({
                "type": "Feature",
                "id": node.node_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [node.longitude, node.latitude],  # GeoJSON is [lon, lat]
                },
                "properties": {
                    "feature_type": "intersection",
                    "node_id": node.node_id,
                    "name": node.name,
                    "type": node.node_type.value if hasattr(node.node_type, "value") else str(node.node_type),
                    "signal_state": node.signal_state.value if hasattr(node.signal_state, "value") else str(node.signal_state),
                    "simulated": True,
                },
            })

        # 2. LineString features for road segments
        for edge in self.edges.values():
            u = self.nodes[edge.source]
            v = self.nodes[edge.target]
            eff_time = finite_or_none(edge.effective_travel_time_seconds, 1)

            features.append({
                "type": "Feature",
                "id": edge.road_id,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [u.longitude, u.latitude],  # [lon, lat]
                        [v.longitude, v.latitude],  # [lon, lat]
                    ],
                },
                "properties": {
                    "feature_type": "road",
                    "road_id": edge.road_id,
                    "pair_id": edge.pair_id or edge.road_id,
                    "direction": edge.direction,
                    "name": edge.name,
                    "source": edge.source,
                    "target": edge.target,
                    "length_meters": edge.length_meters,
                    "speed_limit_kmph": edge.speed_limit_kmph,
                    "lanes": edge.lanes,
                    "congestion_factor": edge.congestion_factor,
                    "capacity_fraction": edge.capacity_fraction,
                    "is_closed": edge.is_closed,
                    "closure_reason": edge.closure_reason,
                    "effective_travel_time_seconds": eff_time,
                    "simulated": True,
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def to_networkx(self) -> Any:
        """Optional conversion to networkx.DiGraph if networkx is installed."""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("NetworkX is not installed. You can use CityGraph native algorithms directly.")

        G = nx.DiGraph(name=self.name)
        for nid, node in self.nodes.items():
            G.add_node(nid, **node.to_dict())
        for rid, edge in self.edges.items():
            cost = edge.effective_travel_time_seconds
            weight = cost if not math.isinf(cost) else None
            G.add_edge(edge.source, edge.target, road_id=rid, weight=weight, **edge.to_dict())
        return G
