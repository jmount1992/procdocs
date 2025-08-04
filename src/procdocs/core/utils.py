#!/usr/bin/env python3

import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any


# --- ProcDoc Constants --- #
# Fieldnames that are not allowed in schema or document structures
RESERVED_FIELDNAMES = {"metadata", "structure", "contents"}

# Current version of the ProcDocs format (schema & document layout)
CURRENT_PROCDOCS_FORMAT_VERSION = "0.0.1"

# Supported document extensions for schema files
SUPPORTED_SCHEMA_EXT = {".json"}


# --- Regular Expressions --- #
# Matches relaxed SemVer strings (e.g., 1, 1.2, 1.2.3, v1, v1.2.3)
VERSION_REGEX = re.compile(r"^v?\d+(\.\d+){0,2}$")

# Matches strict SemVer strings (e.g., 1.2.3 only)
STRICT_SEMVER_FORMAT = re.compile(r"^\d+\.\d+\.\d+$")

# Matches valid fieldnames: letters, numbers, underscores only
FIELDNAME_ALLOWED_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# --- Validation Functions --- #

def is_strict_semver(version: str) -> bool:
    """Return True if version string is strict SemVer (e.g., 1.2.3)."""
    return bool(STRICT_SEMVER_FORMAT.match(version))


def is_valid_version(version: str) -> bool:
    """Return True if version string matches relaxed SemVer (e.g., v1, 1.2)."""
    return bool(VERSION_REGEX.match(version))


def is_valid_fieldname_pattern(name: str) -> bool:
    """
    Return True if the fieldname is matches the FIELDNAME_ALLOWED_PATTERN
    """
    return bool(FIELDNAME_ALLOWED_PATTERN.match(name))


# --- Utility Functions --- #
def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries (override wins)."""
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


# --- File I/O Helper Functions --- #
def load_json_file(path: Path) -> Dict[str, Any]:
    """Load JSON file from path. Returns empty dict if missing."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_schema_metadata_from_render_template(template_path: Path) -> Optional[Dict]:
    with template_path.open("r") as f:
        for line in f:
            if line.startswith("{# PROCDOCS_METADATA"):
                content = line.strip().strip("{# PROCDOCS_METADATA").strip("#}")
                return dict(item.strip().split(": ") for item in content.split(","))
    return {}


def find_schema_path(schema_name: str, schema_paths: List[str]) -> Optional[Path]:
    """
    Find a schema JSON file given a schema name and configured search paths.

    Args:
        schema_name (str): Name of the schema (without extension) or direct path.
        schema_paths (List[str]): Paths to search for schema files.

    Returns:
        Path | None: Full path to the schema JSON file if found, else None.
    """
    # If input is a direct path and exists
    candidate = Path(schema_name)
    if candidate.exists() and candidate.suffix in SUPPORTED_SCHEMA_EXT:
        return candidate.resolve()

    # Search in configured schema paths (by name, no extension required)
    for path in schema_paths:
        base = Path(path)
        if not base.exists():
            continue
        # check explicit .json file
        candidate = base / f"{schema_name}.json"
        if candidate.exists():
            schema = load_json_file(candidate)
            if not schema or "metadata" not in schema or "schema_name" not in schema["metadata"]:
                continue
            return candidate.resolve()

    return None


def find_render_template_path(schema_name: str, schema_paths: List[str]) -> Optional[Path]:
    """
    Find a Jinja2 template file given a schema name and configured search paths.

    Args:
        schema_name (str): Name of the schema (without extension) or direct path.
        schema_paths (List[str]): Paths to search for schema files.

    Returns:
        Path | None: Full path to the schema JSON file if found, else None.
    """
    # If input is a direct path and exists
    candidate = Path(schema_name)
    if candidate.exists() and candidate.suffix in SUPPORTED_SCHEMA_EXT:
        return candidate.resolve()

    # Search in configured schema paths (by name, no extension required)
    for path in schema_paths:
        base = Path(path)
        if not base.exists():
            continue
        # check explicit .json file
        candidate = base / f"{schema_name}.json"
        if candidate.exists():
            template_metadata = extract_schema_metadata_from_render_template(candidate)
            if not template_metadata or "schema_name" not in template_metadata:
                continue
            return candidate.resolve()

    return None


# --- Run Validation on Module Load --- #
def validate_constants():
    """Ensure constants are valid at runtime (used at import)."""
    if not is_strict_semver(CURRENT_PROCDOCS_FORMAT_VERSION):
        raise ValueError(
            f"CURRENT_PROCDOCS_FORMAT_VERSION '{CURRENT_PROCDOCS_FORMAT_VERSION}' must use strict SemVer (e.g., 0.1.0)"
        )


validate_constants()
