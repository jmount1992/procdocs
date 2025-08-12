#!/usr/bin/env python3
"""
Pydantic model for JSON document-schema metadata in ProcDocs.

Defines the metadata required for schema files, built on top of `BaseMetadata`.
"""

from pydantic import Field

from procdocs.core.metadata_base import BaseMetadata
from procdocs.core.annotated_types import SchemaName, FreeFormVersion


class SchemaMetadata(BaseMetadata):
    """
    Metadata attached to a ProcDocs JSON document schema.

    Fields
    ------
    schema_name:
        Canonical, case-insensitive schema identifier. Normalized to lowercase and
        validated against `SCHEMA_NAME_ALLOWED_RE`.
    schema_version:
        Optional, user-managed free-form label. Whitespace is trimmed; empty → None.

    Example
    -------
    >>> from procdocs.core.schema.metadata import SchemaMetadata
    >>> md = SchemaMetadata(
    ...     format_version="0.0.1",
    ...     schema_name="Test.Schema-01",
    ...     schema_version=" 0.3 ",
    ...     extensions={"owner": "QA Team"}
    ... )
    >>> md.schema_name
    'test.schema-01'
    >>> md.schema_version
    '0.3'
    """

    schema_name: SchemaName = Field(
        ...,
        description="Canonical schema identifier (lowercased, validated).",
    )
    schema_version: FreeFormVersion = Field(
        default=None,
        description="Free-form version label for this schema (optional).",
    )
