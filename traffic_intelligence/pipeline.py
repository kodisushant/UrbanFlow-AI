"""
UrbanFlow AI - Traffic Intelligence Pipeline
Orchestrates observation ingestion, state evaluation, anomaly detection,
5-minute interval bucketing/resampling, 15-30m forecasting, and formatting output.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import copy
import numpy as np

from traffic_intelligence.models import (
    CCTVObservation,
    CongestionLevel,
    CurrentTrafficState,
    TrafficIntelligenceOutput,
)
from traffic_intelligence.congestion_scorer import CongestionScorer
from traffic_intelligence.forecaster import TrafficForecaster
from traffic_intelligence.synthetic_data import generate_synthetic_traffic_series
from traffic_intelligence.config import DEFAULT_TIMEZONE, normalize_timestamp


class TrafficIntelligencePipeline:
    """
    Main entry point for Member 3's Traffic Intelligence module.
    Handles irregular spacing via 5-minute bucketing, timezone normalization,
    and supports both road-segment and intersection keys.
    """

    def __init__(
        self,
        road_configs: Optional[Dict[str, dict]] = None,
        auto_calibrate: bool = True,
        timezone: str = DEFAULT_TIMEZONE
    ):
        self.timezone = timezone
        self.scorer = CongestionScorer(road_configs=road_configs)
        self.forecaster = TrafficForecaster()

        # Key: (road_id, intersection_id)
        # Value: list of aggregated 5-minute bucket CurrentTrafficState
        self.bucketed_history: Dict[Tuple[str, Optional[str]], List[CurrentTrafficState]] = {}

        # In-progress bucket tracking: key -> (bucket_timestamp, [samples])
        self._active_bucket: Dict[Tuple[str, Optional[str]], Tuple[datetime, List[CurrentTrafficState]]] = {}

        if auto_calibrate:
            self.calibrate_with_synthetic_data()

    def calibrate_with_synthetic_data(self, days: int = 2, random_seed: int = 42):
        """
        Calibrates and fits the ML forecaster using synthetic baseline traffic time series.
        """
        df_synthetic = generate_synthetic_traffic_series(days=days, interval_minutes=5, random_seed=random_seed)
        self.forecaster.fit(df_synthetic, interval_minutes=5)

    def _get_bucket_time(self, dt: datetime) -> datetime:
        """Truncates timestamp to start of 5-minute window."""
        normalized = normalize_timestamp(dt, self.timezone)
        minute_bucket = (normalized.minute // 5) * 5
        return normalized.replace(minute=minute_bucket, second=0, microsecond=0)

    def _aggregate_bucket_samples(
        self,
        samples: List[CurrentTrafficState],
        bucket_time: datetime
    ) -> CurrentTrafficState:
        """Averages multiple intra-bucket observations into a single representative state."""
        if not samples:
            raise ValueError("No samples to aggregate")

        first = samples[0]
        avg_pcu = float(np.mean([s.passenger_car_units for s in samples]))
        avg_speed = float(np.mean([s.estimated_speed_kmph for s in samples]))
        avg_score = float(np.mean([s.congestion_score for s in samples]))
        avg_density = float(np.mean([s.density_pcu_per_km for s in samples]))
        avg_vc = float(np.mean([s.volume_capacity_ratio for s in samples]))
        total_veh = int(round(np.mean([s.vehicle_count for s in samples])))
        is_abn = any(s.is_abnormal for s in samples)
        abn_reason = next((s.abnormal_reason for s in samples if s.abnormal_reason), None)

        level = self.scorer.categorize_congestion(avg_score)

        return CurrentTrafficState(
            road_id=first.road_id,
            intersection_id=first.intersection_id,
            timestamp=bucket_time,
            vehicle_count=total_veh,
            passenger_car_units=round(avg_pcu, 2),
            estimated_speed_kmph=round(avg_speed, 1),
            free_flow_speed_kmph=first.free_flow_speed_kmph,
            density_pcu_per_km=round(avg_density, 2),
            volume_capacity_ratio=round(avg_vc, 2),
            congestion_score=round(avg_score, 3),
            congestion_level=level,
            is_abnormal=is_abn,
            abnormal_reason=abn_reason
        )

    def process_observation(self, observation: CCTVObservation) -> TrafficIntelligenceOutput:
        """
        Processes an incoming CCTV / simulator observation:
        1. Normalizes timestamp to configured timezone (Asia/Kolkata).
        2. Evaluates current state and routing metadata.
        3. Buckets/resamples to 5-minute intervals. Resets history if gap > 15 minutes.
        4. Predicts 15m and 30m forecasts (using model or rule-based fallback).
        5. Packages structured output with provenance.
        """
        # Normalize observation timestamp
        norm_ts = normalize_timestamp(observation.timestamp, self.timezone)
        # Create shallow copy with normalized timestamp for evaluation
        norm_obs = observation.model_copy(update={"timestamp": norm_ts})

        # 1. Current State & Routing Metadata
        current_state, routing_meta = self.scorer.evaluate(norm_obs)

        # 2. Key by (road_id, intersection_id)
        key = (observation.road_id, observation.intersection_id)
        bucket_time = self._get_bucket_time(norm_ts)

        history = self.bucketed_history.setdefault(key, [])

        if key not in self._active_bucket:
            # First observation for this key
            self._active_bucket[key] = (bucket_time, [current_state])
        else:
            active_time, samples = self._active_bucket[key]
            if bucket_time == active_time:
                # Same 5-minute bucket: accumulate sample
                samples.append(current_state)
            elif bucket_time > active_time:
                # New bucket started. Finalize previous bucket
                gap_minutes = (bucket_time - active_time).total_seconds() / 60.0
                if gap_minutes > 15.0:
                    # Gap between buckets is larger than 15 minutes: reset history
                    history.clear()
                else:
                    # Commit aggregated state to history
                    aggregated_state = self._aggregate_bucket_samples(samples, active_time)
                    history.append(aggregated_state)
                    if len(history) > 20:
                        history.pop(0)

                # Start new active bucket
                self._active_bucket[key] = (bucket_time, [current_state])

        # 3. Assemble state sequence for forecaster: history + current observation
        states_for_forecast = list(history) + [current_state]

        # 4. 15-30 Minute Congestion Forecast
        forecast_result, forecast_type = self.forecaster.predict(states_for_forecast)

        # 5. Determine forecast reliability flag
        if current_state.is_abnormal:
            reliability = "low_during_incident"
        elif forecast_type == "rule_based_fallback":
            reliability = "low_cold_start"
        else:
            reliability = "normal"

        # 6. Construct complete output payload
        return TrafficIntelligenceOutput(
            road_id=observation.road_id,
            intersection_id=observation.intersection_id,
            timestamp=norm_ts,
            current_state=current_state,
            forecast=forecast_result,
            routing_metadata=routing_meta,
            forecast_reliability=reliability,
            data_provenance={
                "module": "traffic_intelligence",
                "model_version": "v1.0-ridge-dual-horizon",
                "training_data": "synthetic",
                "forecast_type": forecast_type,
                "forecast_reliability": reliability,
                "is_synthetic": str(observation.is_simulated).lower(),
                "history_points": str(len(states_for_forecast))
            }
        )

    def reset_history(self):
        """Clears stored temporal state history and active buckets."""
        self.bucketed_history.clear()
        self._active_bucket.clear()
        self.scorer._history.clear()
