"""
CloudReclaim — Policy Rule Schema Validator
Provides schema validation for policy rules using JSON/YAML definitions.
Ensures rule configuration options adhere to valid types, bounds, and required keys.
"""

import json
import os
import yaml
import jsonschema
from jsonschema import ValidationError, SchemaError

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "schemas",
    "policy_rules.schema.json"
)

def load_schema():
    """Load the canonical JSON Schema for policy rules."""
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_policy_rules(rules_dict):
    """
    Validate a rules dictionary against the policy schema.
    Returns (is_valid, list_of_error_messages).
    """
    schema = load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    
    for err in sorted(validator.iter_errors(rules_dict), key=lambda e: e.path):
        field_name = ".".join(str(p) for p in err.path) if err.path else "root"
        errors.append(f"Field '{field_name}': {err.message}")
        
    return len(errors) == 0, errors

def load_policy_rules_file(filepath):
    """
    Load and validate policy rules from a JSON or YAML file.
    Returns (rules_dict, errors).
    """
    if not os.path.exists(filepath):
        return None, [f"File not found: {filepath}"]
        
    ext = os.path.splitext(filepath)[1].lower()
    with open(filepath, 'r', encoding='utf-8') as f:
        if ext in ('.yaml', '.yml'):
            rules = yaml.safe_load(f)
        elif ext == '.json':
            rules = json.load(f)
        else:
            return None, [f"Unsupported file format: {ext}. Expected .json or .yaml"]
            
    is_valid, errors = validate_policy_rules(rules)
    if not is_valid:
        return None, errors
        
    return rules, []
