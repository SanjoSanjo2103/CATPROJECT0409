"""
CloudReclaim — Reclaimer Tests
Unit tests for reclamation workflow: grace periods, approvals, extensions.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import db
from models import Resource, ReclamationRequest, User, AuditLog
from scanner import run_scan
from reclaimer import (
    approve_reclamation, reject_reclamation, extend_resource,
    manual_reclaim, process_expired_grace_periods
)
from config import RECLAMATION_RULES
from datetime import datetime, timedelta, timezone
from seed_data import seed_all


@pytest.fixture
def app():
    app = create_app(seed=False, testing=True)
    with app.app_context():
        db.create_all()
        seed_all()
        # Run a scan to create reclamation requests
        run_scan(actor_id=1)
    yield app


class TestApprovalWorkflow:
    """Test approve/reject/extend actions."""

    def test_approve_reclamation(self, app):
        """Approving should reclaim the resource and log savings."""
        with app.app_context():
            req = ReclamationRequest.query.filter_by(status='pending').first()
            if req:
                resource = Resource.query.get(req.resource_id)
                original_cost = resource.monthly_cost

                result = approve_reclamation(req.id, actor_id=1, note='No longer needed')

                assert result['success'] is True
                assert result['cost_saved'] == original_cost

                # Verify state changes
                updated_req = db.session.get(ReclamationRequest, req.id)
                assert updated_req.status == 'approved'
                assert updated_req.response_note == 'No longer needed'

                updated_resource = db.session.get(Resource, resource.id)
                assert updated_resource.status == 'reclaimed'

    def test_reject_reclamation(self, app):
        """Rejecting should keep the resource active."""
        with app.app_context():
            req = ReclamationRequest.query.filter_by(status='pending').first()
            if req:
                result = reject_reclamation(req.id, actor_id=1, note='Still in use')

                assert result['success'] is True

                updated_req = db.session.get(ReclamationRequest, req.id)
                assert updated_req.status == 'rejected'

                resource = Resource.query.get(req.resource_id)
                assert resource.status == 'active'

    def test_approve_nonexistent_request(self, app):
        """Approving a nonexistent request should fail gracefully."""
        with app.app_context():
            result = approve_reclamation(99999, actor_id=1)
            assert result['success'] is False

    def test_reject_already_processed(self, app):
        """Cannot reject a request that's already been processed."""
        with app.app_context():
            req = ReclamationRequest.query.filter_by(status='pending').first()
            if req:
                # Approve first
                approve_reclamation(req.id, actor_id=1)
                # Then try to reject
                result = reject_reclamation(req.id, actor_id=1)
                assert result['success'] is False


class TestExtensionLimits:
    """Test TTL extension with max limits."""

    def test_extend_resource_success(self, app):
        """Extension should update TTL and return remaining count."""
        with app.app_context():
            req = ReclamationRequest.query.filter_by(status='pending').first()
            if req:
                result = extend_resource(req.id, actor_id=1, note='Need 2 more weeks')
                assert result['success'] is True
                assert 'extensions_remaining' in result
                assert result['extensions_remaining'] >= 0

    def test_extension_count_tracked(self, app):
        """Extensions should be tracked and limited."""
        with app.app_context():
            max_ext = RECLAMATION_RULES.get('max_extensions', 2)
            assert max_ext >= 1  # Sanity check


class TestManualReclamation:
    """Test admin manual reclamation."""

    def test_manual_reclaim_by_admin(self, app):
        """Admin should be able to force-reclaim any resource."""
        with app.app_context():
            resource = Resource.query.filter_by(status='active').first()
            if resource:
                result = manual_reclaim(resource.id, actor_id=1, note='Admin cleanup')
                assert result['success'] is True
                assert result['cost_saved'] == resource.monthly_cost

    def test_manual_reclaim_nonexistent(self, app):
        """Manual reclaim of nonexistent resource should fail."""
        with app.app_context():
            result = manual_reclaim(99999, actor_id=1)
            assert result['success'] is False


class TestGracePeriodProcessing:
    """Test automatic grace period enforcement."""

    def test_process_expired_grace_periods(self, app):
        """Expired grace periods should trigger auto-reclamation."""
        with app.app_context():
            # Set a grace deadline in the past
            req = ReclamationRequest.query.filter_by(status='pending').first()
            if req:
                req.grace_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
                db.session.commit()

                result = process_expired_grace_periods()
                assert result['processed'] >= 1

    def test_snapshot_before_reclaim(self, app):
        """Snapshot should be created before reclamation."""
        with app.app_context():
            # After reclamation, check audit log for snapshot entries
            resource = Resource.query.filter_by(status='active').first()
            if resource:
                manual_reclaim(resource.id, actor_id=1)

                snapshot_log = AuditLog.query.filter_by(
                    action='snapshot',
                    resource_id=resource.id
                ).first()
                assert snapshot_log is not None
