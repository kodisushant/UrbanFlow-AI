"""
UrbanFlow AI - Synthetic Traffic Data Generator
Generates realistic, clearly-labelled synthetic traffic time-series data
for training, calibrating, and evaluating the 15-30 minute congestion forecaster.
"""

from datetime import datetime, timedelta
import math
import numpy as np
import pandas as pd
from typing import List, Optional
from traffic_intelligence.config import ROAD_PROFILES, DEFAULT_ROAD_CONFIG, normalize_timestamp


def generate_synthetic_traffic_series(
    road_ids: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    days: int = 3,
    interval_minutes: int = 5,
    inject_incident_on: Optional[str] = "ROAD-02",
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Generates synthetic time-series traffic observations using shared ROAD_PROFILES.

    Each row is explicitly labelled with `is_synthetic: True`.
    Simulates:
      - Daily rhythm: Morning peak (08:00-10:00), Evening peak (17:00-19:30), Night low (00:00-06:00).
      - Multi-class vehicle distribution (cars, buses, bikes, trucks).
      - Physical speed-density relationship using shared road parameters.
      - Injected collision/incident shockwave on `inject_incident_on`.

    Returns:
        pd.DataFrame containing timestamp, road_id, vehicle_counts, pcu, speed, congestion_score.
    """
    np.random.seed(random_seed)

    if road_ids is None:
        road_ids = list(ROAD_PROFILES.keys())

    if start_time is None:
        start_time = datetime(2026, 11, 10, 0, 0, 0)
    start_time = normalize_timestamp(start_time)

    total_steps = int((days * 24 * 60) / interval_minutes)
    records = []

    for road_id in road_ids:
        params = ROAD_PROFILES.get(road_id, DEFAULT_ROAD_CONFIG)
        cap = params["capacity_pcu"]
        v0 = params["free_flow_speed_kmph"]
        jam_pcu = params["jam_density_pcu"]

        for step in range(total_steps):
            current_dt = start_time + timedelta(minutes=step * interval_minutes)
            hour_float = current_dt.hour + (current_dt.minute / 60.0)

            # 1. Base diurnal curve (bimodal: morning & evening peak)
            morning_peak = 0.85 * math.exp(-((hour_float - 8.75) ** 2) / 2.5)
            evening_peak = 0.95 * math.exp(-((hour_float - 18.25) ** 2) / 3.0)
            midday_base = 0.35 + 0.15 * math.sin((hour_float - 13.0) * math.pi / 12.0)
            night_factor = 0.08 if (hour_float < 6.0 or hour_float > 22.5) else 0.0

            base_intensity = max(0.05, morning_peak + evening_peak + midday_base + night_factor)

            # Add stochastic fluctuation (+/- 15%)
            noise = np.random.normal(0.0, 0.06)
            intensity = max(0.04, min(1.2, base_intensity + noise))

            # Calculate vehicle counts
            expected_pcu = intensity * cap
            pcu = max(1.0, float(np.random.poisson(max(1.0, expected_pcu))))

            # Approximate vehicle breakdown
            cars = int(pcu * 0.65)
            bikes = int(pcu * 0.40)
            buses = int(pcu * 0.05)
            trucks = int(pcu * 0.04)
            total_vehicles = max(1, cars + bikes + buses + trucks)

            # Macroscopic speed estimation using shared jam density
            density_ratio = min(1.0, pcu / max(jam_pcu, 1.0))
            speed = max(5.0, v0 * (1.0 - density_ratio) + np.random.normal(0, 2.0))

            stopped_count = 0
            is_abnormal = False

            # Inject simulated incident on Day 2 during evening rush hour (18:00 - 18:45)
            if road_id == inject_incident_on and current_dt.day == start_time.day + 1:
                if 18.0 <= hour_float <= 18.75:
                    is_abnormal = True
                    stopped_count = int(np.random.randint(4, 9))
                    pcu = pcu * 1.6
                    speed = max(0.0, 6.0 + np.random.normal(0, 1.0))

            # Composite Congestion Index [0.0, 1.0] matching CongestionScorer formula
            vc_ratio = min(1.0, pcu / cap)
            speed_deficit = max(0.0, (v0 - speed) / v0)
            queue_penalty = min(1.0, stopped_count / max(total_vehicles, 1))
            congestion_score = round(
                float(min(1.0, max(0.0, 0.45 * vc_ratio + 0.40 * speed_deficit + 0.15 * queue_penalty))),
                3
            )

            records.append({
                "timestamp": current_dt,
                "road_id": road_id,
                "cars": cars,
                "motorcycles": bikes,
                "buses": buses,
                "trucks": trucks,
                "total_vehicles": total_vehicles,
                "passenger_car_units": round(pcu, 2),
                "estimated_speed_kmph": round(speed, 1),
                "free_flow_speed_kmph": v0,
                "stopped_vehicles_count": stopped_count,
                "congestion_score": congestion_score,
                "is_abnormal": is_abnormal,
                "is_synthetic": True
            })

    df = pd.DataFrame(records)
    return df
