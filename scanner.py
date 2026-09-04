"""
CloudReclaim — Multi-Signal Idle Detection Scanner
Implements the ownership-aware, calendar-aware idle detection algorithm.
Compares multiple utilization signals and contextual data to flag resources.
"""

import json
from datetime import datetime, timedelta, timezone
from database import db
from models import (
    Resource, UtilizationMetric, EnvironmentCalendar,
    ReclamationRequest, AuditLog
)
from config import RECLAMATION_RULES


def run_scan(actor_id=None):
    """
    Execute a full idle detection scan across all active resources.
    Returns a summary dict of actions taken.
    """
    rules = RECLAMATION_RULES
    now = datetime.now(timezone.utc)
    summary = {
        'scanned': 0,
        'flagged_idle': 0,
        'flagged_orphaned': 0,
        'flagged_expired': 0,
        'still_active': 0,
        'already_handled': 0,
        'errors': [],
    }

    # Get all resources that are not already reclaimed
    resources = Resource.query.filter(
        Resource.status.notin_(['reclaimed', 'pending_reclaim'])
    ).all()

    for resource in resources:
        summary['scanned'] += 1
        try:
            result = _evaluate_resource(resource, rules, now)

            if result == 'orphaned':
                resource.status = 'orphaned'
                summary['flagged_orphaned'] += 1
                _create_reclamation_request(resource, 'orphaned', rules, now)
                _log_action(actor_id, 'flag_orphaned', resource.id,
                            {'reason': 'No valid owner assigned'})

            elif result == 'expired':
                resource.status = 'idle'
                summary['flagged_expired'] += 1
                _create_reclamation_request(resource, 'semester_expired', rules, now)
                _log_action(actor_id, 'flag_idle', resource.id,
                            {'reason': 'Course semester has ended'})

            elif result == 'idle':
                resource.status = 'idle'
                summary['flagged_idle'] += 1
                _create_reclamation_request(resource, 'idle_threshold', rules, now)
                _log_action(actor_id, 'flag_idle', resource.id,
                            {'reason': 'Below utilization thresholds'})

            elif result == 'active':
                # If it was previously idle but is now active, reset
                if resource.status == 'idle':
                    resource.status = 'active'
                    # Cancel any pending reclamation requests
                    _cancel_pending_requests(resource.id)
                summary['still_active'] += 1

            else:
                summary['already_handled'] += 1

        except Exception as e:
            summary['errors'].append({
                'resource': resource.resource_id,
                'error': str(e)
            })

    # Log the scan itself
    _log_action(actor_id, 'scan', None, summary)
    db.session.commit()

    return summary


def _evaluate_resource(resource, rules, now):
    """
    Evaluate a single resource through the multi-signal detection pipeline.
    Returns: 'orphaned', 'expired', 'idle', 'active', or 'skip'
    """
    # ── Step 1: Ownership Check ──
    if resource.owner_id is None:
        return 'orphaned'

    # ── Step 2: Calendar Check ──
    course = resource.course
    if course and not course.is_active:
        if rules.get('auto_reclaim_after_semester', True):
            # Check if there's already a pending request
            existing = ReclamationRequest.query.filter_by(
                resource_id=resource.id,
                status='pending'
            ).first()
            if not existing:
                return 'expired'
            return 'skip'

    # ── Step 3: Multi-Signal Utilization Check ──
    idle_days = rules.get('idle_duration_days', 7)
    lookback = now - timedelta(days=idle_days)

    metrics = UtilizationMetric.query.filter(
        UtilizationMetric.resource_id == resource.id,
        UtilizationMetric.timestamp >= lookback
    ).all()

    if not metrics:
        # No data — can't determine; leave as-is
        return 'active'

    # Calculate averages over the window
    avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)
    avg_mem = sum(m.memory_percent for m in metrics) / len(metrics)
    total_net = sum(m.network_bytes for m in metrics)

    cpu_idle = avg_cpu < rules.get('cpu_idle_threshold', 5.0)
    mem_idle = avg_mem < rules.get('memory_idle_threshold', 10.0)
    net_idle = total_net < rules.get('network_idle_threshold', 1024)

    # GPU check (only for GPU resources)
    gpu_idle = True
    if resource.resource_type == 'gpu':
        gpu_metrics = [m.gpu_percent for m in metrics if m.gpu_percent is not None]
        if gpu_metrics:
            avg_gpu = sum(gpu_metrics) / len(gpu_metrics)
            gpu_idle = avg_gpu < rules.get('gpu_idle_threshold', 5.0)

    # ALL signals must indicate idle
    all_idle = cpu_idle and mem_idle and net_idle and gpu_idle

    if all_idle:
        # Check if we're in a break period — be more lenient
        if _is_break_period(now):
            # During breaks, require longer idle duration
            extended_days = idle_days + rules.get('break_period_grace_days', 7)
            extended_lookback = now - timedelta(days=extended_days)
            extended_metrics = UtilizationMetric.query.filter(
                UtilizationMetric.resource_id == resource.id,
                UtilizationMetric.timestamp >= extended_lookback
            ).all()

            if extended_metrics:
                ext_avg_cpu = sum(m.cpu_percent for m in extended_metrics) / len(extended_metrics)
                if ext_avg_cpu >= rules.get('cpu_idle_threshold', 5.0):
                    return 'active'  # Was active before the break

        # Check for burst patterns — any spike in the window?
        max_cpu = max(m.cpu_percent for m in metrics)
        if max_cpu > 50.0:
            # There was a significant spike — likely a burst workload
            return 'active'

        # Check for existing pending request
        existing = ReclamationRequest.query.filter_by(
            resource_id=resource.id,
            status='pending'
        ).first()
        if existing:
            return 'skip'

        return 'idle'

    return 'active'


