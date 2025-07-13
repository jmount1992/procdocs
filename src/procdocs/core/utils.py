#!/usr/bin/env python3

import re


# --- Reserved and Required Constants --- #

#: Fieldnames that are not allowed in schema or document structures
RESERVED_FIELDNAMES = {"metadata", "structure", "contents"}

#: Current version of the ProcDocs format (schema & document layout)
CURRENT_PROCDOCS_FORMAT_VERSION = "0.0.1"

# --- Regular Expressions --- #

#: Matches relaxed SemVer strings (e.g., 1, 1.2, 1.2.3, v1, v1.2.3)
VERSION_REGEX = re.compile(r"^v?\d+(\.\d+){0,2}$")

#: Matches strict SemVer strings (e.g., 1.2.3 only)
STRICT_SEMVER_FORMAT = re.compile(r"^\d+\.\d+\.\d+$")

#: Matches valid fieldnames: letters, numbers, underscores only
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


# --- Run validations on module load --- #
validate_constants()
