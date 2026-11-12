"""
UrbanFlow AI - Graph Algorithms: Dijkstra, A*, and Yen's K-Shortest Paths
Member 4: Road Network, Emergency Routing & Traffic Diversion
"""

from __future__ import annotations
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple
from .models import RoutePath, Edge, RouteContext, VehicleClass
from .graph import CityGraph, haversine_distance_meters


def _reconstruct_path(
    graph: CityGraph,
    came_from: Dict[str, Tuple[str, Edge]],
    start_node: str,
    end_node: str,
    total_cost: float,
    ctx: Optional[RouteContext] = None,
) -> RoutePath:
    """Reconstruct node sequence, road sequence, and coordinates from came_from mapping."""
    curr = end_node
    reversed_nodes: List[str] = [curr]
    reversed_roads: List[str] = []
    total_distance = 0.0

    while curr != start_node:
        prev_node, edge = came_from[curr]
        reversed_roads.append(edge.road_id)
        total_distance += edge.length_meters
        reversed_nodes.append(prev_node)
        curr = prev_node

    node_ids = list(reversed(reversed_nodes))
    road_ids = list(reversed(reversed_roads))
    coordinates = [(graph.nodes[nid].latitude, graph.nodes[nid].longitude) for nid in node_ids]

    summary = (
        f"Route from {node_ids[0]} to {node_ids[-1]} via {len(road_ids)} "
        f"segment{'s' if len(road_ids) != 1 else ''} ({round(total_distance / 1000.0, 2)} km)"
    )

    return RoutePath(
        node_ids=node_ids,
        road_ids=road_ids,
        total_distance_meters=total_distance,
        estimated_travel_time_seconds=total_cost,
        coordinates=coordinates,
        summary=summary,
        overlap_ratio=0.0,
    )


def compute_minimum_effective_cost_per_meter(
    graph: CityGraph,
    ctx: Optional[RouteContext] = None,
    excluded_roads: Optional[Set[str]] = None,
) -> float:
    """
    Computes min(cost(e) / e.length_meters) over all open traversable edges at query time.
    Provides the admissible unit rate for the A* Haversine distance heuristic.
    """
    excluded = excluded_roads or set()
    min_rate = float("inf")

    for edge in graph.edges.values():
        if edge.is_closed and (ctx is None or not ctx.ignore_closures):
            continue
        if edge.road_id in excluded:
            continue
        if edge.length_meters <= 0:
            continue

        cost = edge.compute_travel_time(ctx)
        if not math.isinf(cost):
            rate = cost / edge.length_meters
            if rate < min_rate:
                min_rate = rate

    return min_rate if not math.isinf(min_rate) else 0.0


def dijkstra(
    graph: CityGraph,
    start_node: str,
    end_node: str,
    ctx: Optional[RouteContext] = None,
    excluded_road_ids: Optional[Set[str]] = None,
    excluded_node_ids: Optional[Set[str]] = None,
    edge_cost_multipliers: Optional[Dict[str, float]] = None,
) -> Optional[RoutePath]:
    """
    Dijkstra's Shortest Path Algorithm based on dynamic travel time weights.
    Closed roads have infinite cost and are completely skipped.
    """
    if start_node not in graph.nodes or end_node not in graph.nodes:
        return None
    if start_node == end_node:
        node = graph.nodes[start_node]
        return RoutePath(
            node_ids=[start_node],
            road_ids=[],
            total_distance_meters=0.0,
            estimated_travel_time_seconds=0.0,
            coordinates=[(node.latitude, node.longitude)],
            summary="Origin is destination.",
            overlap_ratio=0.0,
        )

    excluded_roads = excluded_road_ids or set()
    excluded_nodes = excluded_node_ids or set()
    multipliers = edge_cost_multipliers or {}

    pq: List[Tuple[float, int, str]] = []
    entry_counter = 0

    dist: Dict[str, float] = {start_node: 0.0}
    came_from: Dict[str, Tuple[str, Edge]] = {}

    heapq.heappush(pq, (0.0, entry_counter, start_node))

    while pq:
        current_dist, _, u = heapq.heappop(pq)

        if u == end_node:
            return _reconstruct_path(graph, came_from, start_node, end_node, current_dist, ctx=ctx)

        if current_dist > dist.get(u, float("inf")):
            continue

        for edge in graph.adjacency.get(u, []):
            if edge.road_id in excluded_roads:
                continue
            if edge.is_closed and (ctx is None or not ctx.ignore_closures):
                continue

            v = edge.target
            if v in excluded_nodes:
                continue

            base_cost = edge.compute_travel_time(ctx)
            if math.isinf(base_cost):
                continue

            multiplier = multipliers.get(edge.road_id, 1.0)
            weight = base_cost * multiplier

            new_cost = current_dist + weight
            if new_cost < dist.get(v, float("inf")):
                dist[v] = new_cost
                came_from[v] = (u, edge)
                entry_counter += 1
                heapq.heappush(pq, (new_cost, entry_counter, v))

    return None


