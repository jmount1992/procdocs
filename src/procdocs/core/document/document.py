#!/usr/bin/env python3
"""
Purpose:
    Represents a concrete ProcDocs YAML document. Validates metadata via
    DocumentMetadata and validates contents against a DocumentSchema using
    a runtime adapter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.document.metadata import DocumentMetadata
from procdocs.core.schema.registry import SchemaRegistry
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.runtime_model import build_contents_adapter
from procdocs.core.formatting import format_pydantic_errors_simple


class Document(BaseModel):
    """
    A concrete ProcDocs document.

    Typical use:
        >>> doc = Document.from_file("doc.yaml")
        >>> errors = doc.validate(registry=my_registry)   # resolve by metadata.document_type
        >>> if not errors:
        ...     pass  # ready to render
    """

    ConfigDict(validate_assignment=True, extra="forbid")

    metadata: DocumentMetadata = Field(..., description="Document metadata (validated).")
    contents: Dict[str, Any] = Field(default_factory=dict, description="User content to validate against a schema.")

    # Keep last validation result (not serialized)
    _last_errors: List[str] = PrivateAttr(default_factory=list)

    # --- IO --- #

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "Document":
        """
        Load a document from a YAML file (.yml/.yaml).

        Raises:
            FileNotFoundError: if the file does not exist
            ValueError: if the extension is not .yml/.yaml
            ValidationError: if the loaded payload fails model validation
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"The file {str(p)!r} does not exist")
        if p.suffix.lower() not in {".yml", ".yaml"}:
            raise ValueError(f"Invalid document file extension for {p.name!r}; expected a .yml/.yaml file")
        data = yaml.safe_load(p.read_text(encoding=DEFAULT_TEXT_ENCODING)) or {}
        return cls.model_validate(data)

    # --- Validation --- #

    def validate(self, schema: Optional[DocumentSchema] = None, registry: Optional[SchemaRegistry] = None) -> List[str]:
        """
        Validate this document against a schema.

        Resolution:
        - If `schema` is provided, validate against it.
        - Else if `registry` is provided, resolve using `metadata.document_type`.
        - Else, return an error prompting for a schema or registry.

        Returns:
            List of human-readable error messages (empty list = valid).
        """
        errors: List[str] = []

        # Resolve schema
        if schema is None:
            if registry is None:
                self._last_errors = ["No schema provided and no registry available for resolution"]
                return self._last_errors
            if not self.metadata or not self.metadata.document_type:
                self._last_errors = ["metadata.document_type is missing; cannot resolve schema"]
                return self._last_errors
            try:
                schema = registry.require(self.metadata.document_type)
            except LookupError as e:
                self._last_errors = [f"Schema resolution failed: {e}"]
                return self._last_errors

        # Check the metadata.document_type matches the schema name
        if self.metadata.document_type != schema.schema_name:
            errors.append(
                f"metadata.document_type: {self.metadata.document_type!r} does not match schema {schema.schema_name!r}"
            )

        # Validate contents shape & types via dynamic adapter
        adapter = build_contents_adapter(schema)
        try:
            adapter.validate_python(self.contents or {})
        except ValidationError as e:
            errors.extend(format_pydantic_errors_simple(e))

        # Save and return
        self._last_errors = errors
        return errors

    # --- Convenience --- #

    @property
    def is_valid(self) -> bool:
        """True if the last `validate()` call produced no errors."""
        return len(self._last_errors) == 0
