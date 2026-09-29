"""
Tests for Synthetic Dataset Generator (resources, telemetry, owner tags, semester schedules)
"""

import os
import json
import pytest
import yaml
from synthetic_generator import SyntheticDatasetGenerator


class TestSyntheticDatasetGenerator:

    @pytest.fixture
    def generator(self):
        return SyntheticDatasetGenerator(seed=42, days=7)

    def test_generate_dataset_structure(self, generator):
        """Verify the high-level keys in generated synthetic dataset."""
        dataset = generator.generate_dataset_dict()

        assert "metadata" in dataset
        assert "calendar_schedules" in dataset
        assert "users" in dataset
        assert "courses" in dataset
        assert "resources" in dataset
        assert "telemetry" in dataset

        meta = dataset["metadata"]
        assert meta["seed"] == 42
        assert meta["telemetry_days"] == 7
        assert meta["total_users"] == 5
        assert meta["total_courses"] == 6

    def test_semester_schedules_content(self, generator):
        """Verify semester schedules include Fall 2026, Spring 2026, breaks, and exams."""
        schedules = generator.generate_calendar_schedules()
        period_types = {s["period_type"] for s in schedules}
        names = [s["name"] for s in schedules]

        assert "semester" in period_types
        assert "break" in period_types
        assert "exam_week" in period_types
        assert "maintenance" in period_types
        assert "Fall 2026 Semester" in names
        assert "Thanksgiving Break" in names

    def test_resources_and_owner_tags(self, generator):
        """Verify resources contain structured owner metadata tags."""
        dataset = generator.generate_dataset_dict()
        resources = dataset["resources"]

        assert len(resources) > 0
        first_res = resources[0]

        assert "resource_id" in first_res
        assert "resource_type" in first_res
        assert "monthly_cost" in first_res
        assert "owner_tags" in first_res

        tags = first_res["owner_tags"]
        assert "env" in tags
        assert "project" in tags
        assert "course_code" in tags
        assert "owner_email" in tags
        assert "department" in tags

    def test_telemetry_metrics_signals(self, generator):
        """Verify multi-signal telemetry includes CPU, memory, network, GPU, disk I/O."""
        dataset = generator.generate_dataset_dict()
        telemetry = dataset["telemetry"]

        # 7 days * 4 points/day * 36 resources = 1008 records
        assert len(telemetry) == 1008
        sample = telemetry[0]

        assert "cpu_percent" in sample
        assert "memory_percent" in sample
        assert "network_bytes" in sample
        assert "gpu_percent" in sample
        assert "disk_io_bytes" in sample

    def test_json_and_yaml_export(self, generator, tmp_path):
        """Verify dataset export to JSON and YAML files."""
        json_file = tmp_path / "test_dataset.json"
        yaml_file = tmp_path / "test_dataset.yaml"

        generator.export_to_json(str(json_file))
        generator.export_to_yaml(str(yaml_file))

        assert os.path.exists(json_file)
        assert os.path.exists(yaml_file)

        with open(json_file, "r") as f:
            data_json = json.load(f)
            assert data_json["metadata"]["seed"] == 42

        with open(yaml_file, "r") as f:
            data_yaml = yaml.safe_load(f)
            assert data_yaml["metadata"]["seed"] == 42
