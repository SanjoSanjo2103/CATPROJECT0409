"""
CloudReclaim — Simple Baseline (CPU-Only)
Single-metric idle detection for comparison with the prototype.
No ownership check, no calendar awareness, no approval workflow.
"""

from datetime import datetime, timedelta, timezone
from database import db
from models import Resource, UtilizationMetric
from config import RECLAMATION_RULES


def run_baseline_scan():
    """
    Baseline idle detection: flag any resource whose average CPU
    over the last 7 days is below the threshold.

    This is intentionally naive — no ownership, no calendar, no multi-signal.
    Used to demonstrate why the prototype is better.
    """
    rules = RECLAMATION_RULES
    now = datetime.now(timezone.utc)
    threshold = rules.get('cpu_idle_threshold', 5.0)
    window_days = rules.get('idle_duration_days', 7)
    lookback = now - timedelta(days=window_days)

    results = {
        'scanned': 0,
        'flagged_idle': 0,
        'still_active': 0,
        'false_positives': 0,   # Will be computed during experiment
        'false_negatives': 0,
        'total_idle_cost': 0.0,
        'resources_flagged': [],
        'resources_missed': [],
    }

    resources = Resource.query.filter(
        Resource.status.notin_(['reclaimed'])
    ).all()

    for resource in resources:
        results['scanned'] += 1

        # Only check CPU — that's the baseline's single signal
        metrics = UtilizationMetric.query.filter(
            UtilizationMetric.resource_id == resource.id,
            UtilizationMetric.timestamp >= lookback
        ).all()

        if not metrics:
            results['still_active'] += 1
            continue

        avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)

        if avg_cpu < threshold:
            results['flagged_idle'] += 1
            results['total_idle_cost'] += resource.monthly_cost
            results['resources_flagged'].append({
                'resource_id': resource.resource_id,
                'resource_type': resource.resource_type,
                'avg_cpu': round(avg_cpu, 2),
                'monthly_cost': resource.monthly_cost,
                'course': resource.course.code if resource.course else 'Unknown',
                'owner': resource.owner.full_name if resource.owner else 'None',
                'actual_status': resource.status,
            })
        else:
            results['still_active'] += 1

    return results


def compare_with_prototype(prototype_results):
    """
    Compare baseline results with prototype results to quantify improvement.
    Returns a comparison dict using the BaselineEvaluator module.
    """
    from baseline_evaluator import BaselineEvaluator

    baseline = run_baseline_scan()

    baseline_flagged_ids = {r['resource_id'] for r in baseline['resources_flagged']}
    proto_flagged_ids = set()

    # Get prototype flagged resources
    proto_resources = Resource.query.filter(
        Resource.status.in_(['idle', 'pending_reclaim', 'orphaned', 'reclaimed'])
    ).all()
    for r in proto_resources:
        proto_flagged_ids.add(r.resource_id)

    # Determine ground truth (from synthetic data patterns)
    truly_idle_ids = set()
    truly_active_ids = set()

    all_resources = Resource.query.all()
    resource_costs = {r.resource_id: r.monthly_cost for r in all_resources}

    for r in all_resources:
        course = r.course
        if r.owner_id is None:
            truly_idle_ids.add(r.resource_id)  # orphaned = truly idle
        elif course and not course.is_active:
            truly_idle_ids.add(r.resource_id)  # expired = truly idle
        elif 'ds401' in r.resource_id and r.resource_type == 'gpu':
            truly_active_ids.add(r.resource_id)  # burst GPU = truly active
        else:
            now = datetime.now(timezone.utc)
            lookback = now - timedelta(days=7)
            metrics = UtilizationMetric.query.filter(
                UtilizationMetric.resource_id == r.id,
                UtilizationMetric.timestamp >= lookback
            ).all()
            if metrics:
                avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)
                if avg_cpu >= 10.0:
                    truly_active_ids.add(r.resource_id)
                else:
                    truly_idle_ids.add(r.resource_id)

    evaluator = BaselineEvaluator()
    report = evaluator.evaluate(
        all_resource_ids=[r.resource_id for r in all_resources],
        resource_costs=resource_costs,
        baseline_flagged_ids=baseline_flagged_ids,
        prototype_flagged_ids=proto_flagged_ids,
        ground_truth_idle_ids=truly_idle_ids,
    )

    baseline_fp = baseline_flagged_ids & truly_active_ids
    proto_fp = proto_flagged_ids & truly_active_ids

    return {
        'baseline': {
            'total_flagged': report.baseline_flagged,
            'true_positives': report.baseline_tp,
            'false_positives': report.baseline_fp,
            'false_negatives': report.baseline_fn,
            'false_positive_rate': round(report.baseline_fp_rate, 1),
            'total_idle_cost': baseline['total_idle_cost'],
            'flagged_resources': list(baseline_flagged_ids),
            'false_positive_resources': list(baseline_fp),
        },
        'prototype': {
            'total_flagged': report.prototype_flagged,
            'true_positives': report.prototype_tp,
            'false_positives': report.prototype_fp,
            'false_negatives': report.prototype_fn,
            'false_positive_rate': round(report.prototype_fp_rate, 1),
            'total_idle_cost': sum(r.monthly_cost for r in proto_resources),
            'flagged_resources': list(proto_flagged_ids),
            'false_positive_resources': list(proto_fp),
        },
        'ground_truth': {
            'total_truly_idle': report.ground_truth_idle_count,
            'total_truly_active': report.ground_truth_active_count,
            'truly_idle_resources': list(truly_idle_ids),
        },
        'improvement': {
            'fp_reduction': report.fp_reduction,
            'fn_reduction': report.fn_reduction,
        }
    }

