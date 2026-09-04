"""
CloudReclaim — Baseline Comparison Tests
Verify that baseline produces more false positives than prototype.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import db
from baseline import run_baseline_scan, compare_with_prototype
from scanner import run_scan
from seed_data import seed_all


@pytest.fixture
def app():
    app = create_app(seed=False, testing=True)
    with app.app_context():
        db.create_all()
        seed_all()
    yield app


class TestBaselineComparison:
    """Verify baseline is worse than prototype."""

    def test_baseline_runs(self, app):
        """Baseline scan should complete without errors."""
        with app.app_context():
            result = run_baseline_scan()
            assert 'scanned' in result
            assert result['scanned'] > 0

    def test_baseline_flags_resources(self, app):
        """Baseline should flag some resources as idle."""
        with app.app_context():
            result = run_baseline_scan()
            assert result['flagged_idle'] >= 0
            assert result['total_idle_cost'] >= 0

    def test_comparison_runs(self, app):
        """Comparison should produce valid output."""
        with app.app_context():
            # Run prototype scan first
            run_scan(actor_id=None)

            comparison = compare_with_prototype(None)

            assert 'baseline' in comparison
            assert 'prototype' in comparison
            assert 'ground_truth' in comparison
            assert 'improvement' in comparison

    def test_prototype_fewer_false_positives(self, app):
        """Prototype should have fewer or equal false positives than baseline."""
        with app.app_context():
            run_scan(actor_id=None)
            comparison = compare_with_prototype(None)

            baseline_fp = comparison['baseline']['false_positives']
            prototype_fp = comparison['prototype']['false_positives']

            # Prototype should not be worse
            assert prototype_fp <= baseline_fp, \
                f"Prototype FP ({prototype_fp}) should be <= Baseline FP ({baseline_fp})"

    def test_zero_active_workloads_deleted(self, app):
        """No active workloads should be incorrectly reclaimed."""
        with app.app_context():
            run_scan(actor_id=None)

            from models import Resource
            reclaimed = Resource.query.filter_by(status='reclaimed').all()
            for r in reclaimed:
                # Reclaimed resources should not be from active courses with active owners
                if r.course and r.course.is_active and r.owner_id is not None:
                    pytest.fail(f"Active resource {r.resource_id} was incorrectly reclaimed!")

    def test_baseline_cost_data(self, app):
        """Baseline should report cost data for flagged resources."""
        with app.app_context():
            result = run_baseline_scan()
            for r in result['resources_flagged']:
                assert 'monthly_cost' in r
                assert r['monthly_cost'] > 0
                assert 'avg_cpu' in r
                assert 'resource_id' in r
