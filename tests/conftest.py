"""
CloudReclaim — conftest.py
Shared pytest fixtures for all tests.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import db as _db


@pytest.fixture(scope='session')
def app():
    """Create a test Flask application."""
    app = create_app(seed=True, testing=True)
    app.config['WTF_CSRF_ENABLED'] = False

    # Re-init with in-memory DB
    with app.app_context():
        _db.create_all()
        from seed_data import seed_all
        seed_all()

    yield app


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope='function')
def db_session(app):
    """Provide a transactional database session."""
    with app.app_context():
        yield _db


def login_as_admin(client):
    """Helper: log in as admin."""
    return client.post('/login', data={
        'username': 'admin1',
        'password': 'password123'
    }, follow_redirects=True)


def login_as_instructor(client):
    """Helper: log in as instructor."""
    return client.post('/login', data={
        'username': 'prof_miller',
        'password': 'password123'
    }, follow_redirects=True)
