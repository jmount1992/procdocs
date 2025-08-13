#!/usr/bin/env python3
"""
Purpose:
    Defines the base metadata model for ProcDocs.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from procdocs.core.constants import PROCDOCS_FORMAT_VERSION
from procdocs.core.utils import (
    is_strict_semver,
    is_semver_at_least,
    is_semver_before,
)


class BaseMetadata(BaseModel):
    """
    Minimal base class for ProcDocs metadata blocks.

    Parameters
    ----------
    format_version:
        ProcDocs format compatibility version (strict semver ``x.y.z``).
        Defaults to the library's current version.
    extensions:
        Free-form key/value bag for user-defined metadata. Keys must be
        non-empty strings. Values are unrestricted.

    Example
    -------
    >>> from procdocs.core.metadata_base import BaseMetadata
    >>> m = BaseMetadata(
    ...     format_version="0.0.1",
    ...     extensions={"created_by": "alice@example.com"}
    ... )
    >>> m.extensions["created_by"]
    'alice@example.com'
    """

    # Keep models strict at the top level; extensibility lives in `extensions`.
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    # Current ProcDocs format default (overrideable by callers).
    format_version: str = Field(
        default=PROCDOCS_FORMAT_VERSION,
        description="ProcDocs format compatibility version (strict semver x.y.z).",
    )

    # Explicit bag for user-defined metadata.
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description="User-defined metadata (free-form key/value).",
    )

    # --- Validators --- #

    @field_validator("format_version", mode="before")
    @classmethod
    def _validate_format_version(cls, v: str) -> str:
        """Normalize and validate ``format_version`` as strict semver."""
        s = str(v).strip()
        if not is_strict_semver(s):
            raise ValueError(f"Invalid format version: {v!r}")
        return s

    @field_validator("extensions")
    @classmethod
    def _validate_extensions(cls, ext: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure extension keys are non-empty strings and normalize by stripping whitespace.
        """
        if not ext:
            return ext
        normalized: dict[str, Any] = {}
        for k, val in ext.items():
            if not isinstance(k, str):
                raise ValueError(f"Extension keys must be strings, got {type(k).__name__}: {k!r}")
            ks = k.strip()
            if not ks:
                raise ValueError("Extension keys must be non-empty strings.")
            if ks in normalized and normalized[ks] is not val:
                # Avoid silent overwrite when accidental whitespace duplicates occur.
                raise ValueError(f"Duplicate extension key after normalization: {ks!r}")
            normalized[ks] = val
        return normalized

    # --- Helpers --- #

    @classmethod
    def current_format_version(cls) -> str:
        """Return the library's current ProcDocs format version default."""
        return PROCDOCS_FORMAT_VERSION

    def format_version_at_least(self, threshold: str) -> bool:
        """Return True if ``self.format_version >= threshold`` (semver-aware)."""
        return is_semver_at_least(self.format_version, threshold)

    def format_version_before(self, threshold: str) -> bool:
        """Return True if ``self.format_version < threshold`` (semver-aware)."""
        return is_semver_before(self.format_version, threshold)