def astar(
    graph: CityGraph,
    start_node: str,
    end_node: str,
    ctx: Optional[RouteContext] = None,
    excluded_road_ids: Optional[Set[str]] = None,
    excluded_node_ids: Optional[Set[str]] = None,
    edge_cost_multipliers: Optional[Dict[str, float]] = None,
) -> Optional[RoutePath]:
    """
    A* Search Algorithm with Admissible Haversine Heuristic.
    Heuristic: h(n) = haversine(n, dest) * min(cost(e)/e.length_meters for open e).
    Computed at query time from the exact cost function and RouteContext used for routing,
    guaranteeing admissibility and consistency under siren speedup, corridor discounts, and congestion.
    """
    if start_node not in graph.nodes or end_node not in graph.nodes:
        return None
    if start_node == end_node:
        node = graph.nodes[start_node]
        return RoutePath(
            node_ids=[start_node],
            road_ids=[],
            total_distance_meters=0.0,
            estimated_travel_time_seconds=0.0,
            coordinates=[(node.latitude, node.longitude)],
            summary="Origin is destination.",
            overlap_ratio=0.0,
        )

    excluded_roads = excluded_road_ids or set()
    excluded_nodes = excluded_node_ids or set()
    multipliers = edge_cost_multipliers or {}

    dest_node = graph.nodes[end_node]
    min_cost_per_meter = compute_minimum_effective_cost_per_meter(
        graph, ctx=ctx, excluded_roads=excluded_roads
    )

    def heuristic(node_id: str) -> float:
        n = graph.nodes[node_id]
        dist_m = haversine_distance_meters(n.latitude, n.longitude, dest_node.latitude, dest_node.longitude)
        return dist_m * min_cost_per_meter

    pq: List[Tuple[float, float, int, str]] = []  # (f_score, g_score, counter, node_id)
    entry_counter = 0

    g_score: Dict[str, float] = {start_node: 0.0}
    came_from: Dict[str, Tuple[str, Edge]] = {}

    h_start = heuristic(start_node)
    heapq.heappush(pq, (h_start, 0.0, entry_counter, start_node))

    while pq:
        f, current_g, _, u = heapq.heappop(pq)

        if u == end_node:
            return _reconstruct_path(graph, came_from, start_node, end_node, current_g, ctx=ctx)

        if current_g > g_score.get(u, float("inf")):
            continue

        for edge in graph.adjacency.get(u, []):
            if edge.road_id in excluded_roads:
                continue
            if edge.is_closed and (ctx is None or not ctx.ignore_closures):
                continue

            v = edge.target
            if v in excluded_nodes:
                continue

            base_cost = edge.compute_travel_time(ctx)
            if math.isinf(base_cost):
                continue

            multiplier = multipliers.get(edge.road_id, 1.0)
            weight = base_cost * multiplier

            tentative_g = current_g + weight
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                came_from[v] = (u, edge)
                f_score = tentative_g + heuristic(v)
                entry_counter += 1
                heapq.heappush(pq, (f_score, tentative_g, entry_counter, v))

    return None


