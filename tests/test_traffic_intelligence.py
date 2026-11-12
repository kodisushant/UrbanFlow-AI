"""
Unit and Integration Tests for UrbanFlow AI - Traffic Intelligence Pipeline (Member 3)
Verifies:
  1. Zero-speed dead-stop reporting (Bug fix A1)
  2. Shared road profiles train/serve consistency (Fix A2)
  3. Timezone normalization with aware & naive mixing (Fix A3)
  4. 5-minute bucketing of 10s inputs & >15m gap history reset (Fix A4)
  5. Heuristic confidence attribute and range (Fix B5)
  6. Intersection-level output and history keying (Fix C9)
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import unittest

from traffic_intelligence.models import (
    CCTVObservation,
    CongestionLevel,
)
from traffic_intelligence.config import (
    DEFAULT_ROAD_CONFIG,
    ROAD_PROFILES,
    DEFAULT_TIMEZONE,
    normalize_timestamp,
)
from traffic_intelligence.congestion_scorer import CongestionScorer
from traffic_intelligence.forecaster import TrafficForecaster
from traffic_intelligence.synthetic_data import generate_synthetic_traffic_series
from traffic_intelligence.pipeline import TrafficIntelligencePipeline


class TestCongestionScorer(unittest.TestCase):

    def setUp(self):
        self.scorer = CongestionScorer()
        self.tz = ZoneInfo(DEFAULT_TIMEZONE)
        self.base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=self.tz)

    def test_zero_speed_reported_as_zero(self):
        """Bug fix A1: observation with speed 0.0 must report speed 0.0 without treating it as missing."""
        obs = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=self.base_time,
            total_vehicles=20,
            estimated_speed_kmph=0.0,  # Dead stop
            stopped_vehicles_count=20
        )
        state, routing = self.scorer.evaluate(obs)
        self.assertEqual(state.estimated_speed_kmph, 0.0)
        self.assertGreater(state.congestion_score, 0.70)
        # Routing multiplier denominator must clamp to safe divisor (max 3.0) without ZeroDivisionError
        self.assertGreater(routing.travel_time_multiplier, 15.0)

    def test_shared_road_profiles_consistency(self):
        """Fix A2: verify scorer uses the shared ROAD_PROFILES parameters."""
        for road_id, profile in ROAD_PROFILES.items():
            scorer_config = self.scorer.get_road_config(road_id)
            self.assertEqual(scorer_config["capacity_pcu"], profile["capacity_pcu"])
            self.assertEqual(scorer_config["free_flow_speed_kmph"], profile["free_flow_speed_kmph"])
            self.assertEqual(scorer_config["jam_density_pcu"], profile["jam_density_pcu"])

    def test_low_traffic(self):
        obs = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=self.base_time,
            vehicle_counts={"car": 4, "motorcycle": 2},
            total_vehicles=6,
            estimated_speed_kmph=52.0,
            stopped_vehicles_count=0
        )
        state, routing = self.scorer.evaluate(obs)
        self.assertEqual(state.congestion_level, CongestionLevel.LOW)
        self.assertLess(state.congestion_score, 0.35)
        self.assertFalse(state.is_abnormal)
        self.assertFalse(routing.recommended_avoid)

    def test_heavy_traffic(self):
        obs = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-02",
            timestamp=self.base_time,
            vehicle_counts={"car": 35, "truck": 3, "bus": 2},
            total_vehicles=40,
            estimated_speed_kmph=10.0,
            stopped_vehicles_count=5
        )
        state, routing = self.scorer.evaluate(obs)
        self.assertIn(state.congestion_level, [CongestionLevel.HEAVY, CongestionLevel.SEVERE])
        self.assertGreaterEqual(state.congestion_score, 0.65)
        self.assertGreater(routing.travel_time_multiplier, 2.5)

    def test_missing_speed_fallback(self):
        obs = CCTVObservation(
            source_id="cam_02",
            road_id="ROAD-02",
            timestamp=self.base_time,
            total_vehicles=15,
            estimated_speed_kmph=None  # Missing speed from camera
        )
        state, routing = self.scorer.evaluate(obs)
        self.assertIsNotNone(state.estimated_speed_kmph)
        self.assertGreater(state.estimated_speed_kmph, 0.0)
        self.assertLessEqual(state.estimated_speed_kmph, state.free_flow_speed_kmph)

    def test_abnormal_stoppage_detection(self):
        obs = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-03",
            timestamp=self.base_time,
            total_vehicles=12,
            estimated_speed_kmph=4.0,
            stopped_vehicles_count=5
        )
        state, routing = self.scorer.evaluate(obs)
        self.assertTrue(state.is_abnormal)
        self.assertIn("Blockage", state.abnormal_reason)
        self.assertGreater(routing.penalty_weight, 30.0)

    def test_spike_rule_rampup_is_not_abnormal(self):
        """Task 1: normal rush-hour jump (0.194 -> 0.544 over 5m) must NOT be flagged abnormal."""
        scorer = CongestionScorer()
        t0 = self.base_time
        # Record initial reading: score ~ 0.194
        scorer._record_history("ROAD-02:none", t0, 0.194)

        is_abn, reason = scorer.check_abnormal_congestion(
            segment_key="ROAD-02:none",
            timestamp=t0 + timedelta(minutes=5),
            current_score=0.544,
            speed=28.5,
            stopped_count=1,
            free_flow_speed=45.0
        )
        self.assertFalse(is_abn)
        self.assertIsNone(reason)

    def test_spike_rule_severe_jump_is_abnormal(self):
        """Task 1: severe spike (0.30 -> 0.78 over 5m) exceeding delta 0.40 and score 0.65 IS abnormal."""
        scorer = CongestionScorer()
        t0 = self.base_time
        scorer._record_history("ROAD-02:none", t0, 0.30)

        is_abn, reason = scorer.check_abnormal_congestion(
            segment_key="ROAD-02:none",
            timestamp=t0 + timedelta(minutes=5),
            current_score=0.78,
            speed=12.0,
            stopped_count=1,
            free_flow_speed=45.0
        )
        self.assertTrue(is_abn)
        self.assertIn("Sudden congestion spike", reason)


class TestTimezoneHandling(unittest.TestCase):

    def test_mixing_aware_and_naive_timestamps(self):
        """Fix A3: mixing aware (UTC / Z) and naive datetimes must not raise error."""
        pipeline = TrafficIntelligencePipeline(auto_calibrate=False)
        pipeline.calibrate_with_synthetic_data(days=1)

        # Naive datetime
        t_naive = datetime(2026, 11, 12, 14, 0, 0)
        obs_naive = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=t_naive,
            total_vehicles=10,
            estimated_speed_kmph=45.0
        )
        out1 = pipeline.process_observation(obs_naive)
        self.assertIsNotNone(out1.timestamp.tzinfo)

        # Aware datetime (UTC)
        t_aware = datetime(2026, 11, 12, 8, 35, 0, tzinfo=timezone.utc)
        obs_aware = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=t_aware,
            total_vehicles=12,
            estimated_speed_kmph=42.0
        )
        out2 = pipeline.process_observation(obs_aware)
        self.assertIsNotNone(out2.timestamp.tzinfo)
        # Should not raise TypeError when processing sequentially
        self.assertEqual(out2.timestamp.tzinfo.key, DEFAULT_TIMEZONE)


class TestIrregularSpacingAndBucketing(unittest.TestCase):

    def test_rapid_10_second_input_bucketing(self):
        """Fix A4: rapid 10s inputs within the same 5m bucket are aggregated rather than polluting lags."""
        pipeline = TrafficIntelligencePipeline(auto_calibrate=False)
        base = datetime(2026, 11, 12, 10, 0, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

        # Send 6 observations 10 seconds apart (all in 10:00 - 10:05 bucket)
        for i in range(6):
            obs = CCTVObservation(
                source_id="cam_01",
                road_id="ROAD-01",
                timestamp=base + timedelta(seconds=i * 10),
                total_vehicles=10 + i,
                estimated_speed_kmph=40.0
            )
            out = pipeline.process_observation(obs)
            self.assertEqual(out.road_id, "ROAD-01")

        # Now send one in the next 5-minute bucket (10:05:00)
        obs_next = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=base + timedelta(minutes=5),
            total_vehicles=16,
            estimated_speed_kmph=38.0
        )
        out_next = pipeline.process_observation(obs_next)
        key = ("ROAD-01", None)
        # History must contain exactly 1 aggregated record for the 10:00-10:05 bucket
        self.assertEqual(len(pipeline.bucketed_history[key]), 1)

    def test_large_gap_resets_history(self):
        """Fix A4: a gap > 15 minutes between buckets resets history and uses fallback."""
        pipeline = TrafficIntelligencePipeline(auto_calibrate=False)
        pipeline.calibrate_with_synthetic_data(days=1)
        base = datetime(2026, 11, 12, 10, 0, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))
        key = ("ROAD-01", None)

        # Build 4 consecutive buckets (10:00, 10:05, 10:10, 10:15)
        for m in [0, 5, 10, 15]:
            obs = CCTVObservation(
                source_id="cam_01",
                road_id="ROAD-01",
                timestamp=base + timedelta(minutes=m),
                total_vehicles=20,
                estimated_speed_kmph=35.0
            )
            pipeline.process_observation(obs)

        # Jump forward by 45 minutes (> 15 min gap)
        jump_obs = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=base + timedelta(minutes=60),
            total_vehicles=25,
            estimated_speed_kmph=30.0
        )
        out = pipeline.process_observation(jump_obs)
        # Provenance must report fallback because history was reset due to the large gap
        self.assertEqual(out.data_provenance["forecast_type"], "rule_based_fallback")


class TestIntersections(unittest.TestCase):

    def test_intersection_level_output_and_keying(self):
        """Fix C9: support intersection_id in output and separate history keys."""
        pipeline = TrafficIntelligencePipeline(auto_calibrate=False)
        base = datetime(2026, 11, 12, 12, 0, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

        obs_int = CCTVObservation(
            source_id="cam_int_01",
            road_id="ROAD-01",
            intersection_id="INT-42",
            timestamp=base,
            total_vehicles=18,
            estimated_speed_kmph=30.0
        )
        out_int = pipeline.process_observation(obs_int)
        self.assertEqual(out_int.intersection_id, "INT-42")
        self.assertEqual(out_int.current_state.intersection_id, "INT-42")

        # Distinct key in pipeline history
        int_key = ("ROAD-01", "INT-42")
        self.assertIn(int_key, pipeline._active_bucket)


class TestForecasterHonestyAndHeuristicConfidence(unittest.TestCase):

    def test_heuristic_confidence_field(self):
        """Fix B5: verify heuristic_confidence is present and bounded in [0, 1]."""
        forecaster = TrafficForecaster()
        scorer = CongestionScorer()
        base = datetime(2026, 11, 12, 8, 0, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))
        obs = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=base,
            total_vehicles=10,
            estimated_speed_kmph=40.0
        )
        state, _ = scorer.evaluate(obs)
        result, f_type = forecaster.predict([state])

        self.assertTrue(hasattr(result.horizon_15m, "heuristic_confidence"))
        self.assertTrue(hasattr(result.horizon_30m, "heuristic_confidence"))
        self.assertGreaterEqual(result.horizon_15m.heuristic_confidence, 0.0)
        self.assertLessEqual(result.horizon_15m.heuristic_confidence, 1.0)
        self.assertEqual(f_type, "rule_based_fallback")

    def test_forecast_reliability_all_three_values(self):
        """Task 3: test 'low_cold_start', 'normal', and 'low_during_incident' reliability flags."""
        pipeline = TrafficIntelligencePipeline(auto_calibrate=True)
        base = datetime(2026, 11, 12, 14, 0, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

        # 1. Cold start observation (< 4 points in history)
        obs_cold = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=base,
            total_vehicles=10,
            estimated_speed_kmph=45.0
        )
        out_cold = pipeline.process_observation(obs_cold)
        self.assertEqual(out_cold.forecast_reliability, "low_cold_start")
        self.assertEqual(out_cold.data_provenance["forecast_reliability"], "low_cold_start")

        # 2. Build 4 consecutive 5-min observations to reach model prediction
        for i in range(1, 5):
            obs = CCTVObservation(
                source_id="cam_01",
                road_id="ROAD-01",
                timestamp=base + timedelta(minutes=i * 5),
                total_vehicles=12 + i,
                estimated_speed_kmph=44.0 - i
            )
            out_normal = pipeline.process_observation(obs)

        # Normal condition reached
        self.assertEqual(out_normal.forecast_reliability, "normal")
        self.assertEqual(out_normal.data_provenance["forecast_reliability"], "normal")
        self.assertEqual(out_normal.data_provenance["forecast_type"], "model_prediction")

        # 3. Trigger incident / blockage
        obs_incident = CCTVObservation(
            source_id="cam_01",
            road_id="ROAD-01",
            timestamp=base + timedelta(minutes=25),
            total_vehicles=40,
            estimated_speed_kmph=4.0,
            stopped_vehicles_count=5
        )
        out_incident = pipeline.process_observation(obs_incident)
        self.assertTrue(out_incident.current_state.is_abnormal)
        self.assertEqual(out_incident.forecast_reliability, "low_during_incident")
        self.assertEqual(out_incident.data_provenance["forecast_reliability"], "low_during_incident")


if __name__ == "__main__":
    unittest.main()
