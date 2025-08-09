#!/usr/bin/env python3

import re

# --- ProcDoc Constants --- #
# Fieldnames that are not allowed in schema or document structures
RESERVED_FIELDNAMES = {"metadata", "structure", "contents"}

# Current version of the ProcDocs format (schema & document layout)
PROCDOCS_FORMAT_VERSION = "0.0.1"

# Supported document extensions for schema files
SUPPORTED_SCHEMA_EXT = {".json"}

# Default text encoding
DEFAULT_TEXT_ENCODING = "utf-8"


# --- Regular Expressions --- #
# Matches relaxed SemVer strings (e.g., 1, 1.2, 1.2.3, v1, v1.2.3)
VERSION_REGEX = re.compile(r"^v?\d+(\.\d+){0,2}$")

# Matches strict SemVer strings (e.g., 1.2.3 only)
STRICT_SEMVER_FORMAT = re.compile(r"^\d+\.\d+\.\d+$")

# Matches valid fieldnames: letters, numbers, underscores only
FIELDNAME_ALLOWED_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Allowed schema name fields
SCHEMA_NAME_ALLOWED_RE = r"^[a-z0-9._-]+$"
