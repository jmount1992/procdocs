#!/usr/bin/env python3

from pydantic import Field

from procdocs.core.metadata_base import BaseMetadata
from procdocs.core.annotated_types import DocumentTypeName, FreeFormVersion


class DocumentMetadata(BaseMetadata):
    """
    Metadata for concrete YAML documents.

    - `document_type` (required): canonical, case-insensitive reference to the target
      schema's name. Normalized to lowercase and must match ``SCHEMA_NAME_ALLOWED_RE``.
    - `document_version` (optional): user-managed, free-form label for this document
      instance; whitespace is trimmed and blank values become `None`.

    Notes
    -----
    - Inherits from `BaseMetadata`, which:
        - enforces strict semver for `format_version`,
        - forbids unknown top-level fields (`extra="forbid"`),
        - provides an `extensions: dict[str, Any]` bag for user-defined metadata.
    - Use `document_type` to select/validate against the corresponding schema.

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

    document_type: DocumentTypeName = Field(...)
    document_version: FreeFormVersion = Field(default=None, description="Version label for this document instance (user managed; free-form)")
