"""
CloudReclaim — Synthetic Data Generator
Creates realistic university cloud lab data for 30 days.
Deterministic seed for reproducibility.

Generates:
  - 5 users (2 admins, 3 instructors)
  - 6 courses across 2 departments
  - ~40 resources (VMs, GPUs, storage, notebooks)
  - 30 days of utilization metrics with realistic patterns
  - Academic calendar (semester, breaks, exams)
"""

import random
import json
from datetime import datetime, timedelta, timezone, date
from werkzeug.security import generate_password_hash
from database import db
from models import (
    User, Course, Resource, UtilizationMetric,
    EnvironmentCalendar, AuditLog
)

SEED = 42


def seed_all():
    """Generate all synthetic data. Idempotent — clears existing data first."""
    random.seed(SEED)

    # Clear existing data (order matters for FK constraints)
    AuditLog.query.delete()
    UtilizationMetric.query.delete()
    from models import ReclamationRequest
    ReclamationRequest.query.delete()
    Resource.query.delete()
    Course.query.delete()
    EnvironmentCalendar.query.delete()
    User.query.delete()
    db.session.commit()

    users = _seed_users()
    calendar = _seed_calendar()
    courses = _seed_courses(users)
    resources = _seed_resources(courses, users)
    _seed_utilization(resources, calendar)
    _seed_audit_log(users)

    db.session.commit()
    print(f"[SEED] Created {len(users)} users, {len(courses)} courses, "
          f"{len(resources)} resources, {len(calendar)} calendar periods")
    return {
        'users': len(users),
        'courses': len(courses),
        'resources': len(resources),
        'calendar': len(calendar),
    }


def _seed_users():
    """Create 5 users: 2 admins + 3 instructors."""
    password = generate_password_hash('password123')

    users_data = [
        # Admins
        ('admin1', password, 'Sarah Chen', 'sarah.chen@univ.edu', 'admin', 'IT Operations'),
        ('admin2', password, 'James Park', 'james.park@univ.edu', 'admin', 'IT Operations'),
        # Instructors
        ('prof_miller', password, 'Dr. Emily Miller', 'emily.miller@univ.edu', 'instructor', 'Computer Science'),
        ('prof_kumar', password, 'Dr. Rajesh Kumar', 'rajesh.kumar@univ.edu', 'instructor', 'Computer Science'),
        ('prof_santos', password, 'Dr. Maria Santos', 'maria.santos@univ.edu', 'instructor', 'Data Science'),
    ]

    users = []
    for udata in users_data:
        user = User(
            username=udata[0],
            password_hash=udata[1],
            full_name=udata[2],
            email=udata[3],
            role=udata[4],
            department=udata[5],
        )
        db.session.add(user)
        users.append(user)

    db.session.flush()  # Get IDs assigned
    return users


def _seed_calendar():
    """Create academic calendar for Fall 2026."""
    periods = [
        ('Fall 2026 Semester', 'semester', date(2026, 8, 25), date(2026, 12, 15)),
        ('Labor Day Break', 'break', date(2026, 9, 7), date(2026, 9, 7)),
        ('Fall Break', 'break', date(2026, 10, 12), date(2026, 10, 16)),
        ('Thanksgiving Break', 'break', date(2026, 11, 24), date(2026, 11, 28)),
        ('Final Exams', 'exam_week', date(2026, 12, 8), date(2026, 12, 15)),
        ('Winter Break', 'break', date(2026, 12, 16), date(2027, 1, 18)),
        ('System Maintenance Window', 'maintenance', date(2026, 12, 20), date(2026, 12, 22)),
        # Spring 2026 (already ended — tests post-semester reclamation)
        ('Spring 2026 Semester', 'semester', date(2026, 1, 15), date(2026, 5, 15)),
    ]

    calendar = []
    for pdata in periods:
        entry = EnvironmentCalendar(
            name=pdata[0],
            period_type=pdata[1],
            start_date=pdata[2],
            end_date=pdata[3],
        )
        db.session.add(entry)
        calendar.append(entry)

    db.session.flush()
    return calendar


