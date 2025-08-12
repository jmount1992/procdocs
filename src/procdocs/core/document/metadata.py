#!/usr/bin/env python3
"""
Pydantic model for document metadata in ProcDocs.

Defines the user-facing metadata required for document instances, built on top of
`BaseMetadata`.
"""

from pydantic import Field

from procdocs.core.metadata_base import BaseMetadata
from procdocs.core.annotated_types import DocumentTypeName, FreeFormVersion


class DocumentMetadata(BaseMetadata):
    """
    Metadata attached to a ProcDocs YAML document instance.

    Fields
    ------
    document_type:
        Canonical, case-insensitive schema name. Normalized to lowercase and
        validated against `SCHEMA_NAME_ALLOWED_RE`.
    document_version:
        Optional, user-managed free-form label. Whitespace is trimmed; empty → None.

    Example
    -------
    >>> from procdocs.core.document.metadata import DocumentMetadata
    >>> md = DocumentMetadata(
    ...     format_version="0.0.1",
    ...     document_type="Test.Schema-01",
    ...     document_version="  1.0-draft  ",
    ...     extensions={"author": "alice"}
    ... )
    >>> md.document_type
    'test.schema-01'
    >>> md.document_version
    '1.0-draft'
    >>> md.extensions["author"]
    'alice'
    """

    document_type: DocumentTypeName = Field(
        ...,
        description="Canonical schema name for this document (lowercased, validated).",
    )
    document_version: FreeFormVersion = Field(
        default=None,
        description="Free-form version label for this document instance (optional).",
    )
