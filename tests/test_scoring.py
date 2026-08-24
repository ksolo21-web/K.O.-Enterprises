"""Executable checks for the Market Void and Entry-Wedge scorecard."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from company_os.errors import ValidationError
from company_os.scoring import (
    COMPONENT_WEIGHTS,
    MarketVoidInput,
    RiskPenalties,
    calculate_market_void_score,
    score_from_evidence,
)


class MarketVoidScoringTests(unittest.TestCase):
    def test_full_component_ratings_equal_one_hundred_points(self) -> None:
        inputs = MarketVoidInput(
            **{name: 1.0 for name in COMPONENT_WEIGHTS},
            strong_demand_signal=True,
            independent_source_count=2,
        )
        score = calculate_market_void_score(inputs)

        self.assertEqual(100.0, score.base_score)
        self.assertEqual(0.0, score.penalty_score)
        self.assertEqual(100.0, score.final_score)
        self.assertEqual(COMPONENT_WEIGHTS, score.component_points)
        self.assertTrue(score.eligible_for_advancement)

    def test_penalties_are_explicit_weighted_deductions(self) -> None:
        inputs = MarketVoidInput(
            **{name: 1.0 for name in COMPONENT_WEIGHTS},
            strong_demand_signal=True,
            independent_source_count=2,
        )
        score = calculate_market_void_score(
            inputs,
            RiskPenalties(legal_risk=1.0, platform_dependency=0.5),
        )

        self.assertEqual(10.0, score.penalty_points["legal_risk"])
        self.assertEqual(4.0, score.penalty_points["platform_dependency"])
        self.assertEqual(14.0, score.penalty_score)
        self.assertEqual(86.0, score.final_score)

    def test_final_score_is_never_negative(self) -> None:
        score = calculate_market_void_score(
            MarketVoidInput(),
            RiskPenalties(**{
                "legal_risk": 1,
                "platform_dependency": 1,
                "proprietary_data_dependency": 1,
                "security_exposure": 1,
                "support_burden": 1,
                "weak_buyer_reach": 1,
                "evidence_staleness": 1,
            }),
        )
        self.assertEqual(0.0, score.final_score)

    def test_out_of_range_component_or_penalty_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            MarketVoidInput(need_severity=1.01)
        with self.assertRaises(ValidationError):
            RiskPenalties(legal_risk=-0.01)
        with self.assertRaises(ValidationError):
            MarketVoidInput(need_severity=True)  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            calculate_market_void_score({"need_severtiy": 1.0})
        with self.assertRaises(ValidationError):
            calculate_market_void_score({}, {"legal_riisk": 1.0})

    def test_high_numeric_score_does_not_override_hard_rejection(self) -> None:
        inputs = MarketVoidInput(
            **{name: 1.0 for name in COMPONENT_WEIGHTS},
            credible_problem_evidence=False,
            strong_demand_signal=True,
            independent_source_count=2,
        )
        score = calculate_market_void_score(inputs)

        self.assertEqual(100.0, score.final_score)
        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("no credible evidence of a real problem", score.rejection_reasons)

    def test_low_competition_requires_demand_and_corroboration(self) -> None:
        uncorroborated = calculate_market_void_score(
            MarketVoidInput(
                **{name: 1.0 for name in COMPONENT_WEIGHTS},
                low_competition=True,
                strong_demand_signal=True,
                independent_source_count=1,
            )
        )
        corroborated = calculate_market_void_score(
            MarketVoidInput(
                **{name: 1.0 for name in COMPONENT_WEIGHTS},
                low_competition=True,
                strong_demand_signal=True,
                independent_source_count=2,
            )
        )

        self.assertFalse(uncorroborated.eligible_for_advancement)
        self.assertTrue(corroborated.eligible_for_advancement)

    def test_advancement_threshold_is_consistent_at_sixty_five(self) -> None:
        below = MarketVoidInput(
            need_severity=1.0,
            demand_acceleration=1.0,
            economic_commitment=1.0,
            supply_gap=1.0,
            incumbent_weakness=0.999,
        )
        at_threshold = MarketVoidInput(
            need_severity=1.0,
            demand_acceleration=1.0,
            economic_commitment=1.0,
            supply_gap=1.0,
            incumbent_weakness=1.0,
        )

        below_score = calculate_market_void_score(below)
        threshold_score = calculate_market_void_score(at_threshold)
        self.assertAlmostEqual(64.99, below_score.final_score)
        self.assertFalse(below_score.eligible_for_advancement)
        self.assertIn(
            "score below 65 advancement threshold",
            below_score.rejection_reasons,
        )
        self.assertEqual(65.0, threshold_score.final_score)
        self.assertTrue(threshold_score.eligible_for_advancement)

    def test_evidence_uses_strength_and_confidence_weighted_mean(self) -> None:
        now = datetime(2026, 8, 24, tzinfo=timezone.utc)
        rows = [
            {
                "criterion": "need_severity",
                "strength": "strong",
                "confidence": 1.0,
                "rating": 1.0,
                "source_uri": "https://example.test/strong",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "need_severity",
                "strength": "weak",
                "confidence": 1.0,
                "rating": 0.0,
                "source_uri": "https://example.test/weak",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "reachable_beachhead",
                "strength": "moderate",
                "confidence": 1.0,
                "rating": 0.5,
                "source_uri": "https://example.test/reach",
                "expires_at": "2099-01-01",
            },
        ]
        score = score_from_evidence(rows, now=now)

        expected_rating = 1.0 / 1.35
        self.assertAlmostEqual(
            20 * expected_rating,
            score.component_points["need_severity"],
            places=6,
        )
        self.assertEqual(5.0, score.component_points["reachable_beachhead"])

    def test_missing_evidence_fails_advancement_closed(self) -> None:
        score = score_from_evidence([])
        self.assertEqual(0.0, score.final_score)
        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("no credible evidence of a real problem", score.rejection_reasons)
        self.assertIn("no credible permission-based path to buyers", score.rejection_reasons)

    def test_expired_evidence_adds_staleness_penalty_and_no_positive_points(self) -> None:
        now = datetime(2026, 8, 24, tzinfo=timezone.utc)
        score = score_from_evidence(
            [
                {
                    "criterion": "need_severity",
                    "strength": "strong",
                    "confidence": 1.0,
                    "rating": 1.0,
                    "source_uri": "https://example.test/expired",
                    "expires_at": (now - timedelta(seconds=1)).isoformat(),
                }
            ],
            now=now,
        )

        self.assertEqual(0.0, score.base_score)
        self.assertEqual(7.0, score.penalty_points["evidence_staleness"])
        self.assertIn("material evidence is stale and should be revalidated", score.warnings)

    def test_missing_expiry_is_stale_and_cannot_support_advancement(self) -> None:
        score = score_from_evidence(
            [
                {
                    "criterion": "need_severity",
                    "strength": "strong",
                    "confidence": 1.0,
                    "rating": 1.0,
                    "source_uri": "https://example.test/no-expiry",
                }
            ],
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
        )

        self.assertEqual(7.0, score.penalty_points["evidence_staleness"])
        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("no credible evidence of a real problem", score.rejection_reasons)

    def test_two_sources_can_satisfy_low_competition_gate(self) -> None:
        rows = [
            {
                "criterion": "need_severity",
                "strength": "strong",
                "confidence": 1.0,
                "rating": 0.8,
                "source_uri": "https://buyers.test/behavior",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "reachable_beachhead",
                "strength": "moderate",
                "confidence": 1.0,
                "rating": 0.5,
                "source_uri": "https://market.test/channel",
                "expires_at": "2099-01-01",
            },
        ]
        score = score_from_evidence(
            rows,
            low_competition=True,
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
        )
        self.assertTrue(score.eligible_for_advancement)

    def test_two_urls_from_one_host_are_not_independent_corroboration(self) -> None:
        rows = [
            {
                "criterion": "need_severity",
                "strength": "strong",
                "confidence": 1.0,
                "rating": 0.8,
                "source_uri": "https://www.same-source.test/first",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "reachable_beachhead",
                "strength": "moderate",
                "confidence": 1.0,
                "rating": 0.5,
                "source_uri": "https://same-source.test/second?copy=1",
                "expires_at": "2099-01-01",
            },
        ]
        score = score_from_evidence(
            rows,
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
            low_competition=True,
        )

        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("two independent sources", " ".join(score.rejection_reasons))

    def test_sibling_subdomains_are_not_independent_corroboration(self) -> None:
        rows = [
            {
                "criterion": "need_severity",
                "strength": "strong",
                "confidence": 1.0,
                "rating": 0.8,
                "source_uri": "https://research.publisher.test/problem",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "reachable_beachhead",
                "strength": "moderate",
                "confidence": 1.0,
                "rating": 0.6,
                "source_uri": "https://blog.publisher.test/channel",
                "expires_at": "2099-01-01",
            },
        ]
        score = score_from_evidence(
            rows,
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
            low_competition=True,
        )

        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("two independent sources", " ".join(score.rejection_reasons))

    def test_component_overrides_cannot_replace_problem_and_reach_evidence(self) -> None:
        score = score_from_evidence(
            [
                {
                    "criterion": "recurring_revenue",
                    "strength": "weak",
                    "confidence": 0.0,
                    "rating": 0.0,
                    "source_uri": "https://irrelevant.test/claim",
                    "expires_at": "2099-01-01",
                }
            ],
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
        )

        self.assertEqual(100.0, score.final_score)
        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("no credible evidence of a real problem", score.rejection_reasons)
        self.assertIn(
            "no credible permission-based path to buyers", score.rejection_reasons
        )

    def test_zero_confidence_signal_cannot_satisfy_low_competition_gate(self) -> None:
        rows = [
            {
                "criterion": "need_severity",
                "strength": "strong",
                "confidence": 0.0,
                "rating": 1.0,
                "source_uri": "https://signal.test/claim",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "reachable_beachhead",
                "strength": "moderate",
                "confidence": 1.0,
                "rating": 1.0,
                "source_uri": "https://channel.test/reach",
                "expires_at": "2099-01-01",
            },
        ]
        score = score_from_evidence(
            rows,
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
            low_competition=True,
        )

        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("strong demand signal", " ".join(score.rejection_reasons))

    def test_unknown_override_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            score_from_evidence([], overrides={"made_up_factor": 1.0})
        with self.assertRaises(ValidationError):
            score_from_evidence([], penalty_overrides={"made_up_risk": 1.0})
        with self.assertRaises(ValidationError):
            score_from_evidence([], hard_rejection_flags={"made_up_gate": True})
        with self.assertRaises(ValidationError):
            score_from_evidence(
                [],
                hard_rejection_flags={"mvp_too_large": "yes"},  # type: ignore[dict-item]
            )

    def test_hard_rejection_flags_override_a_high_numeric_score(self) -> None:
        rows = [
            {
                "criterion": "need_severity",
                "strength": "strong",
                "confidence": 1.0,
                "rating": 1.0,
                "source_uri": "https://evidence.test/hard-gate",
                "expires_at": "2099-01-01",
            },
            {
                "criterion": "reachable_beachhead",
                "strength": "strong",
                "confidence": 1.0,
                "rating": 1.0,
                "source_uri": "https://evidence.test/reach",
                "expires_at": "2099-01-01",
            },
        ]
        score = score_from_evidence(
            rows,
            overrides={name: 1.0 for name in COMPONENT_WEIGHTS},
            hard_rejection_flags={"unlawful_advantage": True},
        )

        self.assertEqual(100.0, score.final_score)
        self.assertFalse(score.eligible_for_advancement)
        self.assertIn("unlawful or prohibited conduct", " ".join(score.rejection_reasons))


if __name__ == "__main__":
    unittest.main()
