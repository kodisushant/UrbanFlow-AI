# UrbanFlow AI — Team Execution & Agent Handoff Plan

Repository: https://github.com/kodisushant/UrbanFlow-AI

## 1. What we are building

UrbanFlow AI is an adaptive urban traffic intelligence and emergency-response prototype.

It combines:
- **Machine Learning:** forecast traffic congestion 15–30 minutes ahead using historical or simulated traffic observations.
- **Deep Learning / Computer Vision:** analyse CCTV or pre-recorded traffic video to detect and track vehicles and identify *potential* incidents or road blockages.
- **Graph optimization:** represent roads and intersections as a weighted graph and calculate routes using Dijkstra or A*.
- **Agentic AI:** use cooperating agents with clear responsibilities to interpret traffic and incident data, recommend emergency responses, coordinate routing and explain decisions.
- **Interactive simulation and dashboard:** show roads, traffic, incidents, emergency units, routes, diversions and signal-priority actions on a map.

### Main end-to-end demonstration

1. A CCTV video or simulated traffic feed is processed.
2. The vision pipeline detects vehicles and produces traffic observations. It flags a **potential** collision/blockage for review; it must not claim certainty from an unverified visual cue.
3. The incident workflow records the location, timestamp, camera/source, evidence snapshot and confidence, then creates a structured incident report.
4. The incident-analysis logic classifies the incident and estimates urgency using explicit rules/model outputs.
5. The emergency-coordination agent recommends the appropriate service(s): ambulance, fire service and/or police. A sample resource registry provides unit locations and simulated availability.
6. The routing engine uses the road graph, closures and congestion weights to find an appropriate route and alternatives.
7. The traffic agent proposes diversions for general traffic and signal priority along the emergency route in the **simulation**.
8. The dashboard shows the incident, evidence, report, recommended/assigned resources, route, diversion and the reasons behind the decisions.

**Important prototype boundary:** This is a hackathon simulation, not a live emergency-dispatch system. Do not contact real emergency services, control real traffic signals, or imply that simulated hospital/service availability is live. Human/operator confirmation should be required before any dispatch action. Clearly label simulated data and model predictions.

## 2. Product modules

1. **Video / CCTV analysis**
   - Accept a pre-recorded video first; live camera support is optional.
   - Detect vehicle classes and track vehicles across frames if feasible.
   - Produce timestamped detections and traffic observations.
   - Flag potential accident/blockage events with evidence and confidence.
2. **Traffic intelligence**
   - Aggregate vehicle counts/speeds/density by road segment or intersection.
   - Estimate congestion.
   - Provide a simple 15–30 minute forecast using a baseline model or clearly labelled simulated time series.
3. **Incident management**
   - Create, update, verify and close incident records.
   - Store type, location, time, source, severity/priority, confidence, evidence and status.
   - Generate a readable report from structured facts; never let an LLM invent injuries, casualties or damage.
4. **Emergency resources**
   - Seed a small dataset of ambulances, fire engines and police units.
   - Track type, location, availability and simulated status.
   - Recommend appropriate units based on incident type, distance, availability and capability.
5. **Road graph and optimization**
   - Model intersections as nodes and roads as edges.
   - Give edges travel-time/congestion weights and closure state.
   - Calculate primary and alternative routes with Dijkstra or A*.
   - Apply simulated diversion and emergency signal priority.
6. **Agent orchestration**
   - Traffic agent: summarize traffic state and forecast.
   - Incident agent: evaluate candidate events and create/update incident records.
   - Emergency coordination agent: recommend suitable services/resources.
   - Route/optimization agent: request routes, alternatives and diversion recommendations.
   - Coordinator: pass structured state between agents, handle workflow and provide explanations.
   - Agents should call deterministic tools/services for calculations. Do not rely on an LLM to calculate shortest paths or fabricate observations.
7. **Dashboard and map simulation**
   - Show map/graph, traffic levels, incident markers, units, routes and closures.
   - Show incident report and evidence.
   - Show agent activity/reasoning summaries and recommended actions.
   - Provide controls to run a sample scenario and advance/reset simulation.

## 3. Team of five — ownership and deliverables

Each member owns a module, its tests and its integration contract. All members use their preferred coding agent (Antigravity, Codex, Cursor or another tool), but the human owner must review generated code, run it and resolve conflicts.

### Member 1 — Team Lead / Backend Integration / Agent Orchestration

**Owns:** shared backend architecture, API contracts, workflow orchestration and integration.

Tasks:
- Inspect the existing repository before changing anything.
- Agree on the stack and folder structure with the team before implementation.
- Create/maintain the shared data models and API contract.
- Implement the coordinator/workflow that connects incident, traffic, resource and routing modules.
- Implement agent interfaces and structured hand-offs; keep routing and other deterministic logic in normal code.
- Add endpoints for scenario execution, incident workflow and dashboard data.
- Integrate modules from Members 2–5 and resolve interface mismatches.
- Add basic logging, error handling, configuration and run instructions.
- Own the final end-to-end demo and integration branch.