def _seed_courses(users):
    """Create 6 courses across CS and Data Science."""
    # Users: admin1(0), admin2(1), prof_miller(2), prof_kumar(3), prof_santos(4)
    courses_data = [
        # Active courses (Fall 2026)
        ('CS301', 'Machine Learning Lab', 'Fall 2026', users[2].id, date(2026, 8, 25), date(2026, 12, 15)),
        ('CS201', 'Systems Programming Lab', 'Fall 2026', users[3].id, date(2026, 8, 25), date(2026, 12, 15)),
        ('DS401', 'Deep Learning Workshop', 'Fall 2026', users[4].id, date(2026, 8, 25), date(2026, 12, 15)),
        ('DS301', 'Data Engineering Lab', 'Fall 2026', users[4].id, date(2026, 8, 25), date(2026, 12, 15)),
        # Expired course (Spring 2026 — already ended)
        ('CS101', 'Intro to Programming Lab', 'Spring 2026', users[2].id, date(2026, 1, 15), date(2026, 5, 15)),
        # Expired course — instructor left (orphaned)
        ('CS401', 'Cloud Computing Lab', 'Spring 2026', None, date(2026, 1, 15), date(2026, 5, 15)),
    ]

    courses = []
    for cdata in courses_data:
        course = Course(
            code=cdata[0],
            name=cdata[1],
            semester=cdata[2],
            instructor_id=cdata[3],
            start_date=cdata[4],
            end_date=cdata[5],
        )
        db.session.add(course)
        courses.append(course)

    db.session.flush()
    return courses


def _seed_resources(courses, users):
    """Create ~40 resources across courses with various states."""
    resources = []
    resource_templates = [
        # ── CS301 Machine Learning Lab (active, mixed utilization) ──
        ('vm-cs301-node-{i}', 'vm', 0, 2, 72.0, {'env': 'lab', 'project': 'ml-hw'}),
        ('gpu-cs301-train-{i}', 'gpu', 0, 2, 1080.0, {'env': 'lab', 'project': 'ml-training'}),
        ('nb-cs301-jupyter-{i}', 'notebook', 0, 2, 57.6, {'env': 'lab', 'project': 'ml-notebooks'}),
        ('sto-cs301-data', 'storage', 0, 2, 14.4, {'env': 'lab', 'project': 'ml-datasets'}),

        # ── CS201 Systems Programming Lab (active, high utilization) ──
        ('vm-cs201-node-{i}', 'vm', 1, 3, 72.0, {'env': 'lab', 'project': 'sys-prog'}),
        ('sto-cs201-builds', 'storage', 1, 3, 14.4, {'env': 'lab', 'project': 'build-artifacts'}),

        # ── DS401 Deep Learning Workshop (active, burst GPU usage) ──
        ('gpu-ds401-a100-{i}', 'gpu', 2, 4, 1080.0, {'env': 'lab', 'project': 'dl-workshop'}),
        ('vm-ds401-preprocess-{i}', 'vm', 2, 4, 72.0, {'env': 'lab', 'project': 'data-prep'}),
        ('nb-ds401-colab-{i}', 'notebook', 2, 4, 57.6, {'env': 'lab', 'project': 'dl-notebooks'}),

        # ── DS301 Data Engineering Lab (active, moderate) ──
        ('vm-ds301-spark-{i}', 'vm', 3, 4, 72.0, {'env': 'lab', 'project': 'data-eng'}),
        ('sto-ds301-lake', 'storage', 3, 4, 14.4, {'env': 'lab', 'project': 'data-lake'}),

        # ── CS101 Intro Programming (EXPIRED — still running!) ──
        ('vm-cs101-student-{i}', 'vm', 4, 2, 72.0, {'env': 'lab', 'project': 'intro-prog'}),
        ('nb-cs101-jupyter-{i}', 'notebook', 4, 2, 57.6, {'env': 'lab', 'project': 'intro-notebooks'}),
        ('sto-cs101-submissions', 'storage', 4, 2, 14.4, {'env': 'lab', 'project': 'submissions'}),

        # ── CS401 Cloud Computing (ORPHANED — no instructor) ──
        ('vm-cs401-cluster-{i}', 'vm', 5, None, 72.0, {'env': 'lab', 'project': 'cloud-lab'}),
        ('gpu-cs401-inference', 'gpu', 5, None, 1080.0, {'env': 'lab', 'project': 'inference'}),
    ]

    now = datetime.now(timezone.utc)

    for tmpl in resource_templates:
        name_pattern, rtype, course_idx, owner_idx, cost, tags = tmpl

        # Determine how many instances (if pattern has {i})
        if '{i}' in name_pattern:
            count = random.randint(2, 4)
            names = [name_pattern.format(i=str(j).zfill(2)) for j in range(1, count + 1)]
        else:
            names = [name_pattern]

        for rname in names:
            owner_id = users[owner_idx].id if owner_idx is not None else None
            course = courses[course_idx]

            # Set TTL based on course end date
            ttl = datetime.combine(course.end_date + timedelta(days=14),
                                   datetime.min.time()).replace(tzinfo=timezone.utc)

            resource = Resource(
                resource_id=rname,
                resource_type=rtype,
                course_id=course.id,
                owner_id=owner_id,
                status='active',
                created_at=datetime.combine(course.start_date,
                                            datetime.min.time()).replace(tzinfo=timezone.utc),
                ttl_expires_at=ttl,
                monthly_cost=cost,
                tags=json.dumps(tags),
            )
            db.session.add(resource)
            resources.append(resource)

    db.session.flush()
    return resources


