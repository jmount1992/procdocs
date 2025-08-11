#!/usr/bin/env python3

from typing import Any
from pydantic import (
    BaseModel, ConfigDict,
    Field, field_validator
)

from procdocs.core.constants import PROCDOCS_FORMAT_VERSION
from procdocs.core.utils import (
    is_strict_semver,
    is_semver_at_least,
    is_semver_before
)


class BaseMetadata(BaseModel):
    """
    Base class for ProcDocs metadata blocks.

    Fields
    ------
    - `format_version` (required): the **ProcDocs format version** which governs which
      metadata fields and validation rules are expected. This is not a user document/schema
      version. The format version must follow semantic version rules (i.e., form x.y.z)
    - `extensions` (optional): an explicit, free-form bag for user defined metadata keys. 
      This allows the top-level namespace clean and prevents field typos from sneaking in.

    Example
    -------
        >>> from procdocs.core.base.base_metadata import BaseMetadata
        >>> m = BaseMetadata(
        ...     format_version="0.0.1",
        ...     extensions={
        ...         "created_by": "alice@example.com",
        ...         "last_reviewed": "2025-08-09"
        ...     }
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
        """Normalizes and validates the format version as strict semver"""
        s = str(v).strip()
        if not is_strict_semver(s):
            raise ValueError(f"Invalid format version: '{v}'")
        return s

    # --- Helpers --- #

    @classmethod
    def current_format_version(cls) -> str:
        """Return the library's current ProcDocs format version default."""
        return PROCDOCS_FORMAT_VERSION

    def format_version_at_least(self, threshold: str) -> bool:
        """True if this metadata's format_version >= threshold."""
        return is_semver_at_least(self.format_version, threshold)

    def format_version_before(self, threshold: str) -> bool:
        """True if this metadata's format_version < threshold."""
        return is_semver_before(self.format_version, threshold)
