"""
CloudReclaim — Reclamation Workflow Engine
Handles grace period enforcement, approval/rejection, extension logic,
snapshot safety checks, and final reclamation execution.
"""

import json
from datetime import datetime, timedelta, timezone
from database import db
from models import Resource, ReclamationRequest, AuditLog, UtilizationMetric
from config import RECLAMATION_RULES


def process_expired_grace_periods():
    """
    Check all pending reclamation requests whose grace deadline has passed.
    Auto-reclaim if no response, respecting safety rules.
    """
    now = datetime.now(timezone.utc)
    rules = RECLAMATION_RULES

    expired = ReclamationRequest.query.filter(
        ReclamationRequest.status == 'pending',
        ReclamationRequest.grace_deadline <= now
    ).all()

    results = {
        'processed': 0,
        'auto_reclaimed': 0,
        'aborted_active': 0,
        'errors': [],
    }

    for req in expired:
        results['processed'] += 1
        resource = Resource.query.get(req.resource_id)

        if not resource:
            results['errors'].append(f'Resource {req.resource_id} not found')
            continue

        # ── Safety Check: Final utilization re-check before reclaiming ──
        # (Edge Case 5: Resource becomes active during reclamation)
        if _is_resource_currently_active(resource, rules):
            req.status = 'rejected'
            req.response_note = 'Auto-aborted: resource showed activity before reclamation'
            req.responded_at = now
            resource.status = 'active'
            results['aborted_active'] += 1

            _log_action(None, 'auto_abort', resource.id,
                        {'reason': 'Activity detected during final check'})
            continue

        # ── Execute Reclamation ──
        if rules.get('snapshot_before_reclaim', True):
            _simulate_snapshot(resource)

        # Check if GPU requires admin approval
        if resource.resource_type == 'gpu' and rules.get('require_approval_for_gpu', True):
            if req.reason != 'manual':  # Admin manual reclaim bypasses this
                req.response_note = 'Awaiting admin approval (GPU resource)'
                # Don't auto-reclaim GPU — leave pending but flag for admin
                _log_action(None, 'notify', resource.id,
                            {'reason': 'GPU resource requires admin approval'})
                continue

        req.status = 'auto_reclaimed'
        req.responded_at = now
        resource.status = 'reclaimed'
        results['auto_reclaimed'] += 1

        _log_action(None, 'auto_reclaim', resource.id,
                    {'reason': req.reason, 'cost_saved': resource.monthly_cost})

    db.session.commit()
    return results


def approve_reclamation(request_id, actor_id, note=None):
    """Instructor or admin approves reclaiming a resource."""
    req = ReclamationRequest.query.get(request_id)
    if not req or req.status != 'pending':
        return {'success': False, 'error': 'Request not found or not pending'}

    resource = Resource.query.get(req.resource_id)
    rules = RECLAMATION_RULES

    # Snapshot before reclaim
    if rules.get('snapshot_before_reclaim', True):
        _simulate_snapshot(resource)

    req.status = 'approved'
    req.responded_at = datetime.now(timezone.utc)
    req.response_note = note or 'Approved by owner'
    req.actioned_by = actor_id
    resource.status = 'reclaimed'

    _log_action(actor_id, 'approve_reclaim', resource.id,
                {'note': note, 'cost_saved': resource.monthly_cost})

    db.session.commit()
    return {'success': True, 'resource_id': resource.resource_id, 'cost_saved': resource.monthly_cost}


def reject_reclamation(request_id, actor_id, note=None):
    """Instructor rejects the reclamation — resource stays active."""
    req = ReclamationRequest.query.get(request_id)
    if not req or req.status != 'pending':
        return {'success': False, 'error': 'Request not found or not pending'}

    resource = Resource.query.get(req.resource_id)

    req.status = 'rejected'
    req.responded_at = datetime.now(timezone.utc)
    req.response_note = note or 'Rejected by owner — resource is needed'
    req.actioned_by = actor_id
    resource.status = 'active'

    _log_action(actor_id, 'reject_reclaim', resource.id, {'note': note})

    db.session.commit()
    return {'success': True, 'resource_id': resource.resource_id}


