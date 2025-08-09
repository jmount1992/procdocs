#!/usr/bin/env python3

from pydantic import Field

from procdocs.core.base.base_metadata import BaseMetadata
from procdocs.core.base.types import SchemaLikeName, FreeFormVersion


class SchemaMetadata(BaseMetadata):
    """
    Metadata for JSON *document schemas*.

    - `schema_name` (required): canonical, case-insensitive identifier for the schema.
      The value is normalized to lowercase and must match ``SCHEMA_NAME_ALLOWED_RE``.
    - `schema_version` (optional): free-form, trimmed only.

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

    schema_name: SchemaLikeName = Field(...)
    schema_version: FreeFormVersion = Field(default=None, description="Version label for this schema instance (user managed; free-form)")
