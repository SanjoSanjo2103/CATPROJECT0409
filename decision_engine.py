"""
CloudReclaim — Core Decision Engine Module
Pure evaluation engine for multi-signal, ownership-aware, calendar-aware resource reclamation decision logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class DecisionResult:
    """Dataclass holding structured evaluation outputs from the DecisionEngine."""
    action: str  # 'active', 'idle', 'orphaned', 'expired', 'skip'
    reason: str
    confidence_score: float  # 0.0 to 1.0
    risk_score: float        # 0.0 to 100.0 (Risk of false positive / breaking active workload)
    requires_approval: bool
    metrics_evaluated: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence_score": round(self.confidence_score, 2),
            "risk_score": round(self.risk_score, 2),
            "requires_approval": self.requires_approval,
            "metrics_evaluated": self.metrics_evaluated,
        }


class DecisionEngine:
    """
    Decoupled decision engine for resource reclamation state classification.
    Evaluates ownership, calendar status, multi-signal utilization, and burst activity.
    """

    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        from config import get_rules
        self.rules = rules if rules is not None else get_rules()

    def evaluate_resource(
        self,
        resource_id: str,
        resource_type: str,
        owner_id: Optional[int],
        course_is_active: bool,
        metrics: List[Dict[str, Any]],
        is_break_period: bool = False,
        extended_break_metrics: Optional[List[Dict[str, Any]]] = None,
    ) -> DecisionResult:
        """
        Evaluate a single resource through the multi-signal detection algorithm.
        """

        # ── Step 1: Ownership Check ──
        if owner_id is None:
            return DecisionResult(
                action="orphaned",
                reason="No valid owner assigned to resource",
                confidence_score=0.95,
                risk_score=5.0,
                requires_approval=False,
                metrics_evaluated={"owner_id": None},
            )

        # ── Step 2: Course / Semester Expiry Check ──
        if not course_is_active:
            if self.rules.get("auto_reclaim_after_semester", True):
                return DecisionResult(
                    action="expired",
                    reason="Course semester has ended",
                    confidence_score=0.95,
                    risk_score=10.0,
                    requires_approval=False,
                    metrics_evaluated={"course_is_active": False},
                )

        # ── Step 3: Telemetry Availability ──
        if not metrics:
            return DecisionResult(
                action="active",
                reason="Insufficient telemetry metrics to determine idle status",
                confidence_score=0.30,
                risk_score=50.0,
                requires_approval=False,
                metrics_evaluated={"metrics_count": 0},
            )

        # ── Step 4: Multi-Signal Calculation ──
        avg_cpu = sum(m.get("cpu_percent", 0.0) for m in metrics) / len(metrics)
        avg_mem = sum(m.get("memory_percent", 0.0) for m in metrics) / len(metrics)
        total_net = sum(m.get("network_bytes", 0) for m in metrics)
        max_cpu = max(m.get("cpu_percent", 0.0) for m in metrics)

        cpu_threshold = self.rules.get("cpu_idle_threshold", 5.0)
        mem_threshold = self.rules.get("memory_idle_threshold", 10.0)
        net_threshold = self.rules.get("network_idle_threshold", 1024)
        gpu_threshold = self.rules.get("gpu_idle_threshold", 5.0)

        cpu_idle = avg_cpu < cpu_threshold
        mem_idle = avg_mem < mem_threshold
        net_idle = total_net < net_threshold

        gpu_idle = True
        avg_gpu = None
        if resource_type == "gpu":
            gpu_vals = [m.get("gpu_percent") for m in metrics if m.get("gpu_percent") is not None]
            if gpu_vals:
                avg_gpu = sum(gpu_vals) / len(gpu_vals)
                gpu_idle = avg_gpu < gpu_threshold

        all_idle = cpu_idle and mem_idle and net_idle and gpu_idle

        eval_summary = {
            "avg_cpu": round(avg_cpu, 2),
            "avg_mem": round(avg_mem, 2),
            "total_net": total_net,
            "max_cpu": round(max_cpu, 2),
            "avg_gpu": round(avg_gpu, 2) if avg_gpu is not None else None,
            "cpu_idle": cpu_idle,
            "mem_idle": mem_idle,
            "net_idle": net_idle,
            "gpu_idle": gpu_idle,
        }
        # ── Step 5: Burst Workload Safeguard ──
        if max_cpu > 50.0:
            return DecisionResult(
                action="active",
                reason=f"Burst workload detected (max CPU {max_cpu:.1f}% > 50.0% threshold)",
                confidence_score=0.85,
                risk_score=85.0,
                requires_approval=False,
                metrics_evaluated=eval_summary,
            )

        # ── Step 6: Multi-Signal Idle Determination ──
        if all_idle:
            # Check break period grace extension
            if is_break_period and extended_break_metrics:
                ext_avg_cpu = sum(m.get("cpu_percent", 0.0) for m in extended_break_metrics) / len(extended_break_metrics)
                if ext_avg_cpu >= cpu_threshold:
                    return DecisionResult(
                        action="active",
                        reason=f"Resource active before break period (pre-break avg CPU {ext_avg_cpu:.1f}%)",
                        confidence_score=0.80,
                        risk_score=75.0,
                        requires_approval=False,
                        metrics_evaluated={**eval_summary, "ext_avg_cpu": round(ext_avg_cpu, 2)},
                    )

            # Requires approval if GPU and configured rule demands it
            req_approval = (resource_type == "gpu") and self.rules.get("require_approval_for_gpu", True)

            return DecisionResult(
                action="idle",
                reason="All utilization metrics consistently below idle thresholds",
                confidence_score=0.90,
                risk_score=15.0,
                requires_approval=req_approval,
                metrics_evaluated=eval_summary,
            )

        return DecisionResult(
            action="active",
            reason="One or more utilization metrics exceed idle thresholds",
            confidence_score=0.95,
            risk_score=95.0,
            requires_approval=False,
            metrics_evaluated=eval_summary,
        )
