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
        resolved, errors = self._resolve_schema(schema, registry)
        if errors:
            self._last_errors = errors
            return errors

        assert resolved is not None  # for type-checkers

        errors = []
        if self.metadata.document_type != resolved.schema_name:
            errors.append(
                f"metadata.document_type: {self.metadata.document_type!r} "
                f"does not match schema {resolved.schema_name!r}"
            )

        errors.extend(self._validate_contents(resolved))
        self._last_errors = errors
        return errors

    def _resolve_schema(self, schema: Optional[DocumentSchema], registry: Optional[SchemaRegistry]) -> tuple[Optional[DocumentSchema], list[str]]:
        """Centralized schema resolution. Returns (schema, errors)."""
        if schema is not None:
            return schema, []

        if registry is None:
            return None, ["No schema provided and no registry available for resolution"]

        doc_type = getattr(self.metadata, "document_type", None)
        if not doc_type:
            return None, ["metadata.document_type is missing; cannot resolve schema"]

        try:
            return registry.require(doc_type), []
        except LookupError as e:
            return None, [f"Schema resolution failed: {e}"]

    def _validate_contents(self, schema: DocumentSchema) -> list[str]:
        """Validate contents via the dynamic adapter. Returns human-friendly errors."""
        adapter = build_contents_adapter(schema)
        try:
            adapter.validate_python(self.contents or {})
            return []
        except ValidationError as e:
            return format_pydantic_errors_simple(e)

    # --- Convenience --- #

    @property
    def is_valid(self) -> bool:
        """True if the last `validate()` call produced no errors."""
        return len(self._last_errors) == 0
