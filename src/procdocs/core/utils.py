#!/usr/bin/env python3

import re
from pathlib import Path
from typing import Optional, List


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


def validate_constants():
    """Ensure constants are valid at runtime (used at import)."""
    if not is_strict_semver(CURRENT_PROCDOCS_FORMAT_VERSION):
        raise ValueError(
            f"CURRENT_PROCDOCS_FORMAT_VERSION '{CURRENT_PROCDOCS_FORMAT_VERSION}' must use strict SemVer (e.g., 0.1.0)"
        )


# --- File I/O Helper Functions --- #
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
            return candidate.resolve()

    return None


# --- Run Validation on Module Load --- #
validate_constants()
