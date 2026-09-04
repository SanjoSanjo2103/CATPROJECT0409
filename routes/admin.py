"""
CloudReclaim — Admin Routes
Rule configuration, orphan management, manual scans, audit log.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from auth import login_required, role_required, get_current_user
from config import RECLAMATION_RULES, get_rules, update_rule
from scanner import run_scan
from reclaimer import manual_reclaim, process_expired_grace_periods
from models import Resource, AuditLog
from database import db
import json

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/config', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def config():
    user = get_current_user()

    if request.method == 'POST':
        changes = []
        for key in RECLAMATION_RULES:
            form_value = request.form.get(key)
            if form_value is not None:
                old_value = RECLAMATION_RULES[key]
                if update_rule(key, form_value):
                    new_value = RECLAMATION_RULES[key]
                    if old_value != new_value:
                        changes.append({'key': key, 'old': old_value, 'new': new_value})

        if changes:
            # Audit log the changes
            log = AuditLog(
                actor_id=user.id,
                action='config_change',
                details=json.dumps(changes),
            )
            db.session.add(log)
            db.session.commit()
            flash(f'{len(changes)} rule(s) updated successfully.', 'success')
        else:
            flash('No changes detected.', 'info')

        return redirect(url_for('admin.config'))

    rules = get_rules()
    return render_template('admin_config.html', user=user, rules=rules)


@admin_bp.route('/admin/scan', methods=['POST'])
@login_required
@role_required('admin')
def trigger_scan():
    user = get_current_user()
    result = run_scan(actor_id=user.id)
    flash(f"Scan complete: {result['scanned']} scanned, {result['flagged_idle']} idle, "
          f"{result['flagged_orphaned']} orphaned, {result['flagged_expired']} expired.", 'success')
    return redirect(url_for('dashboard.index'))


@admin_bp.route('/admin/process-grace', methods=['POST'])
@login_required
@role_required('admin')
def trigger_grace_processing():
    user = get_current_user()
    result = process_expired_grace_periods()
    flash(f"Grace check: {result['processed']} processed, {result['auto_reclaimed']} reclaimed, "
          f"{result['aborted_active']} aborted.", 'success')
    return redirect(url_for('dashboard.index'))


@admin_bp.route('/admin/reclaim/<int:resource_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_reclaim(resource_id):
    user = get_current_user()
    note = request.form.get('note', 'Manual reclamation by admin')
    result = manual_reclaim(resource_id, user.id, note)

    if result['success']:
        flash(f"Resource {result['resource_id']} manually reclaimed. "
              f"Monthly savings: ${result['cost_saved']:.2f}", 'success')
    else:
        flash(result['error'], 'error')

    return redirect(url_for('resources.index'))


@admin_bp.route('/admin/audit')
@login_required
@role_required('admin')
def audit_log():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    logs = AuditLog.query.order_by(
        AuditLog.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('audit_log.html', user=user, logs=logs)
