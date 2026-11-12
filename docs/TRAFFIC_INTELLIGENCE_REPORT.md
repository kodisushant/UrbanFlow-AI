# UrbanFlow AI — Traffic Intelligence & Forecasting Report (Member 3)

> **Document Status:** Baseline architecture implemented and verified.  
> **Schema Status:** Proposed, pending confirmation with Members 1, 2 and 4.  
> **Author:** Member 3 (ML / Traffic Intelligence Engineer)  
> **Repository:** https://github.com/kodisushant/UrbanFlow-AI  
> **Branch:** `feat/traffic-forecast`

---

## 1. Existing ML or Traffic Analytics Code
- **Repository Inspection:** At the project kickoff, the repository contained no preexisting ML models or traffic intelligence codebase. 
- **Current State:** A modular, lightweight traffic intelligence package (`traffic_intelligence`) has been implemented featuring:
  - `models.py`: Pydantic schema validation for CCTV ingestion, current traffic state, 15m/30m forecast horizons, and route engine metadata.
  - `config.py`: Shared road profiles (`ROAD-01` through `ROAD-05`) ensuring train/serve consistency, plus timezone normalization (`Asia/Kolkata`).
  - `congestion_scorer.py`: Speed estimation, Passenger Car Unit (PCU) aggregation, multi-factor congestion scoring, and abnormal blockage identification.
  - `synthetic_data.py`: Clearly-labelled (`is_synthetic: True`) time-series traffic generator for calibration and honest testing.
  - `forecaster.py`: Dual-horizon Scikit-Learn Ridge regression engine with 5-minute lag features and rule-based cold-start fallback.
  - `pipeline.py`: Streaming observation processor with 5-minute interval bucketing/resampling, large-gap history resets (>15m), and intersection tracking.

---

## 2. Available Dependencies & Runtime Environment
Verified against the local system environment:
- **Python:** 3.13.12 (via Windows Python Launcher `py`)
- **Core ML & Data Science:**
  - `numpy>=1.26.0` (installed: 2.4.6)
  - `pandas>=2.0.0` (installed: 3.1.1)
  - `scikit-learn>=1.4.0` (installed: 1.9.0)
  - `scipy` (installed: 1.17.1)
  - `joblib` (installed: 1.5.3)
- **Validation & APIs:**
  - `pydantic>=2.0.0` (installed: 2.14.3)
  - `fastapi` (installed: 0.162.0)
  - `uvicorn` (installed: 0.54.0)
- **Repo Hygiene:** Managed via `requirements.txt` and `.gitignore`.

---

## 3. Required Input Data from Member 2 (Computer Vision / CCTV)
*Proposed, pending confirmation with Members 1, 2 and 4.*

Incoming observations are consumed per camera or simulation step via `CCTVObservation`:
```json
{
  "source_id": "cctv_cam_02",
  "road_id": "ROAD-02",
  "intersection_id": "INT-05",
  "timestamp": "2026-11-12T17:30:00+05:30",
  "vehicle_counts": {
    "car": 18,
    "motorcycle": 8,
    "bus": 2,
    "truck": 1
  },
  "total_vehicles": 29,
  "passenger_car_units": 30.5,
  "estimated_speed_kmph": 28.5,
  "stopped_vehicles_count": 1,
  "lane_occupancy_ratio": 0.58,
  "is_simulated": true
}
```
### Required Fields & Fallbacks:
- `road_id` & `intersection_id`: Matches Member 4's road network topology.
- `estimated_speed_kmph`: Observed vehicle speed in km/h. If optical tracking is unavailable (`None`), the scorer infers macroscopic speed using Greenshields model with stopped-vehicle queue penalties. If speed is `0.0` (dead stop), it is preserved and reported directly.
- `total_vehicles` / `vehicle_counts`: Converted into Passenger Car Units (PCU) via standard weights (`car=1.0`, `motorcycle=0.5`, `bus=3.0`, `truck=2.5`).
- `is_simulated`: Stored in provenance to maintain auditability.

---

## 4. Proposed Congestion Calculation & Anomaly Detection

