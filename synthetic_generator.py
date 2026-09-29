"""
CloudReclaim — Synthetic Dataset Generator
Generates realistic university cloud lab resources, telemetry metrics, owner tags, and semester schedules.
Supports direct database seeding as well as offline JSON/YAML dataset export.
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone, date
import yaml


DEFAULT_SEED = 42


class SyntheticDatasetGenerator:
    """
    Generator for synthetic university cloud laboratory environment data.
    Includes resources, telemetry time-series, owner tags, and academic calendar schedules.
    """

    def __init__(self, seed=DEFAULT_SEED, days=30):
        self.seed = seed
        self.days = days
        random.seed(self.seed)

    def generate_calendar_schedules(self):
        """Generate academic calendar schedules (semesters, breaks, exam weeks, maintenance)."""
        return [
            {
                "id": 1,
                "name": "Fall 2026 Semester",
                "period_type": "semester",
                "start_date": "2026-08-25",
                "end_date": "2026-12-15",
            },
            {
                "id": 2,
                "name": "Labor Day Break",
                "period_type": "break",
                "start_date": "2026-09-07",
                "end_date": "2026-09-07",
            },
            {
                "id": 3,
                "name": "Fall Break",
                "period_type": "break",
                "start_date": "2026-10-12",
                "end_date": "2026-10-16",
            },
            {
                "id": 4,
                "name": "Thanksgiving Break",
                "period_type": "break",
                "start_date": "2026-11-24",
                "end_date": "2026-11-28",
            },
            {
                "id": 5,
                "name": "Final Exams",
                "period_type": "exam_week",
                "start_date": "2026-12-08",
                "end_date": "2026-12-15",
            },
            {
                "id": 6,
                "name": "Winter Break",
                "period_type": "break",
                "start_date": "2026-12-16",
                "end_date": "2027-01-18",
            },
            {
                "id": 7,
                "name": "System Maintenance Window",
                "period_type": "maintenance",
                "start_date": "2026-12-20",
                "end_date": "2026-12-22",
            },
            {
                "id": 8,
                "name": "Spring 2026 Semester",
                "period_type": "semester",
                "start_date": "2026-01-15",
                "end_date": "2026-05-15",
            },
        ]

    def generate_users(self):
        """Generate user profiles (admins and instructors)."""
        return [
            {
                "id": 1,
                "username": "admin1",
                "full_name": "Sarah Chen",
                "email": "sarah.chen@univ.edu",
                "role": "admin",
                "department": "IT Operations",
            },
            {
                "id": 2,
                "username": "admin2",
                "full_name": "James Park",
                "email": "james.park@univ.edu",
                "role": "admin",
                "department": "IT Operations",
            },
            {
                "id": 3,
                "username": "prof_miller",
                "full_name": "Dr. Emily Miller",
                "email": "emily.miller@univ.edu",
                "role": "instructor",
                "department": "Computer Science",
            },
            {
                "id": 4,
                "username": "prof_kumar",
                "full_name": "Dr. Rajesh Kumar",
                "email": "rajesh.kumar@univ.edu",
                "role": "instructor",
                "department": "Computer Science",
            },
            {
                "id": 5,
                "username": "prof_santos",
                "full_name": "Dr. Maria Santos",
                "email": "maria.santos@univ.edu",
                "role": "instructor",
                "department": "Data Science",
            },
        ]

    def generate_courses(self):
        """Generate university lab courses with semester schedules."""
        return [
            {
                "id": 1,
                "code": "CS301",
                "name": "Machine Learning Lab",
                "semester": "Fall 2026",
                "instructor_id": 3,
                "start_date": "2026-08-25",
                "end_date": "2026-12-15",
                "is_active": True,
            },
            {
                "id": 2,
                "code": "CS201",
                "name": "Systems Programming Lab",
                "semester": "Fall 2026",
                "instructor_id": 4,
                "start_date": "2026-08-25",
                "end_date": "2026-12-15",
                "is_active": True,
            },
            {
                "id": 3,
                "code": "DS401",
                "name": "Deep Learning Workshop",
                "semester": "Fall 2026",
                "instructor_id": 5,
                "start_date": "2026-08-25",
                "end_date": "2026-12-15",
                "is_active": True,
            },
            {
                "id": 4,
                "code": "DS301",
                "name": "Data Engineering Lab",
                "semester": "Fall 2026",
                "instructor_id": 5,
                "start_date": "2026-08-25",
                "end_date": "2026-12-15",
                "is_active": True,
            },
            {
                "id": 5,
                "code": "CS101",
                "name": "Intro to Programming Lab",
                "semester": "Spring 2026",
                "instructor_id": 3,
                "start_date": "2026-01-15",
                "end_date": "2026-05-15",
                "is_active": False,
            },
            {
                "id": 6,
                "code": "CS401",
                "name": "Cloud Computing Lab",
                "semester": "Spring 2026",
                "instructor_id": None,  # Orphaned (instructor departed)
                "start_date": "2026-01-15",
                "end_date": "2026-05-15",
                "is_active": False,
            },
        ]

    def generate_resources_and_owner_tags(self, courses, users):
        """Generate resources with rich owner metadata tags and cost parameters."""
        resources = []
        user_map = {u["id"]: u for u in users}
        course_map = {c["id"]: c for c in courses}

        templates = [
            # CS301 (Machine Learning Lab)
            ("vm-cs301-node-{i}", "vm", 1, 3, 72.0, "ml-hw", "lab"),
            ("gpu-cs301-train-{i}", "gpu", 1, 3, 1080.0, "ml-training", "lab"),
            ("nb-cs301-jupyter-{i}", "notebook", 1, 3, 57.6, "ml-notebooks", "lab"),
            ("sto-cs301-data", "storage", 1, 3, 14.4, "ml-datasets", "lab"),

            # CS201 (Systems Programming)
            ("vm-cs201-node-{i}", "vm", 2, 4, 72.0, "sys-prog", "lab"),
            ("sto-cs201-builds", "storage", 2, 4, 14.4, "build-artifacts", "lab"),

            # DS401 (Deep Learning Workshop - Burst GPU workload)
            ("gpu-ds401-a100-{i}", "gpu", 3, 5, 1080.0, "dl-workshop", "research"),
            ("vm-ds401-preprocess-{i}", "vm", 3, 5, 72.0, "data-prep", "lab"),
            ("nb-ds401-colab-{i}", "notebook", 3, 5, 57.6, "dl-notebooks", "lab"),

            # DS301 (Data Engineering)
            ("vm-ds301-spark-{i}", "vm", 4, 5, 72.0, "data-eng", "lab"),
            ("sto-ds301-lake", "storage", 4, 5, 14.4, "data-lake", "lab"),

            # CS101 (Spring 2026 - EXPIRED course)
            ("vm-cs101-student-{i}", "vm", 5, 3, 72.0, "intro-prog", "lab"),
            ("nb-cs101-jupyter-{i}", "notebook", 5, 3, 57.6, "intro-notebooks", "lab"),
            ("sto-cs101-submissions", "storage", 5, 3, 14.4, "submissions", "lab"),

            # CS401 (Spring 2026 - ORPHANED course)
            ("vm-cs401-cluster-{i}", "vm", 6, None, 72.0, "cloud-lab", "production"),
            ("gpu-cs401-inference", "gpu", 6, None, 1080.0, "inference", "production"),
        ]

        res_id_counter = 1
        for tmpl in templates:
            name_pattern, rtype, course_id, owner_id, cost, project, env = tmpl
            course = course_map[course_id]

            if "{i}" in name_pattern:
                count = random.randint(2, 4)
                names = [name_pattern.format(i=str(j).zfill(2)) for j in range(1, count + 1)]
            else:
                names = [name_pattern]

            for rname in names:
                owner = user_map.get(owner_id) if owner_id else None
                owner_email = owner["email"] if owner else "unassigned@univ.edu"
                department = owner["department"] if owner else "Unassigned"

                owner_tags = {
                    "env": env,
                    "project": project,
                    "course_code": course["code"],
                    "owner_email": owner_email,
                    "department": department,
                    "cost_center": f"CC-{course['code']}",
                    "managed_by": "CloudReclaim-Autoscaler",
                }

                res_obj = {
                    "id": res_id_counter,
                    "resource_id": rname,
                    "resource_type": rtype,
                    "course_id": course_id,
                    "owner_id": owner_id,
                    "owner_email": owner_email,
                    "status": "active",
                    "monthly_cost": cost,
                    "owner_tags": owner_tags,
                    "created_at": f"{course['start_date']}T00:00:00Z",
                    "ttl_expires_at": "2026-12-29T00:00:00Z" if course["is_active"] else "2026-05-29T00:00:00Z",
                }
                resources.append(res_obj)
                res_id_counter += 1

        return resources

    def generate_telemetry_metrics(self, resources, courses):
        """Generate multi-signal telemetry metrics (CPU, Memory, Network, GPU, Disk I/O)."""
        metrics = []
        course_map = {c["id"]: c for c in courses}
        base_time = datetime(2026, 9, 29, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=self.days)

        metric_id_counter = 1
        for resource in resources:
            course = course_map[resource["course_id"]]
            is_expired = not course["is_active"]
            is_orphaned = resource["owner_id"] is None
            is_gpu = resource["resource_type"] == "gpu"
            is_burst = "ds401" in resource["resource_id"] and is_gpu

            for day_offset in range(self.days):
                day_time = base_time + timedelta(days=day_offset)

                for hour_offset in range(0, 24, 6):
                    metric_ts = day_time + timedelta(hours=hour_offset)

                    if is_orphaned:
                        cpu = round(random.uniform(0.1, 2.0), 2)
                        mem = round(random.uniform(1.0, 5.0), 2)
                        net = random.randint(0, 500)
                        gpu = round(random.uniform(0.0, 1.0), 2) if is_gpu else None
                        disk = random.randint(0, 200)

                    elif is_expired:
                        cpu = round(random.uniform(0.5, 4.0), 2)
                        mem = round(random.uniform(2.0, 8.0), 2)
                        net = random.randint(100, 800)
                        gpu = round(random.uniform(0.0, 1.0), 2) if is_gpu else None
                        disk = random.randint(50, 500)

                    elif is_burst:
                        if day_offset % 3 == 0 and hour_offset == 12:
                            cpu = round(random.uniform(65.0, 95.0), 2)
                            mem = round(random.uniform(70.0, 90.0), 2)
                            net = random.randint(500000, 2000000)
                            gpu = round(random.uniform(80.0, 99.0), 2)
                            disk = random.randint(100000, 500000)
                        else:
                            cpu = round(random.uniform(1.0, 5.0), 2)
                            mem = round(random.uniform(5.0, 15.0), 2)
                            net = random.randint(500, 3000)
                            gpu = round(random.uniform(0.5, 3.0), 2)
                            disk = random.randint(200, 2000)

                    else:
                        weekday = metric_ts.weekday()
                        is_weekday = weekday < 5
                        base_cpu = random.uniform(30.0, 75.0) if is_weekday else random.uniform(5.0, 20.0)
                        base_mem = random.uniform(40.0, 80.0) if is_weekday else random.uniform(10.0, 30.0)

                        cpu = round(base_cpu, 2)
                        mem = round(base_mem, 2)
                        net = random.randint(50000, 500000) if is_weekday else random.randint(1000, 10000)
                        gpu = round(random.uniform(20.0, 80.0), 2) if is_gpu and is_weekday else (
                            round(random.uniform(1.0, 10.0), 2) if is_gpu else None
                        )
                        disk = random.randint(10000, 100000) if is_weekday else random.randint(500, 5000)

                    metric_entry = {
                        "id": metric_id_counter,
                        "resource_id": resource["id"],
                        "resource_name": resource["resource_id"],
                        "timestamp": metric_ts.isoformat(),
                        "cpu_percent": cpu,
                        "memory_percent": mem,
                        "network_bytes": net,
                        "gpu_percent": gpu,
                        "disk_io_bytes": disk,
                    }
                    metrics.append(metric_entry)
                    metric_id_counter += 1

        return metrics

    def generate_dataset_dict(self):
        """Generate the complete synthetic dataset structure as a dictionary."""
        random.seed(self.seed)
        calendar = self.generate_calendar_schedules()
        users = self.generate_users()
        courses = self.generate_courses()
        resources = self.generate_resources_and_owner_tags(courses, users)
        telemetry = self.generate_telemetry_metrics(resources, courses)

        return {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "seed": self.seed,
                "telemetry_days": self.days,
                "total_users": len(users),
                "total_courses": len(courses),
                "total_resources": len(resources),
                "total_telemetry_records": len(telemetry),
                "total_calendar_periods": len(calendar),
            },
            "calendar_schedules": calendar,
            "users": users,
            "courses": courses,
            "resources": resources,
            "telemetry": telemetry,
        }

    def export_to_json(self, filepath):
        """Export synthetic dataset to a formatted JSON file."""
        dataset = self.generate_dataset_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)
        return dataset

    def export_to_yaml(self, filepath):
        """Export synthetic dataset to a formatted YAML file."""
        dataset = self.generate_dataset_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(dataset, f, default_flow_style=False)
        return dataset


def main():
    parser = argparse.ArgumentParser(description="CloudReclaim Synthetic Dataset Generator CLI")
    parser.add_argument("--export-json", type=str, help="Export dataset to JSON file path")
    parser.add_argument("--export-yaml", type=str, help="Export dataset to YAML file path")
    parser.add_argument("--days", type=int, default=30, help="Days of telemetry time-series to generate")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for deterministic generation")

    args = parser.parse_args()

    generator = SyntheticDatasetGenerator(seed=args.seed, days=args.days)
    dataset = generator.generate_dataset_dict()

    print(f"[Synthetic Generator] Generated synthetic dataset:")
    print(f"  - Users: {dataset['metadata']['total_users']}")
    print(f"  - Courses: {dataset['metadata']['total_courses']}")
    print(f"  - Resources: {dataset['metadata']['total_resources']}")
    print(f"  - Telemetry Records: {dataset['metadata']['total_telemetry_records']}")
    print(f"  - Calendar Schedules: {dataset['metadata']['total_calendar_periods']}")

    if args.export_json:
        generator.export_to_json(args.export_json)
        print(f"  - Exported JSON to: {args.export_json}")

    if args.export_yaml:
        generator.export_to_yaml(args.export_yaml)
        print(f"  - Exported YAML to: {args.export_yaml}")


if __name__ == "__main__":
    main()
