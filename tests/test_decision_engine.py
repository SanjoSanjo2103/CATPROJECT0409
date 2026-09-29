"""
Unit tests for Core Decision Engine Module
"""

import pytest
from decision_engine import DecisionEngine, DecisionResult


class TestDecisionEngine:

    @pytest.fixture
    def engine(self):
        rules = {
            "cpu_idle_threshold": 5.0,
            "memory_idle_threshold": 10.0,
            "network_idle_threshold": 1024,
            "gpu_idle_threshold": 5.0,
            "idle_duration_days": 7,
            "auto_reclaim_after_semester": True,
            "require_approval_for_gpu": True,
        }
        return DecisionEngine(rules=rules)

    def test_orphaned_resource_detected(self, engine):
        """Verify resource with missing owner is classified as orphaned."""
        res = engine.evaluate_resource(
            resource_id="vm-node-01",
            resource_type="vm",
            owner_id=None,
            course_is_active=True,
            metrics=[{"cpu_percent": 1.0, "memory_percent": 2.0, "network_bytes": 100}],
        )
        assert res.action == "orphaned"
        assert res.confidence_score >= 0.90
        assert res.risk_score <= 10.0

    def test_expired_semester_detected(self, engine):
        """Verify resource associated with an inactive/expired course is classified as expired."""
        res = engine.evaluate_resource(
            resource_id="vm-cs101-01",
            resource_type="vm",
            owner_id=3,
            course_is_active=False,
            metrics=[{"cpu_percent": 2.0, "memory_percent": 4.0, "network_bytes": 200}],
        )
        assert res.action == "expired"
        assert "semester has ended" in res.reason.lower()

    def test_burst_workload_safeguard(self, engine):
        """Verify burst CPU spikes prevent false-positive idle classification."""
        metrics = [
            {"cpu_percent": 2.0, "memory_percent": 5.0, "network_bytes": 200},
            {"cpu_percent": 1.0, "memory_percent": 4.0, "network_bytes": 100},
            {"cpu_percent": 85.0, "memory_percent": 80.0, "network_bytes": 900000},  # Burst spike
            {"cpu_percent": 2.0, "memory_percent": 4.0, "network_bytes": 200},
        ]
        res = engine.evaluate_resource(
            resource_id="gpu-ds401-01",
            resource_type="gpu",
            owner_id=5,
            course_is_active=True,
            metrics=metrics,
        )
        assert res.action == "active"
        assert "burst" in res.reason.lower()
        assert res.risk_score >= 80.0

    def test_consistently_idle_resource(self, engine):
        """Verify consistently low utilization is classified as idle."""
        metrics = [
            {"cpu_percent": 1.5, "memory_percent": 3.0, "network_bytes": 200, "gpu_percent": 0.5},
            {"cpu_percent": 2.0, "memory_percent": 4.0, "network_bytes": 300, "gpu_percent": 1.0},
        ]
        res = engine.evaluate_resource(
            resource_id="gpu-cs301-train-01",
            resource_type="gpu",
            owner_id=3,
            course_is_active=True,
            metrics=metrics,
        )
        assert res.action == "idle"
        assert res.requires_approval is True  # GPU requires approval

    def test_break_period_grace_safeguard(self, engine):
        """Verify resource active prior to a break is spared during break period."""
        metrics = [
            {"cpu_percent": 2.0, "memory_percent": 5.0, "network_bytes": 100},
        ]
        extended_pre_break_metrics = [
            {"cpu_percent": 45.0, "memory_percent": 60.0, "network_bytes": 500000},
        ]
        res = engine.evaluate_resource(
            resource_id="vm-cs301-01",
            resource_type="vm",
            owner_id=3,
            course_is_active=True,
            metrics=metrics,
            is_break_period=True,
            extended_break_metrics=extended_pre_break_metrics,
        )
        assert res.action == "active"
        assert "before break" in res.reason.lower()
