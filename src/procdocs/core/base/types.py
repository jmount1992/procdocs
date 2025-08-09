#!/usr/bin/env python3

import re
from typing import Annotated, Optional
from pydantic import BeforeValidator

from procdocs.core.constants import SCHEMA_NAME_ALLOWED_RE


# --- Normalizers --- #

def _normalize_schema_like_name(v) -> str:
    """
    Normalize a schema-like identifier:
    - convert to str
    - strip whitespace
    - lowercase
    - validate against SCHEMA_NAME_ALLOWED_RE
    """
    s = "" if v is None else str(v).strip().lower()
    if not s:
        raise ValueError("Invalid name: must be a non-empty string")
    if not re.fullmatch(SCHEMA_NAME_ALLOWED_RE, s):
        raise ValueError("Invalid name: allowed characters are [a-z0-9._-]")
    return s


def _normalize_freeform_version(v) -> Optional[str]:
    """
    Normalize a free-form version string:
    - None stays None
    - trim whitespace
    - empty string -> None
    """
    if v is None:
        return None
    s = str(v).strip()
    return s if s != "" else None


# --- Reusable Annotated types --- #

SchemaLikeName = Annotated[str, BeforeValidator(_normalize_schema_like_name)]
FreeFormVersion = Annotated[Optional[str], BeforeValidator(_normalize_freeform_version)]
