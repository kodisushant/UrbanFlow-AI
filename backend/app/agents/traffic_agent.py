from typing import List, Dict, Any
from app.schemas.traffic import TrafficForecast, CongestionLevel
from app.services.traffic_service import traffic_service


class TrafficAgent:
    """
    Traffic Intelligence Agent.
    Interprets congestion forecasts across urban corridors and explains bottleneck impacts.
    """

    def summarize_corridor(self, road_ids: List[str]) -> Dict[str, Any]:
        """Summarize current traffic conditions and forecast for a given corridor."""
        severely_congested = []
        heavy_congested = []
        forecasts = []

        for rid in road_ids:
            fc = traffic_service.get_forecast(rid)
            if fc:
                forecasts.append(fc)
                if fc.current_congestion_level == CongestionLevel.SEVERE:
                    severely_congested.append(rid)
                elif fc.current_congestion_level == CongestionLevel.HEAVY:
                    heavy_congested.append(rid)

        if severely_congested:
            summary = (
                f"Severe bottlenecks identified along road segments: {', '.join(severely_congested)}. "
                f"Speed reductions exceed 70%. Emergency routing must divert around these segments."
            )
        elif heavy_congested:
            summary = (
                f"Moderate-to-heavy traffic density detected on {', '.join(heavy_congested)}. "
                f"Signal priority recommended along priority avenues to preserve responder ETA."
            )
        else:
            summary = "Corridor traffic is moving within standard parameters (free-flow to moderate)."

        return {
            "summary": summary,
            "severe_roads": severely_congested,
            "heavy_roads": heavy_congested,
            "sample_forecast_count": len(forecasts)
        }


traffic_agent = TrafficAgent()

