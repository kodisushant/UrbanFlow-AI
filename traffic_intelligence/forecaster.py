"""
UrbanFlow AI - 15-30 Minute Congestion Forecaster
Trains and executes lightweight, robust machine learning regressors
for 15-minute and 30-minute congestion forecasting per road segment.
"""

from datetime import datetime, timedelta
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from traffic_intelligence.models import (
    CongestionLevel,
    CurrentTrafficState,
    ForecastHorizon,
    TrafficForecastResult,
)
from traffic_intelligence.config import normalize_timestamp


class TrafficForecaster:
    """
    Dual-horizon traffic congestion forecaster.
    Predicts congestion score [0.0 - 1.0] and speeds for:
      - Horizon 1 (15 minutes ahead)
      - Horizon 2 (30 minutes ahead)
    """

    def __init__(self, alpha: float = 1.0):
        self.model_15m = Ridge(alpha=alpha)
        self.model_30m = Ridge(alpha=alpha)
        self.is_trained = False
        self.training_metrics: Dict[str, float] = {}

    def _extract_time_features(self, dt: datetime) -> Tuple[float, float]:
        """Cyclical encoding of hour of day using sine and cosine on normalized timezone."""
        dt_norm = normalize_timestamp(dt)
        hour_val = dt_norm.hour + (dt_norm.minute / 60.0)
        sin_time = math.sin(2 * math.pi * hour_val / 24.0)
        cos_time = math.cos(2 * math.pi * hour_val / 24.0)
        return sin_time, cos_time

    def prepare_training_features(
        self,
        df: pd.DataFrame,
        interval_minutes: int = 5
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Builds feature matrix X, targets y_15, y_30, and current_scores (for persistence baseline)
        from a time-series DataFrame.
        """
        df = df.sort_values(by=["road_id", "timestamp"]).reset_index(drop=True)

        feature_rows = []
        target_15m = []
        target_30m = []
        current_scores = []

        steps_15m = 15 // interval_minutes  # 3 steps
        steps_30m = 30 // interval_minutes  # 6 steps

        for road_id, group in df.groupby("road_id"):
            scores = group["congestion_score"].values
            speeds = group["estimated_speed_kmph"].values
            pcus = group["passenger_car_units"].values
            timestamps = group["timestamp"].tolist()
            n = len(scores)

            for i in range(3, n - steps_30m):
                ci_t = scores[i]
                ci_t_1 = scores[i - 1]
                ci_t_2 = scores[i - 2]
                ci_t_3 = scores[i - 3]
                rolling_avg = float(np.mean([ci_t, ci_t_1, ci_t_2]))
                trend = float(ci_t - ci_t_3)

                speed_t = speeds[i]
                pcu_t = pcus[i]
                sin_t, cos_t = self._extract_time_features(timestamps[i])

                features = [
                    ci_t,
                    ci_t_1,
                    ci_t_2,
                    ci_t_3,
                    rolling_avg,
                    trend,
                    speed_t,
                    pcu_t,
                    sin_t,
                    cos_t
                ]

                feature_rows.append(features)
                current_scores.append(ci_t)
                target_15m.append(scores[i + steps_15m])
                target_30m.append(scores[i + steps_30m])

        X = np.array(feature_rows, dtype=np.float32)
        y_15 = np.array(target_15m, dtype=np.float32)
        y_30 = np.array(target_30m, dtype=np.float32)
        y_curr = np.array(current_scores, dtype=np.float32)

        return X, y_15, y_30, y_curr

    def fit(self, df_train: pd.DataFrame, interval_minutes: int = 5):
        """Trains the dual-horizon Ridge regressors on historical / synthetic data."""
        X, y_15, y_30, _ = self.prepare_training_features(df_train, interval_minutes=interval_minutes)

        if len(X) == 0:
            raise ValueError("Insufficient time-series observations to construct lag features.")

        self.model_15m.fit(X, y_15)
        self.model_30m.fit(X, y_30)
        self.is_trained = True

        pred_15 = self.model_15m.predict(X)
        pred_30 = self.model_30m.predict(X)

        self.training_metrics = {
            "samples_count": float(len(X)),
            "train_mae_15m": round(float(mean_absolute_error(y_15, pred_15)), 4),
            "train_rmse_15m": round(float(root_mean_squared_error(y_15, pred_15)), 4),
            "train_mae_30m": round(float(mean_absolute_error(y_30, pred_30)), 4),
            "train_rmse_30m": round(float(root_mean_squared_error(y_30, pred_30)), 4),
        }

    def evaluate(self, df_test: pd.DataFrame, interval_minutes: int = 5) -> Dict[str, float]:
        """
        Evaluates the model on unseen test data and compares against a naive persistence
        baseline ('predict same as now') for both 15m and 30m horizons.
        """
        if not self.is_trained:
            raise RuntimeError("Forecaster model must be fitted before evaluation.")

        X, y_15, y_30, y_curr = self.prepare_training_features(df_test, interval_minutes=interval_minutes)
        if len(X) == 0:
            return {"error": "Insufficient test points"}

        p15 = np.clip(self.model_15m.predict(X), 0.0, 1.0)
        p30 = np.clip(self.model_30m.predict(X), 0.0, 1.0)

        # Naive persistence baseline: predict current observation y_curr for t+15 and t+30
        pers_mae_15 = float(mean_absolute_error(y_15, y_curr))
        pers_rmse_15 = float(root_mean_squared_error(y_15, y_curr))
        pers_mae_30 = float(mean_absolute_error(y_30, y_curr))
        pers_rmse_30 = float(root_mean_squared_error(y_30, y_curr))

        # Model metrics
        model_mae_15 = float(mean_absolute_error(y_15, p15))
        model_rmse_15 = float(root_mean_squared_error(y_15, p15))
        model_mae_30 = float(mean_absolute_error(y_30, p30))
        model_rmse_30 = float(root_mean_squared_error(y_30, p30))

        return {
            "test_samples": float(len(X)),
            "model_mae_15m": round(model_mae_15, 4),
            "model_rmse_15m": round(model_rmse_15, 4),
            "persistence_mae_15m": round(pers_mae_15, 4),
            "persistence_rmse_15m": round(pers_rmse_15, 4),
            "model_mae_30m": round(model_mae_30, 4),
            "model_rmse_30m": round(model_rmse_30, 4),
            "persistence_mae_30m": round(pers_mae_30, 4),
            "persistence_rmse_30m": round(pers_rmse_30, 4),
        }

    def _fallback_forecast(
        self,
        current_state: CurrentTrafficState,
        horizon_minutes: int
    ) -> Tuple[float, float, float]:
        """
        Rule-based EWMA / diurnal trend extrapolation when lag history is incomplete (cold-start).
        Returns: (predicted_score, predicted_speed, heuristic_confidence)
        """
        decay = math.exp(-0.02 * horizon_minutes)
        pred_score = (current_state.congestion_score * decay) + (0.35 * (1.0 - decay))
        pred_score = min(1.0, max(0.0, pred_score))

        pred_speed = max(5.0, current_state.free_flow_speed_kmph * (1.0 - pred_score * 0.85))
        confidence = 0.65 if horizon_minutes == 15 else 0.55

        return round(pred_score, 3), round(pred_speed, 1), confidence

    def predict(
        self,
        recent_states: List[CurrentTrafficState]
    ) -> Tuple[TrafficForecastResult, str]:
        """
        Generates 15-minute and 30-minute forecasts from the sequence of bucketed traffic states.
        Returns:
            (TrafficForecastResult, forecast_type)
            where forecast_type is either 'model_prediction' or 'rule_based_fallback'.
        """
        if not recent_states:
            raise ValueError("recent_states list cannot be empty.")

        latest = recent_states[-1]
        now = normalize_timestamp(latest.timestamp)
        time_15m = now + timedelta(minutes=15)
        time_30m = now + timedelta(minutes=30)

        # Cold start fallback if model is not trained or fewer than 4 lag observations
        if not self.is_trained or len(recent_states) < 4:
            s15, v15, c15 = self._fallback_forecast(latest, 15)
            s30, v30, c30 = self._fallback_forecast(latest, 30)
            forecast_type = "rule_based_fallback"
        else:
            s_t = recent_states[-1].congestion_score
            s_t_1 = recent_states[-2].congestion_score
            s_t_2 = recent_states[-3].congestion_score
            s_t_3 = recent_states[-4].congestion_score
            rolling_avg = float(np.mean([s_t, s_t_1, s_t_2]))
            trend = float(s_t - s_t_3)

            speed_t = latest.estimated_speed_kmph
            pcu_t = latest.passenger_car_units
            sin_t, cos_t = self._extract_time_features(now)

            feats = np.array([[
                s_t, s_t_1, s_t_2, s_t_3,
                rolling_avg, trend,
                speed_t, pcu_t,
                sin_t, cos_t
            ]], dtype=np.float32)

            pred_score_15 = float(np.clip(self.model_15m.predict(feats)[0], 0.0, 1.0))
            pred_score_30 = float(np.clip(self.model_30m.predict(feats)[0], 0.0, 1.0))

            s15 = round(pred_score_15, 3)
            s30 = round(pred_score_30, 3)

            v15 = round(max(5.0, latest.free_flow_speed_kmph * (1.0 - s15 * 0.85)), 1)
            v30 = round(max(5.0, latest.free_flow_speed_kmph * (1.0 - s30 * 0.85)), 1)

            volatility = float(np.std([s_t, s_t_1, s_t_2, s_t_3]))
            c15 = round(max(0.60, min(0.92, 0.90 - volatility * 0.5)), 2)
            c30 = round(max(0.50, min(0.85, 0.82 - volatility * 0.7)), 2)
            forecast_type = "model_prediction"

        def to_level(score: float) -> CongestionLevel:
            if score < 0.35:
                return CongestionLevel.LOW
            elif score < 0.65:
                return CongestionLevel.MODERATE
            elif score < 0.85:
                return CongestionLevel.HEAVY
            else:
                return CongestionLevel.SEVERE

        h15 = ForecastHorizon(
            horizon_minutes=15,
            predicted_timestamp=time_15m,
            predicted_congestion_score=s15,
            predicted_congestion_level=to_level(s15),
            predicted_speed_kmph=v15,
            heuristic_confidence=c15
        )

        h30 = ForecastHorizon(
            horizon_minutes=30,
            predicted_timestamp=time_30m,
            predicted_congestion_score=s30,
            predicted_congestion_level=to_level(s30),
            predicted_speed_kmph=v30,
            heuristic_confidence=c30
        )

        return TrafficForecastResult(horizon_15m=h15, horizon_30m=h30), forecast_type
