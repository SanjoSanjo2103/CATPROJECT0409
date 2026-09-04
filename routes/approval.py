"""
CloudReclaim — Approval Routes
Instructor approval queue: approve, reject, extend reclamation requests.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from auth import login_required, get_current_user
from models import Resource, ReclamationRequest
from reclaimer import approve_reclamation, reject_reclamation, extend_resource
from database import db

approval_bp = Blueprint('approval', __name__)


@approval_bp.route('/approvals')
@login_required
def index():
    user = get_current_user()

    if user.role == 'instructor':
        # Instructors see only their own pending requests
        pending = ReclamationRequest.query.join(Resource).filter(
            ReclamationRequest.status == 'pending',
            Resource.owner_id == user.id
        ).order_by(ReclamationRequest.created_at.desc()).all()
    else:
        # Admins see all pending requests
        pending = ReclamationRequest.query.filter_by(
            status='pending'
        ).order_by(ReclamationRequest.created_at.desc()).all()

    # History (non-pending)
    if user.role == 'instructor':
        history = ReclamationRequest.query.join(Resource).filter(
            ReclamationRequest.status != 'pending',
            Resource.owner_id == user.id
        ).order_by(ReclamationRequest.created_at.desc()).limit(20).all()
    else:
        history = ReclamationRequest.query.filter(
            ReclamationRequest.status != 'pending'
        ).order_by(ReclamationRequest.created_at.desc()).limit(20).all()

    return render_template('approvals.html',
                           user=user,
                           pending=pending,
                           history=history)


@approval_bp.route('/approvals/<int:request_id>/approve', methods=['POST'])
@login_required
def approve(request_id):
    user = get_current_user()
    note = request.form.get('note', '')
    result = approve_reclamation(request_id, user.id, note)

    if result['success']:
        flash(f"Resource {result['resource_id']} reclaimed. Monthly savings: ${result['cost_saved']:.2f}", 'success')
    else:
        flash(result['error'], 'error')

    return redirect(url_for('approval.index'))


@approval_bp.route('/approvals/<int:request_id>/reject', methods=['POST'])
@login_required
def reject(request_id):
    user = get_current_user()
    note = request.form.get('note', '')
    result = reject_reclamation(request_id, user.id, note)

    if result['success']:
        flash(f"Reclamation rejected for {result['resource_id']}. Resource remains active.", 'info')
    else:
        flash(result['error'], 'error')

    return redirect(url_for('approval.index'))


@approval_bp.route('/approvals/<int:request_id>/extend', methods=['POST'])
@login_required
def extend(request_id):
    user = get_current_user()
    note = request.form.get('note', '')
    result = extend_resource(request_id, user.id, note)

    if result['success']:
        flash(f"Resource {result['resource_id']} extended. "
              f"Extensions remaining: {result['extensions_remaining']}", 'success')
    else:
        flash(result['error'], 'error')

    return redirect(url_for('approval.index'))