def _seed_utilization(resources, calendar):
    """Generate 30 days of utilization data with realistic patterns."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    # Classify resources by their expected pattern
    for resource in resources:
        course = resource.course
        is_expired = course and not course.is_active
        is_orphaned = resource.owner_id is None
        is_gpu = resource.resource_type == 'gpu'
        is_burst = 'ds401' in resource.resource_id and is_gpu  # burst pattern for DL GPUs

        for day_offset in range(30):
            ts = start + timedelta(days=day_offset)

            # Generate 4 data points per day (every 6 hours)
            for hour_offset in range(0, 24, 6):
                metric_ts = ts + timedelta(hours=hour_offset)

                if is_orphaned:
                    # Orphaned: near-zero utilization
                    cpu = random.uniform(0.1, 2.0)
                    mem = random.uniform(1.0, 5.0)
                    net = random.randint(0, 500)
                    gpu_pct = random.uniform(0, 1.0) if is_gpu else None
                    disk = random.randint(0, 200)

                elif is_expired:
                    # Expired course: very low utilization (maybe a cron job)
                    cpu = random.uniform(0.5, 4.0)
                    mem = random.uniform(2.0, 8.0)
                    net = random.randint(100, 800)
                    gpu_pct = None
                    disk = random.randint(50, 500)

                elif is_burst:
                    # Burst workload: every 3 days, spikes to high usage for ~6 hours
                    if day_offset % 3 == 0 and hour_offset == 12:
                        cpu = random.uniform(60.0, 95.0)
                        mem = random.uniform(70.0, 90.0)
                        net = random.randint(500000, 2000000)
                        gpu_pct = random.uniform(80.0, 99.0)
                        disk = random.randint(100000, 500000)
                    else:
                        cpu = random.uniform(1.0, 5.0)
                        mem = random.uniform(5.0, 15.0)
                        net = random.randint(500, 3000)
                        gpu_pct = random.uniform(0.5, 3.0)
                        disk = random.randint(200, 2000)

                else:
                    # Active course: normal lab usage (higher during weekdays)
                    weekday = metric_ts.weekday()
                    is_weekday = weekday < 5
                    base_cpu = random.uniform(30.0, 75.0) if is_weekday else random.uniform(5.0, 20.0)
                    base_mem = random.uniform(40.0, 80.0) if is_weekday else random.uniform(10.0, 30.0)

                    cpu = base_cpu
                    mem = base_mem
                    net = random.randint(50000, 500000) if is_weekday else random.randint(1000, 10000)
                    gpu_pct = random.uniform(20.0, 80.0) if is_gpu and is_weekday else (
                        random.uniform(1.0, 10.0) if is_gpu else None)
                    disk = random.randint(10000, 100000) if is_weekday else random.randint(500, 5000)

                metric = UtilizationMetric(
                    resource_id=resource.id,
                    timestamp=metric_ts,
                    cpu_percent=round(cpu, 2),
                    memory_percent=round(mem, 2),
                    network_bytes=net,
                    gpu_percent=round(gpu_pct, 2) if gpu_pct is not None else None,
                    disk_io_bytes=disk,
                )
                db.session.add(metric)


def _seed_audit_log(users):
    """Create a few initial audit log entries."""
    now = datetime.now(timezone.utc)
    entries = [
        (users[0].id, 'scan', None, {'type': 'scheduled', 'resources_scanned': 40}),
        (users[0].id, 'config_change', None, {'key': 'cpu_idle_threshold', 'old': 10.0, 'new': 5.0}),
    ]

    for actor_id, action, res_id, details in entries:
        log = AuditLog(
            timestamp=now - timedelta(hours=random.randint(1, 48)),
            actor_id=actor_id,
            action=action,
            resource_id=res_id,
            details=json.dumps(details),
        )
        db.session.add(log)
