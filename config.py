"""
CloudReclaim — Configurable Rules
All thresholds and policies are defined here and can be overridden
at runtime via the Admin UI. Changes are persisted to the database
and audit-logged.
"""

import os

# ─── Flask Configuration ───────────────────────────────────────────
class FlaskConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cloudreclaim-dev-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///cloudreclaim.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# ─── Reclamation Rules (Editable via Admin UI) ─────────────────────
RECLAMATION_RULES = {
    # ── Utilization Thresholds ──
    "cpu_idle_threshold": 5.0,           # % — average CPU below this = idle signal
    "memory_idle_threshold": 10.0,       # % — average memory below this = idle signal
    "network_idle_threshold": 1024,      # bytes/period — total network below this = idle signal
    "gpu_idle_threshold": 5.0,           # % — average GPU below this = idle signal (GPU resources only)
    "idle_duration_days": 7,             # consecutive days ALL metrics must be below thresholds

    # ── Grace Periods ──
    "grace_period_hours": 72,            # hours owner has to respond before auto-reclaim
    "max_extensions": 2,                 # max times an instructor can extend a resource TTL
    "extension_duration_days": 14,       # days added per extension

    # ── Calendar Rules ──
    "auto_reclaim_after_semester": True,  # auto-flag resources when their semester ends
    "break_period_grace_days": 7,        # extra grace days during break/maintenance periods

    # ── Safety ──
    "snapshot_before_reclaim": True,      # always snapshot data before stopping a resource
    "require_approval_for_gpu": True,     # GPU resources require manual admin approval to reclaim

    # ── Scan Schedule ──
    "scan_interval_hours": 24,           # how often the idle detection scan runs

    # ── Cost Defaults (per hour, USD) ──
    "cost_per_hour_vm": 0.10,
    "cost_per_hour_gpu": 1.50,
    "cost_per_hour_storage": 0.02,
    "cost_per_hour_notebook": 0.08,
}


def get_rules():
    """Return a copy of the current rules dict."""
    return dict(RECLAMATION_RULES)


def update_rule(key, value):
    """Update a single rule. Returns True if the key exists."""
    if key in RECLAMATION_RULES:
        # Type-cast to match original type
        original_type = type(RECLAMATION_RULES[key])
        if original_type == bool:
            RECLAMATION_RULES[key] = str(value).lower() in ('true', '1', 'yes')
        else:
            RECLAMATION_RULES[key] = original_type(value)
        return True
    return False
