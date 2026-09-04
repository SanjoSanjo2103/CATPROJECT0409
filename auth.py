"""
CloudReclaim — Authentication & Authorization
Session-based auth with role decorators for Admin vs Instructor.
"""

from functools import wraps
from flask import Blueprint, session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash
from database import db
from models import User

auth_bp = Blueprint('auth', __name__)


# ─── Decorators ─────────────────────────────────────────────────────

def login_required(f):
    """Ensure user is logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(role):
    """Ensure user has the specified role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('user_role') != role:
                flash(f'Access denied. {role.title()} privileges required.', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_current_user():
    """Get the current logged-in user object."""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None


# ─── Routes ─────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.full_name
            session['username'] = user.username

            # Audit log the login
            from models import AuditLog
            import json
            log = AuditLog(
                actor_id=user.id,
                action='login',
                details=json.dumps({'ip': request.remote_addr})
            )
            db.session.add(log)
            db.session.commit()

            flash(f'Welcome, {user.full_name}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password.', 'error')

    from flask import render_template
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
