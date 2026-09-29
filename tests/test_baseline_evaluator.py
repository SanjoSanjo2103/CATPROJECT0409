"""
Unit tests for Core Baseline Evaluator Module
"""

import pytest
from baseline_evaluator import BaselineEvaluator, EvaluationReport


class TestBaselineEvaluator:

    @pytest.fixture
    def evaluator(self):
        return BaselineEvaluator()

    def test_evaluation_metrics_calculation(self, evaluator):
        """Verify precision, recall, confusion matrix, and cost savings calculations."""
        all_ids = ["res-1", "res-2", "res-3", "res-4", "res-5", "res-6"]
        costs = {r: 100.0 for r in all_ids}

        ground_truth_idle = {"res-1", "res-2", "res-3"}  # Ground truth idle
        baseline_flagged = {"res-1", "res-2", "res-3", "res-4", "res-5"}  # Naive CPU flagged 5 (2 false positives)
        prototype_flagged = {"res-1", "res-2", "res-3"}  # Prototype flagged exactly 3 truly idle

        report = evaluator.evaluate(
            all_resource_ids=all_ids,
            resource_costs=costs,
            baseline_flagged_ids=baseline_flagged,
            prototype_flagged_ids=prototype_flagged,
            ground_truth_idle_ids=ground_truth_idle,
        )

        assert report.total_resources == 6
        assert report.ground_truth_idle_count == 3
        assert report.ground_truth_active_count == 3

        # Baseline confusion matrix
        assert report.baseline_tp == 3
        assert report.baseline_fp == 2
        assert report.baseline_fn == 0
        assert report.baseline_fp_rate == 40.0  # 2 / 5 = 40%

        # Prototype confusion matrix
        assert report.prototype_tp == 3
        assert report.prototype_fp == 0
        assert report.prototype_fn == 0
        assert report.prototype_fp_rate == 0.0

        # Comparative improvements
        assert report.fp_reduction == 2
        assert report.fn_reduction == 0
        assert report.prototype_cost_eliminated == 300.0

        report_dict = report.to_dict()
        assert report_dict["baseline"]["false_positive_rate_pct"] == 40.0
        assert report_dict["prototype"]["false_positive_rate_pct"] == 0.0