def extend_resource(request_id, actor_id, note=None):
    """
    Extend a resource's TTL. Limited by max_extensions rule.
    (Edge Case 4: Instructor exhausts max extensions)
    """
    req = ReclamationRequest.query.get(request_id)
    if not req or req.status != 'pending':
        return {'success': False, 'error': 'Request not found or not pending'}

    resource = Resource.query.get(req.resource_id)
    rules = RECLAMATION_RULES

    # Count previous extensions for this resource via AuditLog
    extension_count = AuditLog.query.filter_by(
        resource_id=resource.id,
        action='extend',
    ).count()

    max_ext = rules.get('max_extensions', 2)
    if extension_count >= max_ext:
        return {
            'success': False,
            'error': f'Maximum extensions ({max_ext}) reached. Resource must be approved or will be auto-reclaimed.'
        }

    # Extend TTL
    ext_days = rules.get('extension_duration_days', 14)
    now = datetime.now(timezone.utc)
    resource.ttl_expires_at = now + timedelta(days=ext_days)
    resource.status = 'extended'

    req.status = 'rejected'
    req.responded_at = now
    req.response_note = note or f'Extended by {ext_days} days (extension {extension_count + 1}/{max_ext})'
    req.actioned_by = actor_id

    _log_action(actor_id, 'extend', resource.id,
                {'days': ext_days, 'extension_number': extension_count + 1,
                 'max_extensions': max_ext})

    db.session.commit()
    return {
        'success': True,
        'resource_id': resource.resource_id,
        'new_ttl': resource.ttl_expires_at.isoformat(),
        'extensions_remaining': max_ext - extension_count - 1,
    }


def manual_reclaim(resource_id, actor_id, note=None):
    """Admin manually reclaims a resource (bypasses grace period)."""
    resource = Resource.query.get(resource_id)
    if not resource:
        return {'success': False, 'error': 'Resource not found'}

    rules = RECLAMATION_RULES
    if rules.get('snapshot_before_reclaim', True):
        _simulate_snapshot(resource)

    # Cancel any pending requests
    pending = ReclamationRequest.query.filter_by(
        resource_id=resource.id, status='pending'
    ).all()
    for req in pending:
        req.status = 'approved'
        req.responded_at = datetime.now(timezone.utc)
        req.response_note = 'Overridden by admin manual reclamation'
        req.actioned_by = actor_id

    # Create a new request for the manual action
    manual_req = ReclamationRequest(
        resource_id=resource.id,
        reason='manual',
        status='approved',
        responded_at=datetime.now(timezone.utc),
        response_note=note or 'Manual reclamation by admin',
        actioned_by=actor_id,
    )
    db.session.add(manual_req)

    resource.status = 'reclaimed'
    _log_action(actor_id, 'manual_reclaim', resource.id,
                {'note': note, 'cost_saved': resource.monthly_cost})

    db.session.commit()
    return {'success': True, 'resource_id': resource.resource_id, 'cost_saved': resource.monthly_cost}


def _is_resource_currently_active(resource, rules):
    """
    Final safety check: is the resource showing current activity?
    Looks at the most recent metrics (last 6 hours).
    """
    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=6)

    metrics = UtilizationMetric.query.filter(
        UtilizationMetric.resource_id == resource.id,
        UtilizationMetric.timestamp >= recent
    ).all()

    if not metrics:
        return False  # No recent data — proceed with reclamation

    avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)
    return avg_cpu >= rules.get('cpu_idle_threshold', 5.0) * 3  # 3x threshold = clearly active


def _simulate_snapshot(resource):
    """Simulate creating a data snapshot before reclamation."""
    _log_action(None, 'snapshot', resource.id, {
        'type': 'pre-reclamation snapshot',
        'resource_type': resource.resource_type,
        'simulated': True,
    })


def _log_action(actor_id, action, resource_id, details):
    """Write to audit log."""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_id=resource_id,
        details=json.dumps(details) if isinstance(details, dict) else details,
    )
    db.session.add(log)
