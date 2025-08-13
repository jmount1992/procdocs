#!/usr/bin/env python3
"""
Purpose:
    Provides reusable annotated types and normalization helpers for ProcDocs'
    Pydantic models such as schema names, and free-form version strings.
"""

from typing import Any, Annotated, Optional
from pydantic import BeforeValidator

from procdocs.core.constants import SCHEMA_NAME_ALLOWED_RE


# --- Normalizers --- #

def _normalize_schema_name(v: Any) -> str:
    """
    Normalize a schema/document type identifier:
    - coerce to str
    - strip surrounding whitespace
    - lowercase
    - validate via fullmatch against SCHEMA_NAME_ALLOWED_RE
    """
    text = "" if v is None else str(v).strip().lower()
    if not text:
        raise ValueError("Invalid name: must be a non-empty string")
    if not SCHEMA_NAME_ALLOWED_RE.fullmatch(text):
        raise ValueError(
            f"Invalid name: {text!r}. Allowed pattern: {SCHEMA_NAME_ALLOWED_RE.pattern!r}"
        )
    return text


def _normalize_freeform_version(v: Any) -> Optional[str]:
    """
    Normalize a free-form version string:
    - None stays None
    - coerce to str and trim whitespace
    - empty/whitespace-only -> None
    - preserves case/content (no lowercasing)
    """
    if v is None:
        return None
    text = str(v).strip()
    return text if text != "" else None


# --- Reusable Annotated types --- #

SchemaName = Annotated[str, BeforeValidator(_normalize_schema_name)]
DocumentTypeName = SchemaName
FreeFormVersion = Annotated[Optional[str], BeforeValidator(_normalize_freeform_version)]
