# UrbanFlow AI — Graph Optimization & Emergency Routing Engine
**Role:** Member 4 (Road Network, Emergency Routing & Dynamic Traffic Diversion)  
**Package:** `routing/`

---

## 1. Simulation Disclaimer & Safety Boundary

> [!IMPORTANT]  
> **Strict Prototype Boundary — Simulated Traffic & Signals Only:**  
> All traffic signal states (`GREEN`, `RED`, `EMERGENCY_PRIORITY`), emergency vehicle trajectories, green corridors, and diversion plans are **strictly simulated** software models. This engine does **not** interface with, actuate, or control real-world traffic signals, municipal hardware, or physical emergency dispatch networks. Every generated output dictionary and GeoJSON feature explicitly carries `"simulated": true`.

---

## 2. Mathematical Formulations & Cost Functions

### 2.1 Dynamic Edge Cost Formula
The effective traversal time cost $c(e)$ of an edge $e$ is evaluated at query time using a `RouteContext`:

1. **Closed Segments:**
   $$\text{cost}(e) = \infty \quad \text{if } e.\text{is\_closed} \text{ and not } \text{ctx.ignore\_closures}$$
   *(Exported as `null` in JSON via `finite_or_none()` to avoid invalid `Infinity`).*

2. **Base Travel Time with Congestion:**
   $$\text{speed\_mps} = \frac{e.\text{speed\_limit\_kmph} \times 1000}{3600}$$
   $$\text{base}(e) = \left(\frac{e.\text{length\_meters}}{\max(\text{speed\_mps}, 0.1)}\right) \times \max(1.0, e.\text{congestion\_factor})$$

3. **Civilian Vehicles (`VehicleClass.CIVILIAN`):**
   $$\text{cost}(e) = \begin{cases} \text{base}(e) + \text{ctx.hold\_delay\_s} & \text{if } e.\text{road\_id} \in \text{ctx.held\_cross\_streets} \\ \text{base}(e) & \text{otherwise} \end{cases}$$
   *Notice: Civilian vehicles never receive speed discounts on emergency corridor segments.*

4. **Emergency Vehicles (`VehicleClass.EMERGENCY`):**
   $$\text{cost}_{\text{emg}}(e) = \frac{\text{base}(e)}{\text{SIREN\_SPEEDUP}} \times \begin{cases} 0.80 & \text{if } e.\text{road\_id} \in \text{ctx.corridor\_roads} \\ 1.00 & \text{otherwise} \end{cases}$$
   $$\text{cost}(e) = \max\left(\text{cost}_{\text{emg}}(e), \frac{\text{base}(e)}{\text{MAX\_COMBINED\_SPEEDUP}}\right)$$
   *Tuning Constants:*
   - `SIREN_SPEEDUP = 1.25` (~25% speedup with sirens).
   - `CORRIDOR_FACTOR = 0.80` (additional 20% speedup along green corridors).
   - `MAX_COMBINED_SPEEDUP = 2.00` (documented hard cap on maximum speedup: cost $\ge \text{base} / 2.0$).
   - `DEFAULT_HOLD_DELAY_SECONDS = 45.0` (delay added for civilian cross-traffic held red).

---

### 2.2 A* Heuristic Admissibility & Consistency
The A* algorithm uses a query-time Haversine distance heuristic:

$$h(n) = \text{haversine}(n, \text{destination}) \times r_{\min}$$
$$r_{\min} = \min_{e \in E_{\text{open}}} \left(\frac{\text{cost}(e, \text{ctx})}{e.\text{length\_meters}}\right)$$

* **Admissibility Proof:**
  Every road edge in `city_data.py` satisfies $e.\text{length\_meters} \ge 0.999 \times \text{haversine}(\text{source}, \text{target})$. For any valid path $P = (e_1, e_2, \dots, e_k)$ to destination:
  $$\text{cost}(P) = \sum_{i=1}^k \text{cost}(e_i) = \sum_{i=1}^k \left(\frac{\text{cost}(e_i)}{L(e_i)}\right) L(e_i) \ge r_{\min} \sum_{i=1}^k L(e_i) \ge r_{\min} \cdot \text{haversine}(n, \text{dest}) = h(n)$$
  Because $h(n) \le \text{cost}^*(n)$ under all congestion, siren, and corridor states, $h(n)$ is **strictly admissible**.
* **Consistency:** Triangle inequality holds: $h(u) \le c(u, v) + h(v)$.
* Verified across 200 random connected graphs where A* matched Dijkstra costs with zero deviations.

---

