# UrbanFlow AI — Traffic Intelligence & ML Forecasting (Member 3)

Part of the **UrbanFlow AI** adaptive traffic and emergency response system.

## 1. Overview
The **Traffic Intelligence** module is responsible for:
- Ingesting vehicle detections and traffic observations from CCTV or traffic simulators (Member 2).
- Computing traffic density, passenger car units (PCU), speed estimations, and composite congestion indices.
- Identifying abnormal traffic congestion and road blockages.
- Providing 15-minute and 30-minute machine learning forecasts per road segment or intersection.
- Supplying travel time multipliers and routing penalties for route optimization (Member 4) and backend orchestration (Member 1).

---

## 2. Architecture & File Structure

```
c:\Users\supri\OneDrive\Documents\Desktop\Yutvik\
├── traffic_intelligence/
│   ├── __init__.py               # Package exports
│   ├── config.py                 # Shared ROAD_PROFILES, timezones & timestamp normalizer
│   ├── models.py                 # Pydantic schemas (CCTVObservation, Output, Forecast)
│   ├── congestion_scorer.py      # Density, Speed deficit, Queue penalty & Anomaly logic
│   ├── synthetic_data.py         # Calibrated synthetic traffic time-series generator
│   ├── forecaster.py             # 15m & 30m Dual-Horizon Ridge ML forecaster
│   └── pipeline.py               # Streaming coordinator with 5m bucketing & gap resets
├── tests/
│   └── test_traffic_intelligence.py  # Automated unit & integration tests
├── docs/
│   └── TRAFFIC_INTELLIGENCE_REPORT.md # Comprehensive Member 3 inspection & proposal report
├── run_demo.py                   # Verification and demonstration runner
├── requirements.txt              # Production and testing dependencies
├── .gitignore                    # Python hygiene ignore list
├── UrbanFlow_AI_Team_Plan.md     # Team Execution & Agent Handoff Plan
└── README.md                     # Module documentation
```

---

## 3. How to Run

### Run Unit Tests
```bash
py -m unittest discover -s tests -p "test_*.py" -v
```

### Run the Interactive Demo
```bash
py run_demo.py
```

---

## 4. Model Evaluation & Metric Honesty

> **Real Measured Metrics (Held-out Synthetic Data)**  
> The model is evaluated on an **unseen** synthetic time-series generated with a separate random seed (`seed=999`, 2,835 evaluation transitions) after training on `seed=42`. In-sample training errors are **never** reported as forecast accuracy.

| Horizon | Ridge Model MAE | Ridge Model RMSE | Naive Persistence MAE | Naive Persistence RMSE | Improvement vs Persistence |
|---|---|---|---|---|---|
| **15 Minutes Ahead** | **0.0767** | **0.0973** | 0.0909 | 0.1173 | **+15.62%** |
| **30 Minutes Ahead** | **0.0876** | **0.1105** | 0.1007 | 0.1293 | **+13.01%** |

### Confidence Score Definition:
`heuristic_confidence` is a heuristic score $[0.0, 1.0]$ derived from recent temporal volatility (or a fixed cold-start value), **NOT** an empirical probability.

### Data Provenance:
- `data_provenance["training_data"]`: Always `"synthetic"` as models are trained on calibrated synthetic traffic series.
- `data_provenance["is_synthetic"]`: Reflects whether the incoming observation itself was marked `is_simulated: true`.
- `data_provenance["forecast_type"]`: Either `"model_prediction"` or `"rule_based_fallback"` (during cold start or following gaps $>15$ minutes).

---

## 5. Known Limitations
1. **Under-prediction during sudden incidents:** The baseline forecaster predicts continuous macroscopic traffic trends. Because sudden collisions are step-function anomalies rather than continuous patterns, the model may under-predict congestion in the initial minutes following an accident until downstream speed drops propagate into lag features.
2. **Feature Ablation Experiment:** Adding `stopped_ratio` and `is_abnormal` as linear regression features was tested; it did not improve held-out MAE ($0.0774$ vs $0.0774$) because incidents constitute $<2\%$ of overall data. The simpler, robust 10-feature baseline was retained.
3. **Simulated Road Network:** Calibrated on representative arterial segments (`ROAD-01` through `ROAD-05`). New roads can be added to `ROAD_PROFILES` in `traffic_intelligence/config.py`.

---

## 6. Integration Schemas (Proposed)

### Input (from Member 2 / CCTV)
```json
{
  "source_id": "cctv_cam_02",
  "road_id": "ROAD-02",
  "intersection_id": "INT-05",
  "timestamp": "2026-11-12T17:30:00+05:30",
  "vehicle_counts": {"car": 18, "motorcycle": 8, "bus": 2, "truck": 1},
  "total_vehicles": 29,
  "estimated_speed_kmph": 28.5,
  "stopped_vehicles_count": 1,
  "is_simulated": true
}
```

### Output (to Member 1 Backend & Member 4 Routing)
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
  "data_provenance": {
    "module": "traffic_intelligence",
    "model_version": "v1.0-ridge-dual-horizon",
    "training_data": "synthetic",
    "forecast_type": "model_prediction",
    "is_synthetic": "true",
    "history_points": "4"
  }
}
```
