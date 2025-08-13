#!/usr/bin/env python3
"""
Purpose:
    Provides common utility functions such as validation, semantic
    version handling, dictionary merge, and file I/O utilities for ProcDocs.
"""

import json
from pathlib import Path
from typing import Dict, Any

from procdocs.core.constants import (
    STRICT_SEMVER_RE, RELAXED_SEMVER_RE,
    FIELDNAME_ALLOWED_RE, DEFAULT_TEXT_ENCODING
)


# --- Validation Helpers --- #

def is_strict_semver(version: str) -> bool:
    """Return True if the version string is strict SemVer (e.g., 'x.y.z')."""
    return bool(STRICT_SEMVER_RE.fullmatch(version))


def is_valid_version(version: str) -> bool:
    """Return True if the version string matches relaxed SemVer (e.g., 'v1', '1.2')."""
    return bool(RELAXED_SEMVER_RE.fullmatch(version))


def is_valid_fieldname_pattern(name: str) -> bool:
    """Return True if the field name fully matches the allowed pattern."""
    return bool(FIELDNAME_ALLOWED_RE.fullmatch(name))


# --- Semantic Version Utilities --- #

def get_semver_tuple(s: str) -> tuple[int, int, int]:
    """
    Parse a strict semantic version string 'x.y.z' into a (major, minor, patch) tuple.

    Raises:
        ValueError: If the string is not in strict semver format.
    """
    if not is_strict_semver(s):
        raise ValueError(f"Invalid semver string: {s!r}")
    return tuple(int(p) for p in s.split("."))


def compare_semver(a: str, b: str) -> int:
    """Return -1 if a<b, 0 if a==b, 1 if a>b (strict semver x.y.z)."""
    ta, tb = get_semver_tuple(a), get_semver_tuple(b)
    return (ta > tb) - (ta < tb)


def is_semver_equal(a: str, b: str) -> bool:
    """Return true if the a == b (strict semver compare)."""
    return compare_semver(a, b) == 0


def is_semver_at_least(version: str, threshold: str) -> bool:
    """Return True if version >= threshold (strict semver compare)."""
    return compare_semver(version, threshold) >= 0


def is_semver_after(version: str, threshold: str) -> bool:
    """Return True if version > threshold (strict semver compare)."""
    return compare_semver(version, threshold) > 0


def is_semver_before(version: str, threshold: str) -> bool:
    """Return True if version < threshold (strict semver compare)."""
    return compare_semver(version, threshold) < 0


# --- Generic Utilities --- #

def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries (values from 'override' take precedence).
    Non-dict values are overwritten; dict values are merged depth-first.
    """
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


# --- File I/O Helpers --- #

def load_json_file(path: Path) -> Dict[str, Any]:
    """
    Load a JSON file from 'path'. Returns an empty dict if the file is missing.

    Raises:
        ValueError: if the file exists but contains invalid JSON.
    """
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding=DEFAULT_TEXT_ENCODING) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in {str(path)!r}: {e.msg} (line {e.lineno}, col {e.colno})"
        ) from e
