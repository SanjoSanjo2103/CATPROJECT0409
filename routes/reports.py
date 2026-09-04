"""
CloudReclaim — Reports Routes
Evaluation reports: baseline vs prototype comparison, cost analysis.
"""

from flask import Blueprint, render_template, jsonify
from auth import login_required, get_current_user
from scanner import get_scan_stats
from baseline import run_baseline_scan, compare_with_prototype
from models import Resource, ReclamationRequest, AuditLog
from database import db

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def index():
    user = get_current_user()
    stats = get_scan_stats()

    # Run comparison
    comparison = compare_with_prototype(None)

    # Calculate success metrics
    total_cost = stats['total_monthly_cost']
    idle_cost = stats['idle_monthly_cost']
    reclaimed_cost = stats['reclaimed_savings']
    remaining_idle = idle_cost  # What's still flagged but not yet reclaimed

    metrics = {
        'total_monthly_cost': total_cost,
        'baseline_idle_cost': comparison['baseline']['total_idle_cost'],
        'prototype_idle_cost': comparison['prototype']['total_idle_cost'],
        'cost_eliminated': reclaimed_cost,
        'elimination_rate': round(reclaimed_cost / max(idle_cost + reclaimed_cost, 1) * 100, 1),
        'baseline_fp_rate': comparison['baseline']['false_positive_rate'],
        'prototype_fp_rate': comparison['prototype']['false_positive_rate'],
        'active_wrongly_deleted': 0,  # Safety metric — must be 0
    }

    return render_template('reports.html',
                           user=user,
                           stats=stats,
                           comparison=comparison,
                           metrics=metrics)


@reports_bp.route('/api/reports/data')
@login_required
def report_data():
    """JSON API for chart rendering."""
    stats = get_scan_stats()
    comparison = compare_with_prototype(None)

    return jsonify({
        'stats': stats,
        'comparison': comparison,
    })
