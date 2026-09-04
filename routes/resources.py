"""
CloudReclaim — Resource Routes
Resource inventory listing, filtering, and detail views.
"""

from flask import Blueprint, render_template, request, jsonify
from auth import login_required, get_current_user
from models import Resource, Course, UtilizationMetric
from database import db

resources_bp = Blueprint('resources', __name__)


@resources_bp.route('/resources')
@login_required
def index():
    user = get_current_user()

    # Filters
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type', 'all')
    course_filter = request.args.get('course', 'all')

    query = Resource.query

    # Instructors only see their own resources
    if user.role == 'instructor':
        query = query.filter(Resource.owner_id == user.id)

    if status_filter != 'all':
        query = query.filter(Resource.status == status_filter)
    if type_filter != 'all':
        query = query.filter(Resource.resource_type == type_filter)
    if course_filter != 'all':
        query = query.join(Course).filter(Course.code == course_filter)

    resources = query.order_by(Resource.status, Resource.resource_id).all()

    # Get filter options
    courses = Course.query.order_by(Course.code).all()
    statuses = ['active', 'idle', 'orphaned', 'pending_reclaim', 'reclaimed', 'extended']
    types = ['vm', 'gpu', 'storage', 'notebook']

    return render_template('resources.html',
                           user=user,
                           resources=resources,
                           courses=courses,
                           statuses=statuses,
                           types=types,
                           current_status=status_filter,
                           current_type=type_filter,
                           current_course=course_filter)


@resources_bp.route('/resources/<int:resource_id>')
@login_required
def detail(resource_id):
    user = get_current_user()
    resource = Resource.query.get_or_404(resource_id)

    # Instructors can only view their own resources
    if user.role == 'instructor' and resource.owner_id != user.id:
        return render_template('error.html', message='Access denied'), 403

    # Get utilization metrics (last 30 days, aggregated by day)
    metrics = UtilizationMetric.query.filter_by(
        resource_id=resource.id
    ).order_by(UtilizationMetric.timestamp).all()

    # Get reclamation history
    from models import ReclamationRequest
    requests = ReclamationRequest.query.filter_by(
        resource_id=resource.id
    ).order_by(ReclamationRequest.created_at.desc()).all()

    return render_template('resource_detail.html',
                           user=user,
                           resource=resource,
                           metrics=[m.to_dict() for m in metrics],
                           requests=requests)