Deliverables:
- Architecture and API contract.
- Working end-to-end scenario endpoint/workflow.
- Agent coordination and explainable action summary.
- Integrated backend startup instructions.

### Member 2 — Computer Vision / CCTV Analysis

**Owns:** video ingestion, vehicle detection/tracking and candidate incident signals.

Tasks:
- Start with one or two suitable pre-recorded traffic clips; do not depend on live CCTV access.
- Set up a practical pretrained object detector (for example, a compatible YOLO model) and OpenCV video processing.
- Detect vehicles and, if feasible, track them across frames.
- Calculate simple observations such as vehicle counts, stopped vehicles or lane/region occupancy.
- Implement a conservative candidate-incident heuristic or use a suitable pretrained capability if available.
- Return structured observations with video timestamp, bounding boxes/classes, confidence and evidence-frame path/reference.
- Clearly distinguish `potential_incident` from a verified accident.
- Provide a small test video or sample output and document hardware/model requirements.

Deliverables:
- Video-processing module or service.
- Structured detection/traffic observation JSON.
- Evidence snapshot generation.
- Demo clip and test instructions.

### Member 3 — Traffic Intelligence / ML Forecasting

**Owns:** traffic aggregation, congestion scoring and 15–30-minute forecast.

Tasks:
- Define the input format for traffic observations per road segment/intersection.
- Build a congestion score from available features such as vehicle count, estimated speed and occupancy.
- Implement a feasible baseline forecast (e.g. moving average/regression or a small model) using available historical or generated time-series data.
- If there is insufficient real data, generate clearly labelled synthetic data and explain its limitations.
- Return forecast horizon, predicted congestion level/value and confidence/limitations.
- Supply congestion weights to the routing module through the agreed API/data contract.
- Add tests for low, moderate and heavy traffic cases.

Deliverables:
- Traffic aggregation/congestion module.
- 15- and 30-minute forecast output.
- Sample dataset and evaluation/limitations note.
- Tests and API/interface documentation.

### Member 4 — Road Graph / Emergency Routing / Diversion

**Owns:** map graph, route optimization, emergency resource selection support and traffic-control simulation logic.

Tasks:
- Build a small, deterministic road network (roughly 15–30 intersections) for the demo.
- Define nodes, edges, travel times, congestion weights and road-closure state.
- Implement Dijkstra or A* for primary and alternative routes.
- Recalculate routes when an incident blocks a road or congestion weights change.
- Implement a simple resource-ranking helper using unit type, availability, distance and capability; coordinate its interface with Member 1.
- Simulate general-traffic diversion and emergency corridor/signal priority; do not control real signals.
- Return route geometry/node sequence, estimated cost/time, excluded roads and a human-readable explanation.

Deliverables:
- Road graph and route engine.
- Alternative-route support.
- Diversion and signal-priority simulation.
- Test scenarios and route API documentation.

### Member 5 — Frontend / Interactive Map / Command Dashboard

**Owns:** user interface and visual demonstration.

Tasks:
- Inspect the existing repository and align with the agreed frontend stack.
- Build a command dashboard with traffic overview, incident list, emergency units and system status.
- Build an interactive map or graph visualization showing intersections, road status, incidents, units, primary/alternative routes and diversions.
- Add a CCTV/video panel with detection overlays or evidence snapshots where feasible.
- Add incident details/report view and emergency recommendation/dispatch simulation controls.
- Show clear labels for simulated data, predicted values and unverified candidate incidents.
- Connect to backend APIs using the agreed contracts; use a temporary mock adapter only until APIs are ready.
- Add a scenario start/reset control and ensure the main demo flow is easy to operate.

Deliverables:
- Working dashboard and map.
- Incident report/evidence panel.
- Emergency route/diversion visualization.
- Setup instructions and a polished demo flow.

## 4. Shared repository and Git workflow

**All code must go into:** https://github.com/kodisushant/UrbanFlow-AI

### Before coding
1. One person checks the repository structure, current branch, README and existing code.
2. Team Lead posts the agreed stack, folder ownership, API contracts and naming conventions.
3. Each member creates a separate feature branch from the latest `main`.
4. Do not let multiple agents edit the same files unless coordinated.

Suggested branches:
- `feat/backend-orchestration`
- `feat/cctv-vision`
- `feat/traffic-forecast`
- `feat/route-optimization`
- `feat/dashboard`

### Daily / continuous Git loop
```bash
git clone https://github.com/kodisushant/UrbanFlow-AI.git
cd UrbanFlow-AI

git checkout main
git pull origin main
git checkout -b feat/your-module
```

Commit and push:
```bash
git status
git add <your-owned-files>
git commit -m "feat: implement <module>"
git push -u origin feat/your-module
```

Before integrating latest changes:
```bash
git fetch origin
git pull --rebase origin main
```

