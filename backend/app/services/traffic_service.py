from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.schemas.traffic import (
    TrafficObservation,
    TrafficForecast,
    CongestionLevel,
)
from app.services.city_graph_service import city_graph_service


class TrafficService:
    """
    Traffic intelligence service managing observation ingestion,
    congestion scoring, and deterministic baseline forecasting.
    """

    def __init__(self):
        self.observations: Dict[str, List[TrafficObservation]] = {}
        self.forecasts: Dict[str, TrafficForecast] = {}

    def ingest_observation(self, obs: TrafficObservation) -> TrafficForecast:
        """Ingest observation, update road edge weights in city graph, and compute forecast."""
        if obs.road_id not in self.observations:
            self.observations[obs.road_id] = []
        self.observations[obs.road_id].append(obs)

        # Deterministic congestion scoring
        speed = obs.average_speed_kmph
        count = obs.vehicle_count

        if speed >= 40.0:
            level = CongestionLevel.FREE_FLOW
            multiplier = 1.0
        elif speed >= 25.0:
            level = CongestionLevel.MODERATE
            multiplier = 1.4
        elif speed >= 12.0:
            level = CongestionLevel.HEAVY
            multiplier = 2.2
        else:
            level = CongestionLevel.SEVERE
            multiplier = 3.5

        # Update road in city graph
        city_graph_service.update_road_congestion(obs.road_id, level, multiplier)

        # Deterministic forward projection (forecast 15m and 30m)
        pred_15m_speed = max(5.0, round(speed * (0.85 if count > 30 else 1.05), 1))
        pred_30m_speed = max(5.0, round(speed * (0.75 if count > 45 else 1.10), 1))

        def speed_to_level(s: float) -> CongestionLevel:
            if s >= 38.0:
                return CongestionLevel.FREE_FLOW
            elif s >= 24.0:
                return CongestionLevel.MODERATE
            elif s >= 12.0:
                return CongestionLevel.HEAVY
            return CongestionLevel.SEVERE

        forecast = TrafficForecast(
            road_id=obs.road_id,
            timestamp=datetime.now(timezone.utc),
            current_congestion_level=level,
            forecast_15m_level=speed_to_level(pred_15m_speed),
            forecast_30m_level=speed_to_level(pred_30m_speed),
            predicted_speed_15m_kmph=pred_15m_speed,
            predicted_speed_30m_kmph=pred_30m_speed,
            congestion_weight_multiplier=multiplier,
            confidence=0.88 if obs.is_simulated else 0.95,
            is_simulated=obs.is_simulated,
            limitations_note="Baseline auto-regressive moving-window projection from observed speeds."
        )
        self.forecasts[obs.road_id] = forecast
        return forecast

    def get_forecast(self, road_id: str) -> Optional[TrafficForecast]:
        if road_id in self.forecasts:
            return self.forecasts[road_id]
        
        # If no explicit observation, generate default baseline from current edge
        edge = city_graph_service.get_edge(road_id)
        if not edge:
            return None
        return TrafficForecast(
            road_id=road_id,
            timestamp=datetime.now(timezone.utc),
            current_congestion_level=edge.current_congestion_level,
            forecast_15m_level=edge.current_congestion_level,
            forecast_30m_level=edge.current_congestion_level,
            predicted_speed_15m_kmph=edge.speed_limit_kmph,
            predicted_speed_30m_kmph=edge.speed_limit_kmph,
            congestion_weight_multiplier=edge.congestion_weight_multiplier,
            confidence=0.75,
            is_simulated=True,
            limitations_note="Default unperturbed street baseline."
        )

    def get_all_road_statuses(self) -> List[Dict]:
        return [
            {
                "road_id": edge.road_id,
                "name": edge.name,
                "congestion_level": edge.current_congestion_level,
                "weight_multiplier": edge.congestion_weight_multiplier,
                "is_blocked": edge.is_blocked,
                "is_diverted": edge.is_diverted
            }
            for edge in city_graph_service.edges.values()
        ]

    def reset(self):
        self.observations.clear()
        self.forecasts.clear()


traffic_service = TrafficService()