### 2.3 Emergency Responder Scoring (Adjusted ETA)
* **Definition of Adjusted ETA:** The estimated traversal time (in seconds) for a responder to travel from its current station node to the incident node, evaluated under emergency vehicle dynamics (`SIREN_SPEEDUP` and active corridors).
* **Scoring Formula:**
  $$\text{Score} = \frac{10000.0}{\text{Adjusted ETA (seconds)} + 1.0} + \text{Capability Bonuses}$$
  *Named Constants:*
  - `BONUS_ALS_EQUIPPED = 5.0` (Advanced Life Support equipment).
  - `BONUS_RESCUE_CUTTERS = 4.0` (Hydraulic extrication tools).
  - `BONUS_RAPID_RESPONSE = 3.0` (High-agility motorcycle/patrol unit).
  *Design Rationale:* Travel time strictly dominates the score. A unit with 60s ETA scores $\approx 163.9$, while a unit with 120s ETA scores $\approx 82.6$. A $+5.0$ bonus cannot displace a unit arriving even 5 seconds faster.

---

### 2.4 Anti-Fluttering Route Hysteresis
To prevent frequent flip-flopping of active routes when minor traffic fluctuations occur:
* When congestion updates or road closures occur, `engine.recompute_active_routes()` evaluates alternative paths.
* If the current active route is blocked ($\text{cost} = \infty$), it switches immediately.
* Otherwise, it only switches if the candidate route is at least **10% faster**:
  $$\frac{T_{\text{current}} - T_{\text{new}}}{T_{\text{current}}} \ge 0.10 \quad (10\% \text{ configurable threshold})$$

---

## 3. Road Network & Package Structure

```
UrbanFlow Project/
├── data/
│   ├── city_graph.json             # Seed topology JSON (nodes + edges)
│   ├── city_map.geojson            # GeoJSON RFC 7946 for Member 5 map
│   ├── emergency_units.json        # Seed emergency responders roster
│   └── sample_scenario_output.json # Sample end-to-end benchmark run
├── routing/
│   ├── __init__.py                 # Clean package exports
│   ├── models.py                   # Data models (Node, Edge, RoutePath, RouteContext, etc.)
│   ├── graph.py                    # CityGraph class, spatial queries, GeoJSON export
│   ├── algorithms.py               # Dijkstra, A*, Yen's K-Shortest Paths, Detour Search
│   ├── city_data.py                # 20-node Cyber City road network & responders
│   ├── emergency.py                # Unit ranking, corridor creation, diversion planning, simulation
│   ├── engine.py                   # Thread-safe UrbanFlowRoutingEngine API
│   ├── service.py                  # Plain dict service layer for Member 1
│   ├── schemas.py                  # Proposed v1 Pydantic v2 schemas
│   └── api.py                      # Ready-to-mount FastAPI APIRouter
├── tests/
│   └── test_routing_engine.py      # Unit test suite (18 tests, zero warnings)
├── demo_routing.py                 # Interactive terminal benchmark demonstration
└── export_graph_data.py            # Strict JSON asset exporter (allow_nan=False)
```

---

## 4. Proposed v1 API Contract for Member 1 (FastAPI)

Mount the router directly into Member 1's FastAPI application:
```python
from routing.api import router as routing_router

app.include_router(routing_router)
```

### Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/routing/route` | Computes primary route and alternative detours |
| `POST` | `/routing/emergency/dispatch` | Dispatches emergency unit & activates green corridor |
| `POST` | `/routing/closures` | Closes road segment(s) and computes diversion |
| `DELETE` | `/routing/closures/{road_id}` | Reopens road segment(s) and clears diversion |
| `POST` | `/routing/traffic` | Applies live or forecast congestion observations |
| `POST` | `/routing/diversion` | Generates civilian traffic diversion around blockage |
| `POST` | `/routing/simulate` | Simulates step-by-step vehicle trajectory frames |
| `GET` | `/routing/graph` | Returns standard GeoJSON for Mapbox / Leaflet |

### Service Layer Usage (Pure Python Dicts)
If integrating as a direct Python module without FastAPI:
```python
from routing.service import RoutingService

service = RoutingService()

# 1. Compute Route
route = service.compute_route(
    origin_node="INT-04",
    destination_node="INT-01",
    algorithm="astar",
    num_alternatives=2,
    is_emergency=False
)

# 2. Close Road with Upstream Diversion
closure_res = service.close_road(
    road_id="ROAD-03A",
    reason="multi_vehicle_collision",
    direction="both"
)
```

---

## 5. Map & Coordinate Standards for Member 5

* **GeoJSON Standard (RFC 7946):**
  - All coordinates in `data/city_map.geojson` and `/routing/graph` are strictly `[longitude, latitude]`.
  - Roads are `LineString` features: `[[source_lon, source_lat], [target_lon, target_lat]]`.
  - Road properties: `road_id`, `pair_id` (shared bidirectional identifier), `direction` (`"forward"` / `"reverse"`), `is_closed`, `congestion_factor`, `capacity_fraction`, `speed_limit_kmph`, `effective_travel_time_seconds` (`null` when closed).
* **API Point Responses:**
  - Route coordinates in `/routing/route` return `{"latitude": lat, "longitude": lon}` objects for developer convenience.

---

## 6. Verification & Test Suite

Run the full test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
*Output:*
```
Ran 18 tests in 0.083s — OK (All passed)
```

Run the interactive terminal demo:
```bash
python demo_routing.py
```