def _is_break_period(dt):
    """Check if the given datetime falls within a break or maintenance period."""
    check_date = dt.date() if isinstance(dt, datetime) else dt
    period = EnvironmentCalendar.query.filter(
        EnvironmentCalendar.period_type.in_(['break', 'maintenance']),
        EnvironmentCalendar.start_date <= check_date,
        EnvironmentCalendar.end_date >= check_date,
    ).first()
    return period is not None


def _create_reclamation_request(resource, reason, rules, now):
    """Create a new reclamation request with appropriate grace period."""
    grace_hours = rules.get('grace_period_hours', 72)

    # Extend grace if we're in a break period
    if _is_break_period(now):
        grace_hours += rules.get('break_period_grace_days', 7) * 24

    deadline = now + timedelta(hours=grace_hours)

    request = ReclamationRequest(
        resource_id=resource.id,
        reason=reason,
        status='pending',
        created_at=now,
        grace_deadline=deadline,
    )
    db.session.add(request)

    # Update resource status
    if reason == 'orphaned':
        resource.status = 'orphaned'
    else:
        resource.status = 'pending_reclaim'


def _cancel_pending_requests(resource_id):
    """Cancel all pending reclamation requests for a resource."""
    pending = ReclamationRequest.query.filter_by(
        resource_id=resource_id,
        status='pending'
    ).all()
    for req in pending:
        req.status = 'rejected'
        req.response_note = 'Auto-cancelled: resource became active'
        req.responded_at = datetime.now(timezone.utc)


def _log_action(actor_id, action, resource_id, details):
    """Write an entry to the audit log."""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_id=resource_id,
        details=json.dumps(details) if isinstance(details, dict) else details,
    )
    db.session.add(log)


def get_scan_stats():
    """Get statistics from the most recent scan for the dashboard."""
    resources = Resource.query.all()
    stats = {
        'total_resources': len(resources),
        'active': sum(1 for r in resources if r.status == 'active'),
        'idle': sum(1 for r in resources if r.status in ('idle', 'pending_reclaim')),
        'orphaned': sum(1 for r in resources if r.status == 'orphaned'),
        'reclaimed': sum(1 for r in resources if r.status == 'reclaimed'),
        'extended': sum(1 for r in resources if r.status == 'extended'),
        'total_monthly_cost': sum(r.monthly_cost for r in resources),
        'idle_monthly_cost': sum(r.monthly_cost for r in resources
                                  if r.status in ('idle', 'pending_reclaim', 'orphaned')),
        'reclaimed_savings': sum(r.monthly_cost for r in resources
                                  if r.status == 'reclaimed'),
    }
    return stats
