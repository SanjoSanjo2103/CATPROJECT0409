"""
CloudReclaim — Scheduler Jobs
APScheduler job definitions for periodic scans and grace period enforcement.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from config import RECLAMATION_RULES

scheduler = BackgroundScheduler()


def init_scheduler(app):
    """Initialize and start the background scheduler."""
    rules = RECLAMATION_RULES
    interval_hours = rules.get('scan_interval_hours', 24)

    # Job 1: Periodic idle detection scan
    scheduler.add_job(
        func=_run_scan_job,
        trigger='interval',
        hours=interval_hours,
        id='idle_scan',
        name='Periodic Idle Resource Scan',
        replace_existing=True,
        kwargs={'app': app},
    )

    # Job 2: Process expired grace periods (every hour)
    scheduler.add_job(
        func=_process_grace_job,
        trigger='interval',
        hours=1,
        id='grace_check',
        name='Grace Period Enforcement',
        replace_existing=True,
        kwargs={'app': app},
    )

    scheduler.start()
    print(f"[SCHEDULER] Started — scan every {interval_hours}h, grace check every 1h")


def _run_scan_job(app):
    """Run the idle detection scan within the app context."""
    with app.app_context():
        from scanner import run_scan
        result = run_scan(actor_id=None)
        print(f"[SCAN JOB] Completed: {result}")


def _process_grace_job(app):
    """Process expired grace periods within the app context."""
    with app.app_context():
        from reclaimer import process_expired_grace_periods
        result = process_expired_grace_periods()
        print(f"[GRACE JOB] Completed: {result}")


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
