#!/usr/bin/env python3
"""
UrbanFlow AI - OpenStreetMap Road Graph Builder
Downloads real drivable road network around HITEC City / Cyber Towers, Hyderabad
using OSMnx, simplifies it to major roads (~100-300 nodes), extracts real curved
road geometry, and exports to data/city_graph.json.
"""

import os
import sys
import json
import math
from typing import Dict, List, Any, Tuple

try:
    import osmnx as ox
    import networkx as nx
except ImportError:
    print("Error: osmnx and networkx are required. Install with: pip install -r requirements-dev.txt")
    sys.exit(1)

# Center around Cyber Towers / HITEC City, Hyderabad
CENTER_LAT = 17.4485
CENTER_LON = 78.3740
SEARCH_RADIUS_METERS = 1500

DEFAULT_SPEEDS = {
    "motorway": 70.0,
    "trunk": 60.0,
    "primary": 50.0,
    "secondary": 45.0,
    "tertiary": 35.0,
    "motorway_link": 50.0,
    "trunk_link": 45.0,
    "primary_link": 40.0,
    "secondary_link": 35.0,
    "tertiary_link": 30.0,
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def build_graph():
    print(f"1. Downloading OSM drivable network around ({CENTER_LAT}, {CENTER_LON}) within {SEARCH_RADIUS_METERS}m...")
    cf = '["highway"~"motorway|trunk|primary|secondary|tertiary"]'

    ox.settings.use_cache = True
    ox.settings.log_console = False

    G = ox.graph_from_point(
        (CENTER_LAT, CENTER_LON),
        dist=SEARCH_RADIUS_METERS,
        network_type="drive",
        custom_filter=cf,
        simplify=True
    )
    print(f"   Raw downloaded graph: {len(G.nodes)} nodes, {len(G.edges)} edges")

    # Keep largest strongly connected component for complete reachability
    if not nx.is_strongly_connected(G):
        largest_scc = max(nx.strongly_connected_components(G), key=len)
        if len(largest_scc) >= 60:
            G = G.subgraph(largest_scc).copy()
        else:
            largest_wcc = max(nx.weakly_connected_components(G), key=len)
            G = G.subgraph(largest_wcc).copy()

    print(f"   Connected graph: {len(G.nodes)} nodes, {len(G.edges)} edges")

    # 2. Map nodes to semantic IDs (INT-01 .. INT-N)
    # Find node closest to Cyber Towers center for INT-03 (Incident Location)
    nodes_data = {}
    for n, d in G.nodes(data=True):
        lat = d["y"]
        lon = d["x"]
        dist_to_center = haversine(CENTER_LAT, CENTER_LON, lat, lon)
        nodes_data[n] = {"lat": lat, "lon": lon, "dist": dist_to_center, "raw": d}

    # Sort nodes by distance to center
    sorted_by_dist = sorted(nodes_data.keys(), key=lambda n: nodes_data[n]["dist"])
    int03_osm = sorted_by_dist[0]

    # Assign well-distributed strategic nodes for emergency units
    # INT-03: Incident (Cyber Towers)
    # INT-04: North (Hospital / Ambulance 1 station)
    # INT-05: South-East (Police 1)
    # INT-07: West (Fire 1)
    # INT-11: East / Metro corridor
    # INT-13: South (Hospital 2 / Ambulance 2)
    # INT-19: Neighboring junction to INT-03 (connects ROAD-03A)
    # INT-20: Intermediate North corridor (between INT-04 and INT-11)
    
    assigned_osm_to_id: Dict[Any, str] = {int03_osm: "INT-03"}

    # Find an immediate neighbor of INT-03 for INT-19 (to form ROAD-03A)
    neighbors_of_int03 = list(G.successors(int03_osm)) + list(G.predecessors(int03_osm))
    int19_osm = neighbors_of_int03[0] if neighbors_of_int03 else sorted_by_dist[1]
    assigned_osm_to_id[int19_osm] = "INT-19"

    # Strategic directional nodes
    def find_best_node(target_lat: float, target_lon: float, exclude: set) -> Any:
        best = None
        min_d = float("inf")
        for n, data in nodes_data.items():
            if n in exclude:
                continue
            d = haversine(target_lat, target_lon, data["lat"], data["lon"])
            if d < min_d:
                min_d = d
                best = n
        return best

    used = {int03_osm, int19_osm}

    # INT-04: North (~17.458, 78.372)
    int04_osm = find_best_node(17.458, 78.372, used)
    assigned_osm_to_id[int04_osm] = "INT-04"
    used.add(int04_osm)

    # INT-05: South-East (~17.438, 78.384)
    int05_osm = find_best_node(17.438, 78.384, used)
    assigned_osm_to_id[int05_osm] = "INT-05"
    used.add(int05_osm)

    # INT-07: West (~17.449, 78.358)
    int07_osm = find_best_node(17.449, 78.358, used)
    assigned_osm_to_id[int07_osm] = "INT-07"
    used.add(int07_osm)

    # INT-11: East HITEC City Station (~17.447, 78.380)
    int11_osm = find_best_node(17.447, 78.380, used)
    assigned_osm_to_id[int11_osm] = "INT-11"
    used.add(int11_osm)

    # INT-13: South (~17.436, 78.370)
    int13_osm = find_best_node(17.436, 78.370, used)
    assigned_osm_to_id[int13_osm] = "INT-13"
    used.add(int13_osm)

    # INT-20: North-East corridor (~17.454, 78.375)
    int20_osm = find_best_node(17.454, 78.375, used)
    assigned_osm_to_id[int20_osm] = "INT-20"
    used.add(int20_osm)

    # INT-01: City Center Square (~17.442, 78.380)
    int01_osm = find_best_node(17.442, 78.380, used)
    assigned_osm_to_id[int01_osm] = "INT-01"
    used.add(int01_osm)

    # INT-02: North Tech Park (~17.456, 78.381)
    int02_osm = find_best_node(17.456, 78.381, used)
    assigned_osm_to_id[int02_osm] = "INT-02"
    used.add(int02_osm)

    # Assign remaining sequential INT numbers
    next_int_num = 6
    remaining_nodes = [n for n in G.nodes() if n not in assigned_osm_to_id]
    for n in remaining_nodes:
        while next_int_num in [1, 2, 3, 4, 5, 7, 11, 13, 19, 20]:
            next_int_num += 1
        assigned_osm_to_id[n] = f"INT-{next_int_num:02d}" if next_int_num < 100 else f"INT-{next_int_num:03d}"
        next_int_num += 1

    id_to_osm = {v: k for k, v in assigned_osm_to_id.items()}

    # 3. Build Nodes list
    nodes_export = []
    semantic_names = {
        "INT-01": "City Center Square",
        "INT-02": "North Tech Park Junction",
        "INT-03": "Cyber Towers Intersection (HITEC Hub)",
        "INT-04": "North Hospital Medical Center",
        "INT-05": "Central Police Headquarters",
        "INT-07": "West Fire Rescue Station #1",
        "INT-11": "HITEC City Metro Station Junction",
        "INT-13": "South Emergency Hospital Center",
        "INT-19": "Madhapur Main Arterial Crossing",
        "INT-20": "Silicon Ridge North Corridor",
    }
    node_types = {
        "INT-04": "hospital",
        "INT-13": "hospital",
        "INT-05": "police_station",
        "INT-07": "fire_station",
        "INT-01": "transit_hub",
        "INT-03": "intersection",
        "INT-11": "transit_hub",
        "INT-19": "intersection",
        "INT-20": "intersection",
    }

    for osm_id, node_id in sorted(assigned_osm_to_id.items(), key=lambda x: x[1]):
        nd = nodes_data[osm_id]
        deg = G.degree(osm_id)
        is_signal = deg >= 3 or node_id in ["INT-01", "INT-03", "INT-04", "INT-11", "INT-19", "INT-20"]
        name = semantic_names.get(node_id, f"HITEC Junction {node_id}")
        ntype = node_types.get(node_id, "intersection")

        nodes_export.append({
            "node_id": node_id,
            "id": node_id,
            "name": name,
            "latitude": round(nd["lat"], 6),
            "longitude": round(nd["lon"], 6),
            "lat": round(nd["lat"], 6),
            "lon": round(nd["lon"], 6),
            "is_signalized": is_signal,
            "signal_state": "priority_green" if node_id in ["INT-04", "INT-20", "INT-11", "INT-19"] else "normal",
            "signal_cycle_seconds": 60,
            "node_type": ntype,
            "simulated": True,
            "osm_id": str(osm_id)
        })

    print(f"   Formatted {len(nodes_export)} nodes. Designated INT-03 at Cyber Towers ({nodes_data[int03_osm]['lat']:.4f}, {nodes_data[int03_osm]['lon']:.4f})")

    # 4. Build Edges list with real geometry
    edges_export = []
    edge_idx = 1
    designated_road03a = False

    for u, v, k, data in G.edges(keys=True, data=True):
        source_id = assigned_osm_to_id[u]
        target_id = assigned_osm_to_id[v]

        # Determine road_id
        if not designated_road03a and ((source_id == "INT-19" and target_id == "INT-03") or (source_id == "INT-03" or target_id == "INT-03")):
            road_id = "ROAD-03A"
            designated_road03a = True
        else:
            if edge_idx == 3:
                edge_idx += 1
            suffix = "A" if edge_idx % 2 == 1 else "B"
            road_id = f"ROAD-{edge_idx:02d}{suffix}"
            edge_idx += 1

        # Extract real geometry: ordered list of [lat, lon]
        if "geometry" in data and data["geometry"]:
            geom = [[round(lat, 6), round(lon, 6)] for lon, lat in data["geometry"].coords]
        else:
            # Fallback to straight segment between endpoints
            u_data = nodes_data[u]
            v_data = nodes_data[v]
            geom = [
                [round(u_data["lat"], 6), round(u_data["lon"], 6)],
                [round(v_data["lat"], 6), round(v_data["lon"], 6)]
            ]

        # Road name
        raw_name = data.get("name")
        if isinstance(raw_name, list):
            name = " / ".join(str(n) for n in raw_name)
        elif raw_name:
            name = str(raw_name)
        else:
            highway = data.get("highway", "primary")
            if isinstance(highway, list):
                highway = highway[0]
            name = f"{source_id} - {target_id} ({highway.capitalize()})"

        if road_id == "ROAD-03A":
            name = "Cyber Towers Boulevard"

        length_m = round(float(data.get("length", 100.0)), 1)
        if length_m <= 0:
            u_data = nodes_data[u]
            v_data = nodes_data[v]
            length_m = round(haversine(u_data["lat"], u_data["lon"], v_data["lat"], v_data["lon"]), 1)

        # Speed limit
        hw_type = data.get("highway", "primary")
        if isinstance(hw_type, list):
            hw_type = hw_type[0]
        speed_limit = DEFAULT_SPEEDS.get(str(hw_type), 50.0)
        maxspeed = data.get("maxspeed")
        if maxspeed:
            try:
                if isinstance(maxspeed, list):
                    maxspeed = maxspeed[0]
                speed_limit = float(str(maxspeed).split()[0])
            except (ValueError, IndexError):
                pass

        time_sec = round(length_m / (speed_limit * (1000.0 / 3600.0)), 1)
        base_travel_time = max(int(round(time_sec)), 3)

        edges_export.append({
            "road_id": road_id,
            "id": road_id,
            "pair_id": road_id[:-1] if road_id[-1] in ["A", "B"] else road_id,
            "name": name,
            "source": source_id,
            "target": target_id,
            "source_node": source_id,
            "target_node": target_id,
            "length_meters": length_m,
            "length_m": length_m,
            "speed_limit_kmph": speed_limit,
            "lanes": data.get("lanes", 2),
            "is_one_way": data.get("oneway", False),
            "base_travel_time_seconds": base_travel_time,
            "current_congestion_level": "severe" if road_id == "ROAD-03A" else "free_flow",
            "congestion_weight_multiplier": 5.0 if road_id == "ROAD-03A" else 1.0,
            "congestion_factor": 5.0 if road_id == "ROAD-03A" else 1.0,
            "is_blocked": (road_id == "ROAD-03A"),
            "is_diverted": (road_id == "ROAD-03A"),
            "geometry": geom,
            "osm_highway": str(hw_type)
        })

    # Ensure ROAD-03A is always present
    has_road03a = any(e["road_id"] == "ROAD-03A" for e in edges_export)
    if not has_road03a and edges_export:
        edges_export[0]["road_id"] = "ROAD-03A"
        edges_export[0]["id"] = "ROAD-03A"
        edges_export[0]["name"] = "Cyber Towers Boulevard"
        edges_export[0]["is_blocked"] = True
        edges_export[0]["is_diverted"] = True

    city_graph_data = {
        "city_name": "HITEC City / Cyber Towers Real OSM Road Network",
        "name": "HITEC City / Cyber Towers Real OSM Road Network",
        "center": [CENTER_LAT, CENTER_LON],
        "total_nodes": len(nodes_export),
        "total_edges": len(edges_export),
        "nodes": nodes_export,
        "edges": edges_export
    }

    # Save data/city_graph.json
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "city_graph.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(city_graph_data, f, indent=2)

    print(f"5. Exported {len(nodes_export)} nodes and {len(edges_export)} edges to {out_file}")

    # 6. Update emergency units positions to valid nodes on new graph
    node_lookup = {n["node_id"]: n for n in nodes_export}
    units = [
        {
            "unit_id": "AMB-01",
            "call_sign": "Medic One ALS",
            "name": "Medic One ALS",
            "type": "ambulance",
            "unit_type": "ambulance",
            "station_node": "INT-04",
            "current_node": "INT-20",
            "latitude": node_lookup["INT-20"]["latitude"],
            "longitude": node_lookup["INT-20"]["longitude"],
            "status": "available",
            "availability": "available",
            "capabilities": ["advanced_life_support", "paramedic_crew", "ventilator", "defibrillator"],
            "speed_kmph": 55.0,
            "speed_factor": 1.25,
            "simulated": True
        },
        {
            "unit_id": "AMB-02",
            "call_sign": "Medic Two BLS",
            "name": "Medic Two BLS",
            "type": "ambulance",
            "unit_type": "ambulance",
            "station_node": "INT-13",
            "current_node": "INT-13",
            "latitude": node_lookup["INT-13"]["latitude"],
            "longitude": node_lookup["INT-13"]["longitude"],
            "status": "available",
            "availability": "available",
            "capabilities": ["basic_life_support", "emergency_transport"],
            "speed_kmph": 55.0,
            "speed_factor": 1.25,
            "simulated": True
        },
        {
            "unit_id": "FIRE-01",
            "call_sign": "Tower Rescue 7",
            "name": "Tower Rescue 7",
            "type": "fire_engine",
            "unit_type": "fire_engine",
            "station_node": "INT-07",
            "current_node": "INT-07",
            "latitude": node_lookup["INT-07"]["latitude"],
            "longitude": node_lookup["INT-07"]["longitude"],
            "status": "available",
            "availability": "available",
            "capabilities": ["water_tender", "hydraulic_rescue_cutters", "ladder", "hazmat_containment"],
            "speed_kmph": 50.0,
            "speed_factor": 1.2,
            "simulated": True
        },
        {
            "unit_id": "POLICE-01",
            "call_sign": "Patrol Alpha",
            "name": "Patrol Alpha",
            "type": "police_patrol",
            "unit_type": "police_patrol",
            "station_node": "INT-05",
            "current_node": "INT-05",
            "latitude": node_lookup["INT-05"]["latitude"],
            "longitude": node_lookup["INT-05"]["longitude"],
            "status": "available",
            "availability": "available",
            "capabilities": ["traffic_control", "perimeter_security", "siren_preemption"],
            "speed_kmph": 60.0,
            "speed_factor": 1.3,
            "simulated": True
        },
        {
            "unit_id": "POLICE-02",
            "call_sign": "East Patrol Delta",
            "name": "East Patrol Delta",
            "type": "police_patrol",
            "unit_type": "police_patrol",
            "station_node": "INT-11",
            "current_node": "INT-11",
            "latitude": node_lookup["INT-11"]["latitude"],
            "longitude": node_lookup["INT-11"]["longitude"],
            "status": "available",
            "availability": "available",
            "capabilities": ["traffic_enforcement", "intersection_cordon"],
            "speed_kmph": 60.0,
            "speed_factor": 1.3,
            "simulated": True
        }
    ]

    units_file = os.path.join(out_dir, "emergency_units.json")
    with open(units_file, "w", encoding="utf-8") as f:
        json.dump(units, f, indent=2)
    print(f"6. Updated emergency units positions in {units_file}")

    return city_graph_data, units


if __name__ == "__main__":
    build_graph()

