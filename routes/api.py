"""
CloudReclaim — JSON API Routes
AJAX endpoints for frontend dynamic updates.
"""

from flask import Blueprint, jsonify, request
from auth import login_required, get_current_user
from models import Resource, UtilizationMetric, ReclamationRequest, AuditLog, Course
from scanner import get_scan_stats
from database import db

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/stats')
@login_required
def stats():
    return jsonify(get_scan_stats())


@api_bp.route('/api/resources')
@login_required
def resources_list():
    user = get_current_user()
    query = Resource.query
    if user.role == 'instructor':
        query = query.filter(Resource.owner_id == user.id)

    resources = query.all()
    return jsonify([r.to_dict() for r in resources])


@api_bp.route('/api/resources/<int:resource_id>/metrics')
@login_required
def resource_metrics(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    metrics = UtilizationMetric.query.filter_by(
        resource_id=resource.id
    ).order_by(UtilizationMetric.timestamp).all()

    return jsonify([m.to_dict() for m in metrics])


@api_bp.route('/api/cost-breakdown')
@login_required
def cost_breakdown():
    resources = Resource.query.all()

    by_status = {}
    by_type = {}
    by_course = {}

    for r in resources:
        # By status
        s = r.status
        by_status[s] = by_status.get(s, 0) + r.monthly_cost

        # By type
        t = r.resource_type
        by_type[t] = by_type.get(t, 0) + r.monthly_cost

        # By course
        c = r.course.code if r.course else 'Unassigned'
        by_course[c] = by_course.get(c, 0) + r.monthly_cost

    return jsonify({
        'by_status': by_status,
        'by_type': by_type,
        'by_course': by_course,
    })


@api_bp.route('/api/calendar')
@login_required
def calendar():
    from models import EnvironmentCalendar
    entries = EnvironmentCalendar.query.order_by(EnvironmentCalendar.start_date).all()
    return jsonify([e.to_dict() for e in entries])


@api_bp.route('/api/notifications')
@login_required
def notifications():
    """Get simulated notifications for the current user."""
    user = get_current_user()

    notifs = []

    # Pending reclamation requests for this user's resources
    if user.role == 'instructor':
        pending = ReclamationRequest.query.join(Resource).filter(
            ReclamationRequest.status == 'pending',
            Resource.owner_id == user.id
        ).all()
    else:
        pending = ReclamationRequest.query.filter_by(status='pending').all()

    for req in pending:
        resource = Resource.query.get(req.resource_id)
        notifs.append({
            'type': 'warning',
            'title': f'Reclamation pending: {resource.resource_id}',
            'message': f'Reason: {req.reason}. Deadline: {req.grace_deadline.strftime("%Y-%m-%d %H:%M") if req.grace_deadline else "N/A"}',
            'request_id': req.id,
            'timestamp': req.created_at.isoformat() if req.created_at else None,
        })

    return jsonify(notifs)
