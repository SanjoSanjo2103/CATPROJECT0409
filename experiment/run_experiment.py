"""
CloudReclaim — Automated Experiment Runner
Seeds data, runs both baseline and prototype, collects metrics,
and outputs results.json with measured outcomes.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import db
from seed_data import seed_all
from scanner import run_scan, get_scan_stats
from baseline import run_baseline_scan, compare_with_prototype
from reclaimer import process_expired_grace_periods, approve_reclamation
from models import Resource, ReclamationRequest
from datetime import datetime, timedelta, timezone


def run_experiment():
    """Run the full experiment and produce results."""
    print("=" * 60)
    print("  CloudReclaim — Experiment Runner")
    print("=" * 60)

    app = create_app(seed=True)

    with app.app_context():
        results = {}

        # ── Step 1: Baseline Measurement ──
        print("\n[1/5] Running baseline scan (CPU-only)...")
        baseline_results = run_baseline_scan()
        results['baseline'] = {
            'scanned': baseline_results['scanned'],
            'flagged_idle': baseline_results['flagged_idle'],
            'total_idle_cost': baseline_results['total_idle_cost'],
            'resources_flagged': len(baseline_results['resources_flagged']),
        }
        print(f"  Baseline: {baseline_results['flagged_idle']} flagged, "
              f"${baseline_results['total_idle_cost']:.2f} idle cost")

        # ── Step 2: Prototype Scan ──
        print("\n[2/5] Running prototype scan (multi-signal)...")
        scan_results = run_scan(actor_id=1)
        stats_after_scan = get_scan_stats()
        results['prototype_scan'] = {
            'scanned': scan_results['scanned'],
            'flagged_idle': scan_results['flagged_idle'],
            'flagged_orphaned': scan_results['flagged_orphaned'],
            'flagged_expired': scan_results['flagged_expired'],
            'still_active': scan_results['still_active'],
            'total_idle_cost': stats_after_scan['idle_monthly_cost'],
        }
        print(f"  Prototype: {scan_results['flagged_idle']} idle, "
              f"{scan_results['flagged_orphaned']} orphaned, "
              f"{scan_results['flagged_expired']} expired")

        # ── Step 3: Simulate Approvals ──
        print("\n[3/5] Simulating approval workflow...")
        pending = ReclamationRequest.query.filter_by(status='pending').all()
        approved_count = 0
        total_savings = 0.0

        for req in pending:
            resource = Resource.query.get(req.resource_id)
            if not resource:
                continue

            # Auto-approve expired and orphaned resources
            if req.reason in ('semester_expired', 'orphaned'):
                result = approve_reclamation(req.id, actor_id=1, note='Auto-approved in experiment')
                if result['success']:
                    approved_count += 1
                    total_savings += result['cost_saved']

        results['approvals'] = {
            'total_pending': len(pending),
            'approved': approved_count,
            'total_savings': total_savings,
        }
        print(f"  Approved {approved_count} of {len(pending)} requests, "
              f"savings: ${total_savings:.2f}/month")

        # ── Step 4: Comparison ──
        print("\n[4/5] Computing baseline vs prototype comparison...")
        comparison = compare_with_prototype(None)
        results['comparison'] = comparison

        print(f"  Baseline FP rate: {comparison['baseline']['false_positive_rate']}%")
        print(f"  Prototype FP rate: {comparison['prototype']['false_positive_rate']}%")
        print(f"  FP reduction: {comparison['improvement']['fp_reduction']}")

        # ── Step 5: Final Metrics ──
        print("\n[5/5] Computing success metrics...")
        final_stats = get_scan_stats()

        # Primary success metric: idle cost eliminated without deleting active workloads
        active_wrongly_deleted = 0
        reclaimed = Resource.query.filter_by(status='reclaimed').all()
        for r in reclaimed:
            if r.course and r.course.is_active and r.owner_id is not None:
                active_wrongly_deleted += 1

        total_idle_before = baseline_results['total_idle_cost']
        cost_eliminated = total_savings
        elimination_rate = round(cost_eliminated / max(total_idle_before, 1) * 100, 1)

        results['success_metrics'] = {
            'total_monthly_cost': final_stats['total_monthly_cost'],
            'baseline_idle_cost': total_idle_before,
            'cost_eliminated': cost_eliminated,
            'elimination_rate_pct': elimination_rate,
            'target_elimination_rate_pct': 60.0,
            'target_met': elimination_rate >= 60.0,
            'active_wrongly_deleted': active_wrongly_deleted,
            'zero_wrongful_deletion_met': active_wrongly_deleted == 0,
            'baseline_fp_rate': comparison['baseline']['false_positive_rate'],
            'prototype_fp_rate': comparison['prototype']['false_positive_rate'],
            'prototype_fp_below_5pct': comparison['prototype']['false_positive_rate'] < 5.0,
        }

        results['metadata'] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_resources': final_stats['total_resources'],
            'seed': 42,
            'idle_duration_days': 7,
        }

        # ── Output ──
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results.json')
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print("\n" + "=" * 60)
        print("  EXPERIMENT RESULTS")
        print("=" * 60)
        print(f"  Monthly idle cost (baseline):    ${total_idle_before:.2f}")
        print(f"  Monthly cost eliminated:         ${cost_eliminated:.2f}")
        print(f"  Elimination rate:                {elimination_rate}% (target: >=60%)")
        print(f"  Active workloads deleted:        {active_wrongly_deleted} (target: 0)")
        print(f"  Baseline FP rate:                {comparison['baseline']['false_positive_rate']}%")
        print(f"  Prototype FP rate:               {comparison['prototype']['false_positive_rate']}% (target: <5%)")
        print(f"  Results saved to:                {output_path}")
        print("=" * 60)

        return results


if __name__ == '__main__':
    run_experiment()