def yen_k_shortest_paths(
    graph: CityGraph,
    start_node: str,
    end_node: str,
    k: int = 3,
    algorithm: str = "astar",
    ctx: Optional[RouteContext] = None,
    excluded_road_ids: Optional[Set[str]] = None,
) -> List[RoutePath]:
    """
    Yen's Algorithm for computing loopless K-Shortest Paths.
    Closed edges are strictly excluded from all spur searches.
    """
    search_fn = astar if algorithm.lower() == "astar" else dijkstra
    base_excluded = set(excluded_road_ids or [])

    # Closed roads are fundamentally excluded
    if ctx is None or not ctx.ignore_closures:
        for rid, edge in graph.edges.items():
            if edge.is_closed:
                base_excluded.add(rid)

    first_path = search_fn(graph, start_node, end_node, ctx=ctx, excluded_road_ids=base_excluded)
    if not first_path:
        return []

    A: List[RoutePath] = [first_path]
    B: List[Tuple[float, RoutePath]] = []

    for path_idx in range(1, k):
        prev_path = A[path_idx - 1]

        for i in range(len(prev_path.node_ids) - 1):
            spur_node = prev_path.node_ids[i]
            root_path_nodes = prev_path.node_ids[: i + 1]
            root_path_roads = prev_path.road_ids[:i]

            root_cost = 0.0
            root_dist = 0.0
            for rid in root_path_roads:
                edge = graph.edges[rid]
                cost = edge.compute_travel_time(ctx)
                if math.isinf(cost):
                    root_cost = float("inf")
                    break
                root_cost += cost
                root_dist += edge.length_meters

            if math.isinf(root_cost):
                continue

            # Exclude edges that branch into already discovered paths sharing root path
            spur_excluded_roads = set(base_excluded)
            for p in A:
                if p.node_ids[: i + 1] == root_path_nodes:
                    if i < len(p.road_ids):
                        spur_excluded_roads.add(p.road_ids[i])

            spur_excluded_nodes = set(root_path_nodes[:-1])

            spur_path = search_fn(
                graph,
                spur_node,
                end_node,
                ctx=ctx,
                excluded_road_ids=spur_excluded_roads,
                excluded_node_ids=spur_excluded_nodes,
            )

            if spur_path:
                total_nodes = root_path_nodes[:-1] + spur_path.node_ids
                total_roads = root_path_roads + spur_path.road_ids
                total_distance = root_dist + spur_path.total_distance_meters
                total_cost = root_cost + spur_path.estimated_travel_time_seconds
                coords = [(graph.nodes[n].latitude, graph.nodes[n].longitude) for n in total_nodes]

                # Compute length-based overlap ratio with primary path A[0]
                shared_length = sum(
                    graph.edges[r].length_meters
                    for r in total_roads
                    if r in A[0].road_ids
                )
                overlap = shared_length / max(total_distance, 1.0)

                candidate = RoutePath(
                    node_ids=total_nodes,
                    road_ids=total_roads,
                    total_distance_meters=total_distance,
                    estimated_travel_time_seconds=total_cost,
                    coordinates=coords,
                    summary=f"Alternative path via {spur_node} ({round(total_distance/1000.0, 2)} km)",
                    overlap_ratio=overlap,
                )

                already_in_B = any(cand.node_ids == candidate.node_ids for _, cand in B)
                already_in_A = any(cand.node_ids == candidate.node_ids for cand in A)
                if not already_in_B and not already_in_A:
                    B.append((total_cost, candidate))

        if not B:
            break

        B.sort(key=lambda x: x[0])
        best_cost, best_candidate = B.pop(0)
        A.append(best_candidate)

    return A


def penalty_based_alternatives(
    graph: CityGraph,
    start_node: str,
    end_node: str,
    primary_route: RoutePath,
    count: int = 2,
    penalty_factor: float = 2.5,
    algorithm: str = "astar",
    ctx: Optional[RouteContext] = None,
) -> List[RoutePath]:
    """
    Generate alternative routes by applying an edge cost penalty to roads used in previous routes.
    This discourages overlapping road segments and finds viable detour corridors.
    Computes and reports the physical overlap ratio with the primary route.
    """
    search_fn = astar if algorithm.lower() == "astar" else dijkstra
    alternatives: List[RoutePath] = []
    cumulative_penalties: Dict[str, float] = {}

    for rid in primary_route.road_ids:
        cumulative_penalties[rid] = penalty_factor

    for alt_idx in range(count):
        alt = search_fn(
            graph,
            start_node,
            end_node,
            ctx=ctx,
            edge_cost_multipliers=cumulative_penalties,
        )
        if not alt:
            break
        if alt.node_ids == primary_route.node_ids:
            break
        if any(alt.node_ids == existing.node_ids for existing in alternatives):
            break

        # Recompute true cost without artificial penalty
        true_time = 0.0
        for rid in alt.road_ids:
            c = graph.edges[rid].compute_travel_time(ctx)
            if math.isinf(c):
                true_time = float("inf")
                break
            true_time += c

        if math.isinf(true_time):
            break

        # Calculate length-based overlap ratio with primary route
        shared_length = sum(
            graph.edges[r].length_meters
            for r in alt.road_ids
            if r in primary_route.road_ids
        )
        overlap = shared_length / max(alt.total_distance_meters, 1.0)

        alt.estimated_travel_time_seconds = true_time
        alt.overlap_ratio = overlap
        alt.summary = (
            f"Detour option #{alt_idx + 1} "
            f"(overlap: {round(overlap * 100, 1)}% with primary path)"
        )

        alternatives.append(alt)
        for rid in alt.road_ids:
            cumulative_penalties[rid] = cumulative_penalties.get(rid, 1.0) * penalty_factor

    return alternatives
