"""
Export City Graph Data to JSON and GeoJSON for Member 1 and Member 5.
Enforces allow_nan=False to ensure strict, valid JSON output.
"""

import os
import json
from routing.engine import UrbanFlowRoutingEngine


def export_assets():
    engine = UrbanFlowRoutingEngine()
    os.makedirs("data", exist_ok=True)

    # 1. Export Graph Topology JSON (for Member 1 FastAPI models & Member 3)
    graph_dict = engine.graph.to_dict()
    with open("data/city_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, indent=2, allow_nan=False)
    print("Exported data/city_graph.json")

    # 2. Export GeoJSON (for Member 5 Mapbox/Leaflet visualization)
    geojson_dict = engine.graph.to_geojson()
    with open("data/city_map.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson_dict, f, indent=2, allow_nan=False)
    print("Exported data/city_map.geojson")

    # 3. Export Emergency Units JSON
    units_dict = [u.to_dict() for u in engine.emergency_units.values()]
    with open("data/emergency_units.json", "w", encoding="utf-8") as f:
        json.dump(units_dict, f, indent=2, allow_nan=False)
    print("Exported data/emergency_units.json")

    # 4. Export Sample Benchmark Scenario Run
    scenario_result = engine.run_demonstration_scenario()
    with open("data/sample_scenario_output.json", "w", encoding="utf-8") as f:
        json.dump(scenario_result, f, indent=2, allow_nan=False)
    print("Exported data/sample_scenario_output.json")


if __name__ == "__main__":
    export_assets()
