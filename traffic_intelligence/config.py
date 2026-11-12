"""
UrbanFlow AI - Shared Configuration & Road Profiles
Ensures training data generation and live scoring use identical road parameter scales.
"""

from datetime import datetime
from typing import Dict, Any
from zoneinfo import ZoneInfo

DEFAULT_ROAD_CONFIG: Dict[str, Any] = {
    "length_km": 0.5,
    "lanes": 2,
    "capacity_pcu": 40.0,
    "jam_density_pcu": 80.0,
    "free_flow_speed_kmph": 50.0,
}

ROAD_PROFILES: Dict[str, Dict[str, Any]] = {
    "ROAD-01": {
        "length_km": 0.6,
        "lanes": 2,
        "capacity_pcu": 45.0,
        "jam_density_pcu": 90.0,
        "free_flow_speed_kmph": 55.0,
    },
    "ROAD-02": {
        "length_km": 0.5,
        "lanes": 2,
        "capacity_pcu": 35.0,
        "jam_density_pcu": 70.0,
        "free_flow_speed_kmph": 45.0,
    },
    "ROAD-03": {
        "length_km": 0.8,
        "lanes": 3,
        "capacity_pcu": 50.0,
        "jam_density_pcu": 100.0,
        "free_flow_speed_kmph": 50.0,
    },
    "ROAD-04": {
        "length_km": 0.5,
        "lanes": 2,
        "capacity_pcu": 40.0,
        "jam_density_pcu": 80.0,
        "free_flow_speed_kmph": 50.0,
    },
    "ROAD-05": {
        "length_km": 0.4,
        "lanes": 2,
        "capacity_pcu": 30.0,
        "jam_density_pcu": 60.0,
        "free_flow_speed_kmph": 40.0,
    },
}

DEFAULT_TIMEZONE = "Asia/Kolkata"


def normalize_timestamp(dt: datetime, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    """
    Normalizes any datetime (aware or naive) to the configured target timezone.
    - If naive: assumed to be in target timezone and assigned tzinfo.
    - If aware: converted via astimezone to target timezone.
    Prevents offset-naive / offset-aware subtraction errors.
    """
    target_tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=target_tz)
    return dt.astimezone(target_tz)