Then open a Pull Request into `main`. Team Lead reviews and merges after the module runs and its contract/tests pass.

**Rules**
- Never force-push to `main`.
- Never commit `.env`, API keys, credentials, private CCTV footage or large model weights.
- Add `.env.example` with placeholder variable names only.
- Add generated datasets/videos/model files to `.gitignore` or use small documented sample assets.
- Keep commits small and descriptive.
- Do not overwrite another member's work. Coordinate before shared-file edits.
- If a merge conflict occurs, the owners of the affected files resolve it together.
- Pull latest `main` regularly, especially before starting a new task.
- Every PR must state what changed, how to run it, tests performed and known limitations.

## 5. Shared interfaces — agree before parallel development

Use these conceptual contracts even if the exact endpoint names change.

### Incident object
```json
{
  "incident_id": "INC-001",
  "type": "possible_collision",
  "status": "detected_unverified",
  "latitude": 17.0000,
  "longitude": 78.0000,
  "timestamp": "ISO-8601",
  "source": "cctv_camera_01",
  "confidence": 0.0,
  "severity": "unknown",
  "evidence": [],
  "affected_road_ids": []
}
```

### Traffic observation
```json
{
  "road_id": "ROAD-01",
  "timestamp": "ISO-8601",
  "vehicle_count": 12,
  "estimated_speed_kmph": 18,
  "congestion_level": "heavy",
  "source": "simulation_or_cctv"
}
```

### Emergency resource
```json
{
  "unit_id": "AMB-01",
  "type": "ambulance",
  "latitude": 17.0000,
  "longitude": 78.0000,
  "availability": "available",
  "capabilities": ["basic_life_support"]
}
```

### Route result
```json
{
  "unit_id": "AMB-01",
  "incident_id": "INC-001",
  "algorithm": "astar",
  "road_ids": ["ROAD-01", "ROAD-04"],
  "estimated_travel_time_seconds": 420,
  "blocked_roads_avoided": [],
  "alternative_routes": [],
  "explanation": "Selected route has the lowest estimated travel cost."
}
```

These are starter contracts, not final schemas. Team Lead must align field names, validation and coordinate conventions across all modules.

## 6. Suggested 12-hour schedule

| Time | Team focus | Expected outcome |
|---|---|---|
| 0:00–0:45 | All: inspect repo, agree stack/contracts, branch | No ambiguous interfaces |
| 0:45–3:00 | Parallel module implementation | Each module has a first runnable version |
| 3:00–5:00 | Complete core logic and tests | CV output, congestion, routes, dashboard skeleton |
| 5:00–7:00 | Integrate APIs and shared data | Modules communicate end-to-end |
| 7:00–9:00 | Build the complete demo scenario | Incident → report → response → route/diversion |
| 9:00–10:30 | Fix bugs, improve UI and explanations | Stable demo |
| 10:30–11:30 | Rehearse, test reset/re-run, prepare fallback | Reliable presentation |
| 11:30–12:00 | Freeze features, final checks and pitch | Demo-ready build |

Do not spend the first hours building elaborate agent frameworks. Make the deterministic end-to-end workflow work first, then add agentic coordination around it.

## 7. Definition of done for the hackathon demo

The team should be able to demonstrate this single connected scenario:

1. Start the dashboard and load the sample city.
2. Play a sample CCTV clip or run the traffic simulation.
3. Show vehicle detections and traffic observations.
4. Trigger or detect a potential accident.
5. Create an incident record and evidence-backed report.
6. Verify the incident in the demo workflow.
7. Recommend the appropriate emergency service(s) and available sample unit(s).
8. Calculate the emergency route and at least one alternative.
9. Divert regular traffic and prioritize simulated signals.
10. Show all actions, statuses and explanations on the dashboard.

A feature is not complete merely because an agent generated code. It must run, connect to the shared workflow and be testable.

## 8. Instructions for every coding agent

Every member should give their coding agent the following constraints:
- First inspect the repository, README, existing code, package files and current Git state.
- Do not assume a framework, folder structure, API endpoint or dependency before inspecting the repo.
- Do not rewrite or delete existing project files without explaining why and getting team approval.
- Work only in the module assigned to that member.
- Coordinate shared contracts with the Team Lead; do not invent incompatible schemas.
- Prefer the smallest working implementation over unnecessary complexity.
- Add error handling and a minimal test or reproducible manual test.
- Do not hardcode secrets or claim simulated data is real.
- Before finishing, list files changed, commands run, tests/results, limitations and exact Git commands for the human owner.
- The member may commit and push their own feature branch after reviewing the diff and running checks. Never push directly to `main`; integrate through a Pull Request. The human owner should handle credentials, review and final merge.

## 9. Final product principle

**UrbanFlow AI does not just detect traffic problems. It turns traffic intelligence into coordinated, explainable response actions.**

The strongest demo is the complete chain:

**Observe → Detect → Verify → Classify → Coordinate → Optimize → Divert → Explain.**
