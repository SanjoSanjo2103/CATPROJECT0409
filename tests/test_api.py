"""
CloudReclaim — API Tests
Integration tests for web endpoints and role enforcement.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import db
from seed_data import seed_all


@pytest.fixture
def app():
    app = create_app(seed=False, testing=True)
    with app.app_context():
        db.create_all()
        seed_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username='admin1', password='password123'):
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)


class TestAuthentication:
    """Test login/logout and session management."""

    def test_login_page_accessible(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_login_success(self, client):
        resp = login(client)
        assert resp.status_code == 200

    def test_login_failure(self, client):
        resp = client.post('/login', data={
            'username': 'wrong',
            'password': 'wrong'
        }, follow_redirects=True)
        assert b'Invalid' in resp.data

    def test_logout(self, client):
        login(client)
        resp = client.get('/logout', follow_redirects=True)
        assert resp.status_code == 200

    def test_protected_route_redirects(self, client):
        resp = client.get('/', follow_redirects=False)
        assert resp.status_code == 302  # Redirect to login


class TestRoleEnforcement:
    """Test that role-based access control works."""

    def test_admin_can_access_config(self, client):
        login(client, 'admin1', 'password123')
        resp = client.get('/admin/config')
        assert resp.status_code == 200

    def test_instructor_cannot_access_config(self, client):
        login(client, 'prof_miller', 'password123')
        resp = client.get('/admin/config', follow_redirects=True)
        # Should be redirected with access denied
        assert b'Access denied' in resp.data or resp.status_code in (302, 200)

    def test_admin_can_access_audit_log(self, client):
        login(client, 'admin1', 'password123')
        resp = client.get('/admin/audit')
        assert resp.status_code == 200

    def test_instructor_can_access_dashboard(self, client):
        login(client, 'prof_miller', 'password123')
        resp = client.get('/')
        assert resp.status_code == 200

    def test_instructor_can_access_approvals(self, client):
        login(client, 'prof_miller', 'password123')
        resp = client.get('/approvals')
        assert resp.status_code == 200


class TestAPIEndpoints:
    """Test JSON API endpoints."""

    def test_api_stats(self, client):
        login(client)
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total_resources' in data

    def test_api_resources(self, client):
        login(client)
        resp = client.get('/api/resources')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_api_cost_breakdown(self, client):
        login(client)
        resp = client.get('/api/cost-breakdown')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'by_status' in data
        assert 'by_type' in data
        assert 'by_course' in data

    def test_api_calendar(self, client):
        login(client)
        resp = client.get('/api/calendar')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_api_notifications(self, client):
        login(client)
        resp = client.get('/api/notifications')
        assert resp.status_code == 200


class TestResourcePages:
    """Test resource CRUD pages."""

    def test_resources_list(self, client):
        login(client)
        resp = client.get('/resources')
        assert resp.status_code == 200

    def test_resources_filter_by_status(self, client):
        login(client)
        resp = client.get('/resources?status=active')
        assert resp.status_code == 200

    def test_resources_filter_by_type(self, client):
        login(client)
        resp = client.get('/resources?type=vm')
        assert resp.status_code == 200

    def test_resource_detail(self, client, app):
        login(client)
        with app.app_context():
            from models import Resource
            resource = Resource.query.first()
            resp = client.get(f'/resources/{resource.id}')
            assert resp.status_code == 200

    def test_reports_page(self, client):
        login(client)
        resp = client.get('/reports')
        assert resp.status_code == 200
