#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.document.metadata import DocumentMetadata
from procdocs.core.schema.registry import SchemaRegistry
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.runtime_model import build_contents_adapter


class Document(BaseModel):
    """
    A concrete ProcDocs document:
      - `metadata`: validated by DocumentMetadata
      - `contents`: free-form mapping that can be validated against a DocumentSchema

    Use:
        doc = Document.from_file("doc.yaml")
        errors = doc.validate(registry=my_registry)   # auto-resolve by document_type
        if not errors:
            ... # good to render with Jinja etc.
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    metadata: DocumentMetadata = Field(...)
    contents: Dict[str, Any] = Field(default_factory=dict)

    # Keep last validation result (not serialized)
    _last_errors: List[str] = PrivateAttr(default_factory=list)

    # --- IO ------------------------------------------------------------------ #

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "Document":
        """
        Load a document from a YAML file (.yml/.yaml).
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"The file '{p}' does not exist")
        if p.suffix.lower() not in {".yml", ".yaml"}:
            raise ValueError(f"Invalid document file extension for '{p.name}'; expected a .yml/.yaml file")
        data = yaml.safe_load(p.read_text(encoding=DEFAULT_TEXT_ENCODING)) or {}
        return cls.model_validate(data)

    @classmethod
    def from_json_str(cls, text: str) -> "Document":
        """Helper for tests / tools that already have JSON doc text."""
        return cls.model_validate_json(text)

    # --- Validation ----------------------------------------------------------- #

    def validate(self, schema: Optional[DocumentSchema] = None, registry: Optional[SchemaRegistry] = None) -> List[str]:
        """
        Validate this document against a schema.

        - If `schema` is provided: validate against it.
        - Else if `registry` is provided: resolve schema from `metadata.document_type`.
        - Else: returns an error prompting for a schema or registry.

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
                f"metadata.document_type: '{self.metadata.document_type}' does not match schema '{schema.schema_name}'"
            )

        # Validate contents shape & types via dynamic adapter
        adapter = build_contents_adapter(schema)
        try:
            adapter.validate_python(self.contents or {})
        except ValidationError as e:
            errors.extend(_format_pydantic_errors_simple(e))

        # Save and return
        self._last_errors = errors
        return errors

    # --- Convenience ---------------------------------------------------------- #

    @property
    def is_valid(self) -> bool:
        return len(self._last_errors) == 0


def _format_pydantic_errors_simple(e: ValidationError) -> List[str]:
    """
    Minimal, stable formatter for Pydantic errors.
    Example path: contents.steps[0].step_number
    """
    msgs: List[str] = []
    for err in e.errors():
        loc = err.get("loc", ())
        msg = err.get("msg", "Validation error")
        parts: List[str] = []
        for seg in loc:
            if isinstance(seg, int):
                parts.append(f"[{seg}]")
            else:
                if parts:  # dot before string segment (except at start)
                    parts.append(".")
                parts.append(str(seg))
        path = "".join(parts) if parts else "<root>"
        msgs.append(f"{path}: {msg}")
    return msgs
