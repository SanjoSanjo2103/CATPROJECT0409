"""
CloudReclaim — Flask Application Entry Point
University Cloud Lab Idle-Resource Reclamation System

Usage:
    python app.py              # Start the server (auto-seeds data)
    python app.py --no-seed    # Start without re-seeding
"""

import sys
import os
from flask import Flask
from config import FlaskConfig
from database import db, init_db


def create_app(seed=True, testing=False):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(FlaskConfig)

    if testing:
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Initialize database
    db.init_app(app)

    with app.app_context():
        # Import models to register with SQLAlchemy
        import models  # noqa: F401
        db.create_all()

        # Seed synthetic data if requested
        if seed:
            from seed_data import seed_all
            result = seed_all()
            print(f"[APP] Database seeded: {result}")

    # Register blueprints
    from auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.resources import resources_bp
    from routes.approval import approval_bp
    from routes.admin import admin_bp
    from routes.reports import reports_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)

    # Initialize scheduler (skip during testing to avoid conflicts)
    if not testing:
        from scheduler_jobs import init_scheduler
        init_scheduler(app)

    return app


if __name__ == '__main__':
    seed = '--no-seed' not in sys.argv
    app = create_app(seed=seed)
    print("\n" + "=" * 60)
    print("  CloudReclaim — University Cloud Lab Resource Manager")
    print("=" * 60)
    print("  Server:  http://127.0.0.1:5000")
    print("  Admin:   admin1 / password123")
    print("  Faculty: prof_miller / password123")
    print("=" * 60 + "\n")
    app.run(debug=True, use_reloader=False, port=5000)
