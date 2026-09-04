"""
CloudReclaim — Dashboard Routes
Main dashboard with KPIs, cost trends, status breakdown.
"""

from flask import Blueprint, render_template
from auth import login_required, get_current_user
from scanner import get_scan_stats
from models import Resource, ReclamationRequest, AuditLog
from database import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    user = get_current_user()
    stats = get_scan_stats()

    # Recent activity
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    # Pending approvals count (for instructor badge)
    if user.role == 'instructor':
        pending_count = ReclamationRequest.query.join(Resource).filter(
            ReclamationRequest.status == 'pending',
            Resource.owner_id == user.id
        ).count()
    else:
        pending_count = ReclamationRequest.query.filter_by(status='pending').count()

    # Cost breakdown by resource type
    cost_by_type = {}
    resources = Resource.query.all()
    for r in resources:
        rtype = r.resource_type
        if rtype not in cost_by_type:
            cost_by_type[rtype] = {'total': 0, 'idle': 0}
        cost_by_type[rtype]['total'] += r.monthly_cost
        if r.status in ('idle', 'pending_reclaim', 'orphaned'):
            cost_by_type[rtype]['idle'] += r.monthly_cost

    return render_template('dashboard.html',
                           user=user,
                           stats=stats,
                           recent_logs=recent_logs,
                           pending_count=pending_count,
                           cost_by_type=cost_by_type)
