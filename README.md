# CloudReclaim — University Cloud Lab Resource Reclamation System

An ownership-aware idle-resource reclamation workflow with safe approval and expiry rules, designed for university cloud laboratories.

## Problem

Universities running cloud labs across courses and semesters face a critical operational failure: **idle resources continue generating cost because ownership is unclear.** Resources provisioned for courses are left running after semesters end, during breaks, or when instructors leave — with nobody responsible for stopping them.

## Solution

CloudReclaim augments existing workflows (not replaces them) by adding:

1. **Ownership-aware scanning** — Every resource is linked to an owner and course
2. **Multi-signal idle detection** — CPU + Memory + Network + GPU (not just CPU)
3. **Calendar awareness** — Integrates with academic calendar (semesters, breaks, exams)
4. **Safe approval workflow** — Grace periods, instructor notifications, extension limits
5. **Configurable rules** — All thresholds editable via Admin UI, not hard-coded

## Architecture

| Component | Technology |
|---|---|
| Backend | Python 3.11+ / Flask |
| Database | SQLite (zero-config) |
| Frontend | HTML + CSS + Vanilla JS |
| Scheduler | APScheduler (in-process) |
| Charts | Chart.js (CDN) |

Runs on modest hardware or a free-tier cloud environment.

## Quick Start

```bash
# 1. Clone and setup
cd coe
pip install -r requirements.txt

# 2. Run the server (auto-seeds synthetic data)
python app.py

# 3. Open browser
# http://127.0.0.1:5000
```

## Demo Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin1` | `password123` |
| Admin | `admin2` | `password123` |
| Instructor | `prof_miller` | `password123` |
| Instructor | `prof_kumar` | `password123` |
| Instructor | `prof_santos` | `password123` |

## Roles

- **Admin** — Full control: configure rules, trigger scans, reclaim resources, view audit log
- **Instructor** — Course-scoped: view own resources, approve/reject/extend reclamation requests

## Key Features

### Dashboard
- KPI cards (total resources, idle count, orphaned, monthly cost, savings)
- Status breakdown chart (donut)
- Cost by resource type (bar chart)
- Recent activity feed

### Resource Inventory
- Filterable by status, type, course
- Detail view with 30-day utilization charts
- Reclamation history per resource

### Approval Workflow
- Pending reclamation queue per instructor
- Approve / Reject / Extend actions
- Extension limits (configurable, default: 2 max)

### Admin Configuration
- All rules editable via form UI
- Changes are audit-logged
- Trigger manual scans and grace period processing

### Evaluation Reports
- Baseline vs. Prototype comparison charts
- False positive / negative rates
- Cost impact analysis
- Design rationale documentation

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test files
python -m pytest tests/test_scanner.py -v
python -m pytest tests/test_edge_cases.py -v
```

## Running the Experiment

```bash
python experiment/run_experiment.py
# Results saved to experiment/results.json
```

## Synthetic Dataset

30 days of realistic university data:
- 5 users (2 admins, 3 instructors)
- 6 courses (4 active Fall 2026, 2 expired Spring 2026)
- ~40 resources (VMs, GPUs, storage, notebooks)
- Utilization patterns: active, idle, burst, orphaned
- Academic calendar with breaks and exam periods

## Edge Cases Tested

1. **Orphaned Owner** — Faculty leaves, resources have no owner
2. **Burst Workloads** — GPU training every 3 days (low average, high peaks)
3. **Grace During Break** — Deadline expires during Thanksgiving break
4. **Max Extensions** — Instructor exhausts all allowed extensions
5. **Race Condition** — Resource becomes active during reclamation process

## Project Structure

```
├── app.py                 # Flask entry point
├── config.py              # Configurable rules
├── models.py              # Database models (7 tables)
├── scanner.py             # Multi-signal idle detection
├── baseline.py            # CPU-only baseline for comparison
├── reclaimer.py           # Reclamation workflow engine
├── seed_data.py           # Synthetic data generator
├── routes/                # Flask blueprints (6 modules)
├── templates/             # HTML templates (9 pages)
├── static/css/            # Dark theme with glassmorphism
├── tests/                 # pytest tests (5 test files)
├── experiment/            # Experiment runner + results
└── docs/                  # Problem analysis, design rationale
```

## License

Academic use — built as a course project prototype.
