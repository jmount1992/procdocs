#!/usr/bin/env python3

import re

# Reserved fieldnames that cannot be redefined in schema or document
RESERVED_FIELDNAMES = {"metadata", "structure", "contents"}

# Version format: v1, v1.2, v1.2.3, or 1, 1.2, 1.2.3
VERSION_REGEX = re.compile(r"^v?\d+(\.\d+){0,2}$")

# Current format version of ProcDocs layout/schema
CURRENT_PROCDOCS_FORMAT_VERSION = "0.0.1"

STRICT_SEMVER_FORMAT = re.compile(r"^\d+\.\d+\.\d+$")


def is_strict_semver(version: str) -> bool:
    return bool(STRICT_SEMVER_FORMAT.match(version))


def is_valid_version(version: str) -> bool:
    """Return True if the version string matches SemVer-like pattern."""
    return bool(VERSION_REGEX.match(version))


if not is_strict_semver(CURRENT_PROCDOCS_FORMAT_VERSION):
    raise ValueError(f"The current ProcDocs format version '{CURRENT_PROCDOCS_FORMAT_VERSION}' is invalid")