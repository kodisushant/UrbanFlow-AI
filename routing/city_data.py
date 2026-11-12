"""
UrbanFlow AI - Test City Road Network Data
Member 4: Road Network, Emergency Routing & Traffic Diversion

Realistic 20-Intersection Grid & Arterial Road Network with Geographic Coordinates.
All road lengths strictly exceed Haversine distances to maintain geometric admissibility.
"""

from typing import List
from .models import Node, NodeType, SignalState, EmergencyUnit, EmergencyUnitType, UnitStatus, SIREN_SPEEDUP
from .graph import CityGraph


def build_cyber_city_network() -> CityGraph:
    """
    Constructs the 20-intersection 'Cyber City' road network graph.
    All road lengths strictly satisfy length_meters >= 0.999 * haversine.
    """
    g = CityGraph(name="Cyber City Metro Network")

    # -------------------------------------------------------------------------
    # 1. Nodes (Intersections & Specialized Facilities)
    # -------------------------------------------------------------------------
    nodes_data = [
        # (node_id, name, lat, lon, node_type)
        ("INT-01", "City Center Square", 17.4420, 78.3800, NodeType.TRANSIT_HUB),
        ("INT-02", "North Tech Park Junction", 17.4560, 78.3810, NodeType.INTERSECTION),
        ("INT-03", "Cyber Gateway Hub", 17.4485, 78.3740, NodeType.INTERSECTION),
        ("INT-04", "Metro Hospital North", 17.4600, 78.3720, NodeType.HOSPITAL),
        ("INT-05", "Central Police Headquarters", 17.4380, 78.3850, NodeType.POLICE_STATION),
        ("INT-06", "West Industrial Zone", 17.4430, 78.3580, NodeType.INTERSECTION),
        ("INT-07", "West Fire Station #1", 17.4490, 78.3550, NodeType.FIRE_STATION),
        ("INT-08", "Financial District South", 17.4310, 78.3680, NodeType.INTERSECTION),
        ("INT-09", "South Express Junction", 17.4260, 78.3820, NodeType.INTERSECTION),
        ("INT-10", "East Riverside Crossing", 17.4440, 78.3970, NodeType.INTERSECTION),
        ("INT-11", "East Police Substation", 17.4520, 78.3980, NodeType.POLICE_STATION),
        ("INT-12", "Midtown Commercial Plaza", 17.4490, 78.3880, NodeType.INTERSECTION),
        ("INT-13", "South City Apex Hospital", 17.4220, 78.3730, NodeType.HOSPITAL),
        ("INT-14", "Outer Ring Road - West Gate", 17.4370, 78.3480, NodeType.INTERSECTION),
        ("INT-15", "Outer Ring Road - North Gate", 17.4680, 78.3800, NodeType.INTERSECTION),
        ("INT-16", "Outer Ring Road - East Gate", 17.4500, 78.4090, NodeType.INTERSECTION),
        ("INT-17", "Outer Ring Road - South Gate", 17.4180, 78.3820, NodeType.INTERSECTION),
        ("INT-18", "Central Market Circle", 17.4360, 78.3760, NodeType.INTERSECTION),
        ("INT-19", "Grand Boulevard Overpass", 17.4450, 78.3840, NodeType.INTERSECTION),
        ("INT-20", "Airport Expressway Interchange", 17.4150, 78.3650, NodeType.TRANSIT_HUB),
    ]

    for nid, name, lat, lon, ntype in nodes_data:
        g.add_node(Node(
            node_id=nid,
            name=name,
            latitude=lat,
            longitude=lon,
            node_type=ntype,
            signal_state=SignalState.GREEN,
            signal_cycle_seconds=60,
        ))

    # -------------------------------------------------------------------------
    # 2. Edges (Road Segments - Bidirectional streets with validated physical lengths)
    # -------------------------------------------------------------------------
    # (id_fwd, id_rev, u, v, road_name, length_m, speed_limit_kmph, lanes)
    roads_data = [
        # Central Arterials & Boulevards
        ("ROAD-01A", "ROAD-01B", "INT-01", "INT-19", "Central Grand Blvd", 650, 50, 3),
        ("ROAD-02A", "ROAD-02B", "INT-19", "INT-12", "Midtown Avenue", 700, 50, 2),
        ("ROAD-03A", "ROAD-03B", "INT-19", "INT-03", "Cyber Gateway Link", 1250, 60, 3),
        ("ROAD-04A", "ROAD-04B", "INT-01", "INT-18", "Market Road", 850, 40, 2),
        ("ROAD-05A", "ROAD-05B", "INT-18", "INT-08", "South Financial Way", 1150, 60, 2),
        ("ROAD-06A", "ROAD-06B", "INT-01", "INT-05", "Police HQ Avenue", 750, 50, 2),
        ("ROAD-07A", "ROAD-07B", "INT-05", "INT-09", "South Expressway Link", 1500, 60, 3),

        # North Sector Connections (Tech Park & North Hospital)
        ("ROAD-08A", "ROAD-08B", "INT-12", "INT-02", "Tech Corridor North", 1200, 60, 3),
        ("ROAD-09A", "ROAD-09B", "INT-03", "INT-02", "Cyber Tech Connector", 1250, 60, 2),
        ("ROAD-10A", "ROAD-10B", "INT-02", "INT-04", "Hospital Access Blvd", 1200, 50, 2),
        ("ROAD-11A", "ROAD-11B", "INT-03", "INT-04", "North Gateway Expressway", 1350, 60, 2),
        ("ROAD-12A", "ROAD-12B", "INT-02", "INT-15", "North Ring Link", 1500, 80, 4),

        # West Sector Connections (Industrial Zone & Fire Station)
        ("ROAD-13A", "ROAD-13B", "INT-03", "INT-06", "West Industrial Highway", 1950, 60, 3),
        ("ROAD-14A", "ROAD-14B", "INT-06", "INT-07", "Fire Station Feeder Road", 800, 50, 2),
        ("ROAD-15A", "ROAD-15B", "INT-06", "INT-14", "West Ring Connector", 1350, 80, 4),
        ("ROAD-16A", "ROAD-16B", "INT-14", "INT-08", "Southwest Arterial", 2400, 70, 3),

        # East Sector Connections (Riverside & East Substation)
        ("ROAD-17A", "ROAD-17B", "INT-12", "INT-10", "Riverside Parkway", 1200, 50, 2),
        ("ROAD-18A", "ROAD-18B", "INT-10", "INT-11", "East Substation Road", 1000, 50, 2),
        ("ROAD-19A", "ROAD-19B", "INT-11", "INT-16", "East Ring Connector", 1350, 80, 4),
        ("ROAD-20A", "ROAD-20B", "INT-01", "INT-10", "River Boulevard East", 2000, 60, 3),

        # South Sector Connections (South Hospital & Airport Expressway)
        ("ROAD-21A", "ROAD-21B", "INT-08", "INT-13", "Apex Hospital Drive", 1250, 50, 2),
        ("ROAD-22A", "ROAD-22B", "INT-09", "INT-17", "South Ring Interchange Road", 1050, 80, 4),
        ("ROAD-23A", "ROAD-23B", "INT-13", "INT-20", "Airport Link South", 1300, 80, 3),
        ("ROAD-24A", "ROAD-24B", "INT-08", "INT-20", "Financial Airport Connector", 1950, 80, 3),
        ("ROAD-25A", "ROAD-25B", "INT-17", "INT-20", "South Ring Terminal Road", 2000, 80, 4),

        # Outer Ring Road High-Speed Highway (Bypasses city center)
        ("ROAD-26A", "ROAD-26B", "INT-15", "INT-16", "Outer Ring Road North-East", 3900, 80, 4),
        ("ROAD-27A", "ROAD-27B", "INT-16", "INT-17", "Outer Ring Road East-South", 4800, 80, 4),
        ("ROAD-28A", "ROAD-28B", "INT-17", "INT-14", "Outer Ring Road South-West", 4400, 80, 4),
        ("ROAD-29A", "ROAD-29B", "INT-14", "INT-15", "Outer Ring Road West-North", 5100, 80, 4),
    ]

    for fwd_id, rev_id, u, v, name, length_m, speed_limit, lanes in roads_data:
        g.add_bidirectional_road(
            forward_id=fwd_id,
            reverse_id=rev_id,
            node_a=u,
            node_b=v,
            name=name,
            length_meters=length_m,
            speed_limit_kmph=speed_limit,
            lanes=lanes,
            pair_id=fwd_id[:7],
        )

    g.validate()
    return g