### Composite Congestion Index ($CI \in [0.0, 1.0]$)
$$CI = 0.45 \cdot \left(\frac{\text{PCU}}{\text{Capacity}}\right) + 0.40 \cdot \left(\frac{v_0 - v}{v_0}\right) + 0.15 \cdot \left(\frac{N_{\text{stopped}}}{N_{\text{total}}}\right)$$
*(If visual lane occupancy is supplied by camera, weights re-balance to 0.35, 0.35, 0.15, 0.15).*

### Level Thresholds:
- **`low`**: $0.00 \le CI < 0.35$
- **`moderate`**: $0.35 \le CI < 0.65$
- **`heavy`**: $0.65 \le CI < 0.85$
- **`severe`**: $0.85 \le CI \le 1.00$

### Abnormal Congestion Detection:
Triggers `is_abnormal = True` when:
1. **Sudden Spike:** Rate of change $\Delta CI \ge 0.35$ within 5 to 15 minutes.
2. **Blockage / Stoppage:** $\ge 3$ stopped vehicles with observed speed $< 25\%$ of free-flow speed.

### Routing Multiplier & Penalties (for Member 4):
- Travel time multiplier: $M = \frac{v_0}{\max(3.0, v)}$ (clamped denominator prevents division by zero).
- Additive routing cost penalty: $W = 15.0 \cdot CI^2 + 35.0 \cdot (\text{if abnormal})$.
- Avoid recommendation: `recommended_avoid = True` if $CI \ge 0.85$ or (abnormal and $CI \ge 0.65$).

---

## 5. Proposed 15–30-Minute Forecasting Method

### Architecture:
A dual-horizon Ridge regressor ($\alpha=1.0$) predicting continuous congestion score at $t+15\text{m}$ (3 intervals) and $t+30\text{m}$ (6 intervals).

### Features (10-feature vector):
- Autoregressive lags: $CI_t, CI_{t-1}, CI_{t-2}, CI_{t-3}$ (5-minute resampled steps).
- Rolling metrics: 3-step moving average $\mu_{CI}$ and 15-minute trend $\Delta CI = CI_t - CI_{t-3}$.
- Current state: Observed speed $v_t$ and volume $\text{PCU}_t$.
- Time context: Cyclical hour encoding $[\sin(2\pi \cdot \text{hour}/24), \cos(2\pi \cdot \text{hour}/24)]$ normalized to `Asia/Kolkata`.

### Irregular Spacing & Cold Start Fallbacks:
- Observations arriving faster than 5 minutes (e.g. 10-second CCTV frames) are bucketed and averaged into 5-minute intervals.
- If a data gap $>15\text{ minutes}$ occurs, state history is reset to prevent stale lag distortion, and the pipeline executes a rule-based exponential decay fallback (`rule_based_fallback`).

---

## 6. Expected JSON Output
*Proposed, pending confirmation with Members 1, 2 and 4.*

```json
{
  "road_id": "ROAD-02",
  "intersection_id": "INT-05",
  "timestamp": "2026-11-12T17:45:00+05:30",
  "current_state": {
    "road_id": "ROAD-02",
    "intersection_id": "INT-05",
    "timestamp": "2026-11-12T17:45:00+05:30",
    "vehicle_count": 50,
    "passenger_car_units": 51.5,
    "estimated_speed_kmph": 0.0,
    "free_flow_speed_kmph": 45.0,
    "density_pcu_per_km": 103.0,
    "volume_capacity_ratio": 1.47,
    "congestion_score": 0.868,
    "congestion_level": "severe",
    "is_abnormal": true,
    "abnormal_reason": "Blockage detected: 6 stopped vehicles with speed 0.0 km/h"
  },
  "forecast": {
    "horizon_15m": {
      "horizon_minutes": 15,
      "predicted_timestamp": "2026-11-12T18:00:00+05:30",
      "predicted_congestion_score": 0.622,
      "predicted_congestion_level": "moderate",
      "predicted_speed_kmph": 21.2,
      "heuristic_confidence": 0.78
    },
    "horizon_30m": {
      "horizon_minutes": 30,
      "predicted_timestamp": "2026-11-12T18:15:00+05:30",
      "predicted_congestion_score": 0.655,
      "predicted_congestion_level": "heavy",
      "predicted_speed_kmph": 19.9,
      "heuristic_confidence": 0.65
    }
  },
  "routing_metadata": {
    "travel_time_multiplier": 15.0,
    "penalty_weight": 46.3,
    "recommended_avoid": true
  },
  "forecast_reliability": "low_during_incident",
  "data_provenance": {
    "module": "traffic_intelligence",
    "model_version": "v1.0-ridge-dual-horizon",
    "training_data": "synthetic",
    "forecast_type": "model_prediction",
    "forecast_reliability": "low_during_incident",
    "is_synthetic": "true",
    "history_points": "4"
  }
}
```

