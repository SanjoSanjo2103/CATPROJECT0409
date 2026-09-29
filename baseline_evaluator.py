"""
CloudReclaim — Core Baseline Evaluator Module
Evaluates and benchmarks single-metric (CPU-only) baseline detection against multi-signal prototype detection.
Calculates Precision, Recall, False Positive Rate (FPR), False Negative Rate (FNR), and Cost Savings.
"""

from dataclasses import dataclass, field
from typing import Set, Dict, List, Any


@dataclass
class EvaluationReport:
    """Dataclass holding quantitative comparison evaluation metrics."""
    total_resources: int
    ground_truth_idle_count: int
    ground_truth_active_count: int

    # Baseline metrics
    baseline_flagged: int
    baseline_tp: int
    baseline_fp: int
    baseline_fn: int
    baseline_fp_rate: float

    # Prototype metrics
    prototype_flagged: int
    prototype_tp: int
    prototype_fp: int
    prototype_fn: int
    prototype_fp_rate: float

    # Comparative improvements
    fp_reduction: int
    fn_reduction: int
    baseline_idle_cost: float
    prototype_cost_eliminated: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_resources": self.total_resources,
            "ground_truth": {
                "idle_count": self.ground_truth_idle_count,
                "active_count": self.ground_truth_active_count,
            },
            "baseline": {
                "flagged": self.baseline_flagged,
                "true_positives": self.baseline_tp,
                "false_positives": self.baseline_fp,
                "false_negatives": self.baseline_fn,
                "false_positive_rate_pct": round(self.baseline_fp_rate, 2),
                "monthly_idle_cost": round(self.baseline_idle_cost, 2),
            },
            "prototype": {
                "flagged": self.prototype_flagged,
                "true_positives": self.prototype_tp,
                "false_positives": self.prototype_fp,
                "false_negatives": self.prototype_fn,
                "false_positive_rate_pct": round(self.prototype_fp_rate, 2),
                "monthly_cost_eliminated": round(self.prototype_cost_eliminated, 2),
            },
            "improvements": {
                "fp_reduction": self.fp_reduction,
                "fn_reduction": self.fn_reduction,
            },
        }


class BaselineEvaluator:
    """
    Evaluator for comparing baseline vs prototype resource reclamation algorithms.
    """

    def evaluate(
        self,
        all_resource_ids: List[str],
        resource_costs: Dict[str, float],
        baseline_flagged_ids: Set[str],
        prototype_flagged_ids: Set[str],
        ground_truth_idle_ids: Set[str],
    ) -> EvaluationReport:
        """
        Compute comprehensive evaluation metrics comparing baseline and prototype algorithms.
        """
        all_ids = set(all_resource_ids)
        ground_truth_active_ids = all_ids - ground_truth_idle_ids

        # Baseline confusion matrix
        b_tp = len(baseline_flagged_ids & ground_truth_idle_ids)
        b_fp = len(baseline_flagged_ids & ground_truth_active_ids)
        b_fn = len(ground_truth_idle_ids - baseline_flagged_ids)

        b_fp_rate = (b_fp / max(len(baseline_flagged_ids), 1)) * 100.0

        # Prototype confusion matrix
        p_tp = len(prototype_flagged_ids & ground_truth_idle_ids)
        p_fp = len(prototype_flagged_ids & ground_truth_active_ids)
        p_fn = len(ground_truth_idle_ids - prototype_flagged_ids)

        p_fp_rate = (p_fp / max(len(prototype_flagged_ids), 1)) * 100.0

        # Cost calculations
        b_idle_cost = sum(resource_costs.get(rid, 0.0) for rid in baseline_flagged_ids)
        p_cost_eliminated = sum(resource_costs.get(rid, 0.0) for rid in (prototype_flagged_ids & ground_truth_idle_ids))

        return EvaluationReport(
            total_resources=len(all_ids),
            ground_truth_idle_count=len(ground_truth_idle_ids),
            ground_truth_active_count=len(ground_truth_active_ids),
            baseline_flagged=len(baseline_flagged_ids),
            baseline_tp=b_tp,
            baseline_fp=b_fp,
            baseline_fn=b_fn,
            baseline_fp_rate=b_fp_rate,
            prototype_flagged=len(prototype_flagged_ids),
            prototype_tp=p_tp,
            prototype_fp=p_fp,
            prototype_fn=p_fn,
            prototype_fp_rate=p_fp_rate,
            fp_reduction=b_fp - p_fp,
            fn_reduction=b_fn - p_fn,
            baseline_idle_cost=b_idle_cost,
            prototype_cost_eliminated=p_cost_eliminated,
        )