def get_sample_emergency_units(graph: CityGraph) -> List[EmergencyUnit]:
    """
    Seeds a representative roster of emergency service vehicles stationed at respective facilities.
    """
    units_data = [
        # (unit_id, type, station_node, capabilities, speed_factor)
        (
            "AMB-01",
            EmergencyUnitType.AMBULANCE,
            "INT-04",  # Stationed at Metro Hospital North
            ["advanced_life_support", "paramedic_crew", "ventilator", "defibrillator"],
            SIREN_SPEEDUP,
        ),
        (
            "AMB-02",
            EmergencyUnitType.AMBULANCE,
            "INT-13",  # Stationed at South City Apex Hospital
            ["basic_life_support", "emergency_transport"],
            SIREN_SPEEDUP,
        ),
        (
            "FIRE-01",
            EmergencyUnitType.FIRE_ENGINE,
            "INT-07",  # Stationed at West Fire Station
            ["water_tender", "hydraulic_rescue_cutters", "ladder", "hazmat_containment"],
            1.20,
        ),
        (
            "POLICE-01",
            EmergencyUnitType.POLICE,
            "INT-05",  # Stationed at Central Police HQ
            ["traffic_control", "perimeter_security", "incident_investigation"],
            1.30,
        ),
        (
            "POLICE-02",
            EmergencyUnitType.POLICE,
            "INT-11",  # Stationed at East Police Substation
            ["rapid_response", "crowd_diversion", "motorcycle_escort"],
            1.35,
        ),
    ]

    units: List[EmergencyUnit] = []
    for uid, utype, station_node, caps, speed_factor in units_data:
        node = graph.nodes[station_node]
        units.append(EmergencyUnit(
            unit_id=uid,
            unit_type=utype,
            location_node=station_node,
            latitude=node.latitude,
            longitude=node.longitude,
            availability=UnitStatus.AVAILABLE,
            capabilities=caps,
            speed_factor=speed_factor,
        ))

    return units
