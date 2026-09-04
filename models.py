"""
CloudReclaim — SQLAlchemy Models
7 tables: users, courses, resources, utilization_metrics,
reclamation_requests, audit_log, environment_calendar
"""

from datetime import datetime, timezone
from database import db
import json


# ─── Users ──────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='instructor')  # 'admin' or 'instructor'
    department = db.Column(db.String(100), nullable=True)

    # Relationships
    courses = db.relationship('Course', backref='instructor', lazy=True)
    owned_resources = db.relationship('Resource', backref='owner', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'department': self.department,
        }


# ─── Courses ────────────────────────────────────────────────────────
class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Relationships
    resources = db.relationship('Resource', backref='course', lazy=True)

    @property
    def is_active(self):
        today = datetime.now(timezone.utc).date()
        return self.start_date <= today <= self.end_date

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'semester': self.semester,
            'instructor_id': self.instructor_id,
            'instructor_name': self.instructor.full_name if self.instructor else None,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'is_active': self.is_active,
        }


# ─── Resources ──────────────────────────────────────────────────────
class Resource(db.Model):
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.String(100), unique=True, nullable=False)
    resource_type = db.Column(db.String(30), nullable=False)  # vm, gpu, storage, notebook
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='active')
    # Statuses: active, idle, orphaned, pending_reclaim, reclaimed, extended
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ttl_expires_at = db.Column(db.DateTime, nullable=True)
    monthly_cost = db.Column(db.Float, default=0.0)
    tags = db.Column(db.Text, default='{}')  # JSON string

    # Relationships
    metrics = db.relationship('UtilizationMetric', backref='resource',
                              lazy=True, order_by='UtilizationMetric.timestamp.desc()')
    reclamation_requests = db.relationship('ReclamationRequest', backref='resource', lazy=True)

    def get_tags(self):
        try:
            return json.loads(self.tags) if self.tags else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_tags(self, tag_dict):
        self.tags = json.dumps(tag_dict)

    def to_dict(self):
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'course_id': self.course_id,
            'course_code': self.course.code if self.course else None,
            'course_name': self.course.name if self.course else None,
            'owner_id': self.owner_id,
            'owner_name': self.owner.full_name if self.owner else 'Unassigned',
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ttl_expires_at': self.ttl_expires_at.isoformat() if self.ttl_expires_at else None,
            'monthly_cost': self.monthly_cost,
            'tags': self.get_tags(),
        }


# ─── Utilization Metrics ────────────────────────────────────────────
class UtilizationMetric(db.Model):
    __tablename__ = 'utilization_metrics'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    cpu_percent = db.Column(db.Float, default=0.0)
    memory_percent = db.Column(db.Float, default=0.0)
    network_bytes = db.Column(db.Integer, default=0)
    gpu_percent = db.Column(db.Float, nullable=True)
    disk_io_bytes = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'network_bytes': self.network_bytes,
            'gpu_percent': self.gpu_percent,
            'disk_io_bytes': self.disk_io_bytes,
        }


# ─── Reclamation Requests ───────────────────────────────────────────
class ReclamationRequest(db.Model):
    __tablename__ = 'reclamation_requests'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    reason = db.Column(db.String(50), nullable=False)
    # Reasons: idle_threshold, semester_expired, orphaned, manual
    status = db.Column(db.String(30), nullable=False, default='pending')
    # Statuses: pending, approved, rejected, expired, auto_reclaimed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    grace_deadline = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    response_note = db.Column(db.Text, nullable=True)
    actioned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship for the user who acted
    actioner = db.relationship('User', foreign_keys=[actioned_by])

    def to_dict(self):
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'resource_name': self.resource.resource_id if self.resource else None,
            'resource_type': self.resource.resource_type if self.resource else None,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'grace_deadline': self.grace_deadline.isoformat() if self.grace_deadline else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'response_note': self.response_note,
            'actioned_by': self.actioned_by,
            'actioner_name': self.actioner.full_name if self.actioner else 'System',
        }


# ─── Audit Log ──────────────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    # Actions: scan, flag_idle, flag_orphaned, notify, extend, approve_reclaim,
    #          reject_reclaim, auto_reclaim, config_change, login, snapshot
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=True)
    details = db.Column(db.Text, default='{}')  # JSON string

    # Relationships
    actor = db.relationship('User', foreign_keys=[actor_id])
    resource = db.relationship('Resource', foreign_keys=[resource_id])

    def get_details(self):
        try:
            return json.loads(self.details) if self.details else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'actor_id': self.actor_id,
            'actor_name': self.actor.full_name if self.actor else 'System',
            'action': self.action,
            'resource_id': self.resource_id,
            'resource_name': self.resource.resource_id if self.resource else None,
            'details': self.get_details(),
        }


# ─── Environment Calendar ───────────────────────────────────────────
class EnvironmentCalendar(db.Model):
    __tablename__ = 'environment_calendar'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    period_type = db.Column(db.String(30), nullable=False)
    # Types: semester, break, exam_week, maintenance
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'period_type': self.period_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        }
