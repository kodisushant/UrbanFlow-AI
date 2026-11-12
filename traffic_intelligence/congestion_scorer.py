"""
UrbanFlow AI - Traffic Congestion Scorer
Computes density, speeds, multi-factor congestion levels,
identifies abnormal congestion spikes, and produces routing multipliers for Member 4.
"""

from datetime import datetime
from typing import Dict, Optional, Tuple
from traffic_intelligence.models import (
    CCTVObservation,
    CongestionLevel,
    CurrentTrafficState,
    RoutingMetadata,
)
from traffic_intelligence.config import DEFAULT_ROAD_CONFIG, ROAD_PROFILES

# Passenger Car Unit (PCU) standard conversion factors
DEFAULT_PCU_WEIGHTS = {
    "car": 1.0,
    "motorcycle": 0.5,
    "bus": 3.0,
    "truck": 2.5,
    "auto_rickshaw": 0.75,
    "bicycle": 0.2,
}


class CongestionScorer:
    """
    Evaluates real-time traffic observations, calculates density and congestion levels,
    detects anomalies, and supplies routing penalties.
    """

    def __init__(self, road_configs: Optional[Dict[str, dict]] = None):
        """
        Args:
            road_configs: Optional dictionary mapping road_id -> custom road parameters.
                          Defaults to shared ROAD_PROFILES.
        """
        self.road_configs = dict(ROAD_PROFILES)
        if road_configs:
            self.road_configs.update(road_configs)
        # Stores recent history per segment/intersection for anomaly detection: {key: [(timestamp, score)]}
        self._history: Dict[str, list] = {}

    def get_road_config(self, road_id: str) -> dict:
        config = dict(DEFAULT_ROAD_CONFIG)
        if road_id in self.road_configs:
            config.update(self.road_configs[road_id])
        return config

    def calculate_pcu(self, observation: CCTVObservation) -> float:
        """Calculate total Passenger Car Units from vehicle breakdown or fallback to total count."""
        if observation.passenger_car_units is not None:
            return float(observation.passenger_car_units)

        if observation.vehicle_counts:
            pcu = 0.0
            for v_type, count in observation.vehicle_counts.items():
                weight = DEFAULT_PCU_WEIGHTS.get(v_type.lower(), 1.0)
                pcu += count * weight
            return round(pcu, 2)

        return float(observation.total_vehicles)

    def estimate_speed(
        self,
        observation: CCTVObservation,
        pcu: float,
        free_flow_speed: float,
        capacity_pcu: float,
        jam_pcu: float
    ) -> float:
        """
        Returns observed speed if available from CCTV tracking (including 0.0 for dead stop).
        If estimated_speed_kmph is None, infers speed using Greenshields macroscopic traffic flow model.
        """
        # Bug fix 1: Check `is not None` instead of `> 0` so 0.0 (dead stop) is reported directly
        if observation.estimated_speed_kmph is not None:
            return min(max(0.0, float(observation.estimated_speed_kmph)), free_flow_speed * 1.2)

        # Fallback estimation: v = v_0 * max(0.1, 1 - (k / k_jam))
        density_ratio = min(1.0, pcu / max(jam_pcu, 1.0))
        estimated = free_flow_speed * max(0.12, 1.0 - density_ratio)

        # Extra penalty if stopped vehicles are present
        if observation.stopped_vehicles_count > 0:
            stop_penalty = min(0.6, (observation.stopped_vehicles_count / max(observation.total_vehicles, 1)) * 0.8)
            estimated *= (1.0 - stop_penalty)

        return round(max(0.0, estimated), 1)

    def compute_congestion_score(
        self,
        pcu: float,
        speed: float,
        free_flow_speed: float,
        capacity_pcu: float,
        stopped_count: int,
        total_vehicles: int,
        lane_occupancy: Optional[float]
    ) -> float:
        """
        Calculates normalized Congestion Index CI in [0.0, 1.0] using a composite formula:
        CI = 0.45 * (V/C) + 0.40 * Speed_Deficit + 0.15 * Queue_Penalty
        """
        # 1. Volume-to-Capacity ratio (capped at 1.0 for index)
        vc_ratio = min(1.0, pcu / max(capacity_pcu, 1.0))

        # 2. Speed deficit ratio: (v_0 - v) / v_0
        speed_deficit = max(0.0, (free_flow_speed - speed) / max(free_flow_speed, 1.0))

        # 3. Queue / Stopped vehicle penalty
        if total_vehicles > 0:
            queue_penalty = min(1.0, stopped_count / total_vehicles)
        else:
            queue_penalty = 0.0

        # Optional visual lane occupancy boost if camera reported it
        if lane_occupancy is not None:
            score = (0.35 * vc_ratio) + (0.35 * speed_deficit) + (0.15 * queue_penalty) + (0.15 * lane_occupancy)
        else:
            score = (0.45 * vc_ratio) + (0.40 * speed_deficit) + (0.15 * queue_penalty)

        return round(float(min(1.0, max(0.0, score))), 3)

    def categorize_congestion(self, score: float) -> CongestionLevel:
        """Maps continuous score [0, 1] to discrete level."""
        if score < 0.35:
            return CongestionLevel.LOW
        elif score < 0.65:
            return CongestionLevel.MODERATE
        elif score < 0.85:
            return CongestionLevel.HEAVY
        else:
            return CongestionLevel.SEVERE

    def check_abnormal_congestion(
        self,
        segment_key: str,
        timestamp: datetime,
        current_score: float,
        speed: float,
        stopped_count: int,
        free_flow_speed: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Identifies abnormal congestion:
        - Sudden steep spike in congestion (rate of change delta > 0.35 in 5-15 minutes)
        - Standstill speed drop (speed < 25% free-flow) with stopped vehicles detected
        """
        history = self._history.setdefault(segment_key, [])

        # Check rate of change against recent history
        if history:
            prev_time, prev_score = history[-1]
            time_diff_min = max(0.1, (timestamp - prev_time).total_seconds() / 60.0)
            if time_diff_min <= 15.0:
                delta_score = current_score - prev_score
                # Sudden severe increase
                if delta_score >= 0.35:
                    self._record_history(segment_key, timestamp, current_score)
                    return True, f"Sudden congestion spike: +{delta_score:.2f} within {time_diff_min:.1f} mins"

        # Check stoppage / blockage
        if stopped_count >= 3 and speed < (0.25 * free_flow_speed):
            self._record_history(segment_key, timestamp, current_score)
            return True, f"Blockage detected: {stopped_count} stopped vehicles with speed {speed:.1f} km/h"

        self._record_history(segment_key, timestamp, current_score)
        return False, None

    def _record_history(self, segment_key: str, timestamp: datetime, score: float):
        history = self._history.setdefault(segment_key, [])
        history.append((timestamp, score))
        if len(history) > 30:
            history.pop(0)

    def compute_routing_metadata(
        self,
        congestion_score: float,
        speed: float,
        free_flow_speed: float,
        is_abnormal: bool
    ) -> RoutingMetadata:
        """
        Supplies travel time multiplier and penalty weight for Member 4's Dijkstra/A* routing.
        Denominator clamped with max(3.0, speed) so speed=0 does not divide by zero.
        """
        multiplier = free_flow_speed / max(3.0, speed)
        multiplier = max(1.0, round(multiplier, 2))

        # Additive penalty weight: grows quadratically with congestion, plus surge if abnormal
        penalty = round(15.0 * (congestion_score ** 2) + (35.0 if is_abnormal else 0.0), 2)

        # Recommend avoiding if severe gridlock or abnormal blockage
        avoid = (congestion_score >= 0.85) or (is_abnormal and congestion_score >= 0.65)

        return RoutingMetadata(
            travel_time_multiplier=multiplier,
            penalty_weight=penalty,
            recommended_avoid=avoid
        )

    def evaluate(self, observation: CCTVObservation) -> Tuple[CurrentTrafficState, RoutingMetadata]:
        """
        End-to-end evaluation of an incoming observation.
        Returns CurrentTrafficState and RoutingMetadata.
        """
        config = self.get_road_config(observation.road_id)
        pcu = self.calculate_pcu(observation)
        speed = self.estimate_speed(
            observation=observation,
            pcu=pcu,
            free_flow_speed=config["free_flow_speed_kmph"],
            capacity_pcu=config["capacity_pcu"],
            jam_pcu=config["jam_density_pcu"]
        )

        congestion_score = self.compute_congestion_score(
            pcu=pcu,
            speed=speed,
            free_flow_speed=config["free_flow_speed_kmph"],
            capacity_pcu=config["capacity_pcu"],
            stopped_count=observation.stopped_vehicles_count,
            total_vehicles=observation.total_vehicles,
            lane_occupancy=observation.lane_occupancy_ratio
        )

        level = self.categorize_congestion(congestion_score)

        segment_key = f"{observation.road_id}:{observation.intersection_id or 'none'}"
        is_abnormal, abnormal_reason = self.check_abnormal_congestion(
            segment_key=segment_key,
            timestamp=observation.timestamp,
            current_score=congestion_score,
            speed=speed,
            stopped_count=observation.stopped_vehicles_count,
            free_flow_speed=config["free_flow_speed_kmph"]
        )

        density = round(pcu / max(0.1, config["length_km"]), 2)
        vc_ratio = round(pcu / max(1.0, config["capacity_pcu"]), 2)

        state = CurrentTrafficState(
            road_id=observation.road_id,
            intersection_id=observation.intersection_id,
            timestamp=observation.timestamp,
            vehicle_count=observation.total_vehicles,
            passenger_car_units=pcu,
            estimated_speed_kmph=speed,
            free_flow_speed_kmph=config["free_flow_speed_kmph"],
            density_pcu_per_km=density,
            volume_capacity_ratio=vc_ratio,
            congestion_score=congestion_score,
            congestion_level=level,
            is_abnormal=is_abnormal,
            abnormal_reason=abnormal_reason
        )

        routing = self.compute_routing_metadata(
            congestion_score=congestion_score,
            speed=speed,
            free_flow_speed=config["free_flow_speed_kmph"],
            is_abnormal=is_abnormal
        )

        return state, routing
