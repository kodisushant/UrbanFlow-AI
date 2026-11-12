"""
UrbanFlow AI - Traffic Intelligence Demo & Verification Runner (Member 3)
Demonstrates:
  1. Calibration on synthetic training dataset (seed 42)
  2. Honest held-out evaluation on unseen synthetic series (seed 999) vs Naive Persistence Baseline
  3. Real-time streaming observation processing with 5-minute interval bucketing
  4. Congestion scoring and abnormal blockage identification
  5. 15-minute and 30-minute dual-horizon machine learning forecasts
  6. Routing metadata and penalty output for Member 4
  7. Data provenance formatting
"""

from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo
from traffic_intelligence import (
    CCTVObservation,
    TrafficIntelligencePipeline,
    generate_synthetic_traffic_series,
    DEFAULT_TIMEZONE,
)


def main():
    print("=================================================================")
    print("  UrbanFlow AI — Member 3 (Traffic Intelligence & Forecasting)   ")
    print("=================================================================\n")

    tz = ZoneInfo(DEFAULT_TIMEZONE)

    # 1. Dataset Generation: Train & Held-out Evaluation
    print("[1] Generating Synthetic Datasets for Training & Honest Evaluation...")
    df_train = generate_synthetic_traffic_series(days=3, random_seed=42)
    df_heldout = generate_synthetic_traffic_series(days=2, random_seed=999)
    print(f"    - Training Series: {len(df_train)} observations across {len(df_train['road_id'].unique())} roads (Seed 42)")
    print(f"    - Held-out Evaluation Series: {len(df_heldout)} observations (Seed 999, Unseen by model)\n")

    # 2. Pipeline Initialization & Model Training
    pipeline = TrafficIntelligencePipeline(auto_calibrate=False, timezone=DEFAULT_TIMEZONE)
    pipeline.forecaster.fit(df_train, interval_minutes=5)

    # 3. Held-out Evaluation vs Naive Persistence Baseline
    print("[2] Held-Out Evaluation vs Naive Persistence Baseline (Real Measured Numbers):")
    eval_metrics = pipeline.forecaster.evaluate(df_heldout, interval_minutes=5)
    print(f"    - Evaluated on {int(eval_metrics['test_samples'])} held-out step transitions:")
    print("    --- 15-Minute Horizon ---")
    print(f"      Ridge Model MAE:        {eval_metrics['model_mae_15m']:.4f} | RMSE: {eval_metrics['model_rmse_15m']:.4f}")
    print(f"      Persistence Baseline:   {eval_metrics['persistence_mae_15m']:.4f} | RMSE: {eval_metrics['persistence_rmse_15m']:.4f}")
    improvement_15m = ((eval_metrics['persistence_mae_15m'] - eval_metrics['model_mae_15m']) / eval_metrics['persistence_mae_15m']) * 100.0
    print(f"      Improvement over Naive: {improvement_15m:+.2f}%")
    print("    --- 30-Minute Horizon ---")
    print(f"      Ridge Model MAE:        {eval_metrics['model_mae_30m']:.4f} | RMSE: {eval_metrics['model_rmse_30m']:.4f}")
    print(f"      Persistence Baseline:   {eval_metrics['persistence_mae_30m']:.4f} | RMSE: {eval_metrics['persistence_rmse_30m']:.4f}")
    improvement_30m = ((eval_metrics['persistence_mae_30m'] - eval_metrics['model_mae_30m']) / eval_metrics['persistence_mae_30m']) * 100.0
    print(f"      Improvement over Naive: {improvement_30m:+.2f}%\n")

    # 4. Stream Observations: Free-flow -> Density building -> Peak rush -> Incident blockage
    base_time = datetime(2026, 11, 12, 17, 30, 0, tzinfo=tz)
    scenarios = [
        {
            "desc": "T0 (17:30): Free flow traffic (Late afternoon)",
            "obs": CCTVObservation(
                source_id="cctv_cam_02",
                road_id="ROAD-02",
                intersection_id="INT-05",
                timestamp=base_time,
                vehicle_counts={"car": 8, "motorcycle": 4, "bus": 1},
                total_vehicles=13,
                estimated_speed_kmph=42.0,
                stopped_vehicles_count=0,
                is_simulated=True
            )
        },
        {
            "desc": "T+5m (17:35): Density building up",
            "obs": CCTVObservation(
                source_id="cctv_cam_02",
                road_id="ROAD-02",
                intersection_id="INT-05",
                timestamp=base_time + timedelta(minutes=5),
                vehicle_counts={"car": 18, "motorcycle": 8, "bus": 2, "truck": 1},
                total_vehicles=29,
                estimated_speed_kmph=28.5,
                stopped_vehicles_count=1,
                is_simulated=True
            )
        },
        {
            "desc": "T+10m (17:40): Peak rush hour density",
            "obs": CCTVObservation(
                source_id="cctv_cam_02",
                road_id="ROAD-02",
                intersection_id="INT-05",
                timestamp=base_time + timedelta(minutes=10),
                vehicle_counts={"car": 26, "motorcycle": 12, "bus": 3, "truck": 2},
                total_vehicles=43,
                estimated_speed_kmph=18.0,
                stopped_vehicles_count=2,
                is_simulated=True
            )
        },
        {
            "desc": "T+15m (17:45): Incident Blockage (Stalled vehicle / potential collision)",
            "obs": CCTVObservation(
                source_id="cctv_cam_02",
                road_id="ROAD-02",
                intersection_id="INT-05",
                timestamp=base_time + timedelta(minutes=15),
                vehicle_counts={"car": 30, "motorcycle": 15, "bus": 3, "truck": 2},
                total_vehicles=50,
                estimated_speed_kmph=0.0,  # Dead stop verified
                stopped_vehicles_count=6,
                is_simulated=True
            )
        }
    ]

    print("[3] Streaming observations and calculating live intelligence...\n")

    latest_output = None
    for step in scenarios:
        print(f"--- {step['desc']} ---")
        output = pipeline.process_observation(step["obs"])
        latest_output = output

        state = output.current_state
        f15 = output.forecast.horizon_15m
        f30 = output.forecast.horizon_30m
        route = output.routing_metadata
        prov = output.data_provenance

        print(f"  Observed: Road: {output.road_id} | Intersection: {output.intersection_id} | PCU: {state.passenger_car_units:.1f} | Speed: {state.estimated_speed_kmph:.1f} km/h")
        print(f"  State: Congestion Score: {state.congestion_score:.3f} ({state.congestion_level.value.upper()}) | Abnormal: {state.is_abnormal}")
        if state.is_abnormal:
            print(f"  ! ALERT: {state.abnormal_reason}")
        print(f"  Forecast 15m -> Score: {f15.predicted_congestion_score:.3f} ({f15.predicted_congestion_level.value}) | Speed: {f15.predicted_speed_kmph:.1f} km/h | Heuristic Conf: {f15.heuristic_confidence:.2f}")
        print(f"  Forecast 30m -> Score: {f30.predicted_congestion_score:.3f} ({f30.predicted_congestion_level.value}) | Speed: {f30.predicted_speed_kmph:.1f} km/h | Heuristic Conf: {f30.heuristic_confidence:.2f}")
        print(f"  Route Metadata: Multiplier: {route.travel_time_multiplier:.2f}x | Penalty: {route.penalty_weight:.1f} | Recommend Avoid: {route.recommended_avoid}")
        print(f"  Reliability: {output.forecast_reliability} | Provenance: {prov['forecast_type']} | is_synthetic: {prov['is_synthetic']} | training_data: {prov['training_data']}\n")

    print("[4] Final Structured JSON Output for Backend (Member 1 & Member 4):")
    if latest_output:
        formatted_json = json.dumps(latest_output.model_dump(mode="json"), indent=2)
        print(formatted_json)


if __name__ == "__main__":
    main()
