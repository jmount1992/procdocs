#!/usr/bin/env python3
"""
Core constants used across ProcDocs.

- Versioning: current ProcDocs format version (schema/document layout compatibility).
- Reserved identifiers: field names disallowed in schemas/documents to avoid collisions.
- File handling: supported extensions and default text encoding.
- Regular expressions: compiled patterns used by validators and normalizers.
"""

import re
from typing import Final

# --- ProcDocs constants --- #

# Field names that are not allowed in schema or document structures
RESERVED_FIELDNAMES: Final[frozenset[str]] = frozenset({"metadata", "structure", "contents"})

# Current version of the ProcDocs format (schema & document layout compatibility)
PROCDOCS_FORMAT_VERSION: Final[str] = "0.0.1"

# Supported schema file extensions
SUPPORTED_SCHEMA_EXT: Final[frozenset[str]] = frozenset({".json"})

# Default text encoding
DEFAULT_TEXT_ENCODING: Final[str] = "utf-8"


# --- Regular Expressions --- #
# Matches relaxed SemVer strings (e.g., 1, 1.2, 1.2.3, v1, v1.2.3)
RELAXED_SEMVER_RE: re.Pattern[str] = re.compile(r"^v?\d+(\.\d+){0,2}$")

# Matches strict SemVer strings (e.g., 1.2.3 only)
STRICT_SEMVER_RE: re.Pattern[str] = re.compile(r"^\d+\.\d+\.\d+$")

# Matches valid field names: leading letter/underscore, then letters/numbers/underscores
FIELDNAME_ALLOWED_RE: re.Pattern[str] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Allowed schema (document type) names: lowercase letters, digits, dot, underscore, hyphen
SCHEMA_NAME_ALLOWED_RE: re.Pattern[str] = re.compile(r"^[a-z0-9._-]+$")


# --- Runtime guard --- #
def validate_constants():
    """
    Ensure constants are valid at runtime.
    """
    if not STRICT_SEMVER_RE.fullmatch(PROCDOCS_FORMAT_VERSION):
        raise RuntimeError(
            f"PROCDOCS_FORMAT_VERSION must be strict semver (x.y.z), got {PROCDOCS_FORMAT_VERSION!r}"
        )

validate_constants()