---

## 7. Testing, Evaluation & Metric Honesty

### Automated Unit Test Suite
14 automated unit tests in `tests/test_traffic_intelligence.py` verify:
- Dead-stop handling (`speed=0.0` preserves 0.0 without treating as missing).
- Road profile consistency between training generator and live scorer.
- Timezone handling: mixing aware (e.g. UTC/Z) and naive timestamps.
- Irregular spacing: bucketing 10-second inputs and resetting history after gaps $>15$ minutes.
- Support for intersection-level output and keying.
- Heuristic confidence property bounds.
- Spike anomaly thresholds: normal ramp-up (0.194 $\to$ 0.544) is NOT abnormal; severe jump (0.30 $\to$ 0.78) IS abnormal.
- Forecast reliability tri-state flags (`normal`, `low_during_incident`, `low_cold_start`).

### Held-out Evaluation on Unseen Synthetic Data (Real Measured Numbers)
- **Training Set:** 3 days (4,320 observations, random seed 42)
- **Held-out Evaluation Set:** 2 days (2,880 observations, random seed 999, unseen by model)
- **Evaluation Transitions:** 2,835 transitions

| Horizon | Ridge Model MAE | Ridge Model RMSE | Naive Persistence MAE | Naive Persistence RMSE | Improvement over Persistence |
|---|---|---|---|---|---|
| **15 Minutes** | **0.0767** | **0.0973** | 0.0909 | 0.1173 | **+15.62%** |
| **30 Minutes** | **0.0876** | **0.1105** | 0.1007 | 0.1293 | **+13.01%** |

*(Note: These figures represent held-out empirical evaluation on synthetic time-series data. In-sample training error is never reported as forecast accuracy).*

---

## 8. Known Limitations & Feature Ablation Study
1. **Limited Incident Data:** The model has little incident data to learn from (in our synthetic dataset, incidents account for exactly **0.23% of training rows** [10 / 4,320], **0.35% of held-out test rows** [10 / 2,880], and **0.28% overall** [20 / 7,200]). Consequently, during unexpected collisions, the baseline regressor can under-predict congestion.
2. **Feature Ablation Experiment (Measured Numbers):**
   - **Baseline (10 features):** Overall 15m MAE = **0.0767**, RMSE = **0.0973** | 30m MAE = **0.0876**, RMSE = **0.1105**
   - **Extended (12 features with `stopped_ratio` & `is_abnormal`):** Overall 15m MAE = **0.0767**, RMSE = **0.0973** | 30m MAE = **0.0876**, RMSE = **0.1105**
   - **Incident-Window Only (16 rows within 30 min of an incident):** Baseline 15m MAE = 0.0542, 30m MAE = 0.0538 vs Extended 15m MAE = 0.0528, 30m MAE = 0.0585.
   Because the extended model produced identical overall held-out MAE and deteriorated on 30m incident RMSE (0.0706 vs 0.0641), the simpler 10-feature baseline was retained.
3. **Data Provenance:** Training was performed on simulated/synthetic series. Field `data_provenance["is_synthetic"]` transparently mirrors whether the incoming observation is simulated. Field `forecast_reliability` explicitly flags when confidence is degraded (`low_during_incident`, `low_cold_start`).
