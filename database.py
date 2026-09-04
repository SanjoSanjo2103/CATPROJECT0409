"""
CloudReclaim — Database Setup
SQLite via Flask-SQLAlchemy. Zero external dependencies.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the database with the Flask app and create all tables."""
    db.init_app(app)
    with app.app_context():
        # Import models so they are registered with SQLAlchemy
        import models  # noqa: F401
        db.create_all()
