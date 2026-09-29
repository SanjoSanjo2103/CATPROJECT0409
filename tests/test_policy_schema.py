"""
Tests for CloudReclaim Policy Rule Schema Definition & Validation
"""

import os
import pytest
from policy_validator import (
    validate_policy_rules,
    load_policy_rules_file,
    SCHEMA_PATH
)
from config import RECLAMATION_RULES, validate_rules, update_rule


class TestPolicySchemaValidation:

    def test_schema_file_exists(self):
        """Verify schema file exists at canonical path."""
        assert os.path.exists(SCHEMA_PATH)

    def test_default_config_passes_validation(self):
        """Verify default RECLAMATION_RULES pass schema validation."""
        is_valid, errors = validate_policy_rules(RECLAMATION_RULES)
        assert is_valid is True, f"Validation errors: {errors}"
        assert len(errors) == 0

    def test_load_default_json_config(self):
        """Verify loading default JSON config file."""
        json_path = os.path.join("config", "policy_rules_default.json")
        rules, errors = load_policy_rules_file(json_path)
        assert rules is not None
        assert len(errors) == 0
        assert rules["cpu_idle_threshold"] == 5.0

    def test_load_default_yaml_config(self):
        """Verify loading default YAML config file."""
        yaml_path = os.path.join("config", "policy_rules_default.yaml")
        rules, errors = load_policy_rules_file(yaml_path)
        assert rules is not None
        assert len(errors) == 0
        assert rules["idle_duration_days"] == 7

    def test_invalid_cpu_threshold(self):
        """Verify invalid CPU threshold (>100 or <0) fails validation."""
        bad_rules = dict(RECLAMATION_RULES)
        bad_rules["cpu_idle_threshold"] = 150.0  # Invalid > 100
        is_valid, errors = validate_policy_rules(bad_rules)
        assert is_valid is False
        assert any("cpu_idle_threshold" in err for err in errors)

    def test_negative_grace_period(self):
        """Verify negative grace period fails validation."""
        bad_rules = dict(RECLAMATION_RULES)
        bad_rules["grace_period_hours"] = -5  # Invalid < 1
        is_valid, errors = validate_policy_rules(bad_rules)
        assert is_valid is False
        assert any("grace_period_hours" in err for err in errors)

    def test_invalid_type_rejection(self):
        """Verify invalid parameter type fails validation."""
        bad_rules = dict(RECLAMATION_RULES)
        bad_rules["idle_duration_days"] = "seven_days"  # Should be integer
        is_valid, errors = validate_policy_rules(bad_rules)
        assert is_valid is False
        assert any("idle_duration_days" in err for err in errors)

    def test_config_update_rule_with_validation(self):
        """Verify update_rule respects schema validation."""
        # Valid update
        assert update_rule("cpu_idle_threshold", 7.5) is True
        assert RECLAMATION_RULES["cpu_idle_threshold"] == 7.5

        # Invalid update attempt
        assert update_rule("cpu_idle_threshold", 200.0) is False
        assert RECLAMATION_RULES["cpu_idle_threshold"] == 7.5  # Reverts/unchanged

        # Reset back
        update_rule("cpu_idle_threshold", 5.0)
