#!/usr/bin/env python3
"""
DocumentSchema: ProcDocs JSON meta-schema for a document type.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from procdocs.core.constants import DEFAULT_TEXT_ENCODING, SUPPORTED_SCHEMA_EXT
from procdocs.core.schema.field_descriptor import FieldDescriptor, DictSpec, ListSpec
from procdocs.core.schema.field_type import FieldType
from procdocs.core.schema.metadata import SchemaMetadata


# --- Model --- #

class DocumentSchema(BaseModel):
    """
    ProcDocs meta-schema defining the structure of a document type.

    Fields:
    -------
    metadata:
        is validated by `SchemaMetadata` (schema_name, format_version, etc.)
    structure:
        is an ordered list of `FieldDescriptor` entries (nested via specs)

    Notes:
    ------
    On construction we:
        1) assign a canonical private `_path` to all nodes (used for stable UIDs)
        2) validate there are no duplicate `fieldname` values among siblings (recursively)
    """

    ConfigDict(validate_assignment=True, extra="forbid")

    metadata: SchemaMetadata = Field(...)
    structure: list[FieldDescriptor] = Field(default_factory=list)

    # --- Convenience --- #

    @property
    def schema_name(self) -> str:
        """Canonical schema identifier (lowercased)."""
        return self.metadata.schema_name

    @property
    def format_version(self) -> str:
        """ProcDocs format compatibility version (strict semver x.y.z)."""
        return self.metadata.format_version

    # --- Normalization / Validation --- #

    @model_validator(mode="after")
    def _post_init(self) -> "DocumentSchema":
        # 1) assign canonical paths (used by FieldDescriptor.uid)
        self._assign_paths(self.structure, parent_path="")
        # 2) enforce no duplicate fieldnames at each sibling level
        self._check_no_duplicates(self.structure, at_path="structure")
        return self

    @classmethod
    def _assign_paths(cls, fds: Iterable[FieldDescriptor], parent_path: str) -> None:
        """
        Assign canonical `_path` to each FieldDescriptor and recurse into
        dict/list children held within their `spec`.
        """
        for fd in fds:
            fd._path = f"{parent_path}/{fd.fieldname}" if parent_path else fd.fieldname

            # Recurse into DICT -> spec.fields
            if fd.fieldtype == FieldType.DICT:
                spec: DictSpec = fd.spec  # type: ignore[assignment]
                cls._assign_paths(spec.fields, parent_path=fd._path)

            # Recurse into LIST -> spec.item (single FieldDescriptor)
            if fd.fieldtype == FieldType.LIST:
                spec: ListSpec = fd.spec  # type: ignore[assignment]
                # Use '[]' in path to distinguish the element from the list node itself.
                # This keeps FieldDescriptor.uid stable and unambiguous.
                spec.item._path = f"{fd._path}[]/{spec.item.fieldname}"
                # And recurse further in case the item is dict/list
                cls._assign_paths([spec.item], parent_path=f"{fd._path}[]")

    @classmethod
    def _check_no_duplicates(cls, fds: Iterable[FieldDescriptor], at_path: str) -> None:
        """
        Ensure no duplicate fieldnames among siblings, recursing into dict/list specs.
        """
        names = [fd.fieldname for fd in fds]
        dup_counts = {n: c for n, c in Counter(names).items() if c > 1}
        if dup_counts:
            details = ", ".join(f"{n} ×{c}" for n, c in sorted(dup_counts.items()))
            raise ValueError(f"Duplicate field names at {at_path!r}: {details}")

        for fd in fds:
            if fd.fieldtype == FieldType.DICT:
                spec: DictSpec = fd.spec  # type: ignore[assignment]
                cls._check_no_duplicates(spec.fields, f"{at_path}.{fd.fieldname}")
            elif fd.fieldtype == FieldType.LIST:
                spec: ListSpec = fd.spec  # type: ignore[assignment]
                # The item itself may be a dict/list; treat it as a child list in the path.
                cls._check_no_duplicates([spec.item], f"{at_path}.{fd.fieldname}[]")

    # --- File IO --- #

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "DocumentSchema":
        """
        Load a DocumentSchema from a JSON file.

        Rules:
        - Only supported schema extensions are accepted (JSON-only at present).
        - File must exist; errors are explicit.

        Raises:
            FileNotFoundError: if the file does not exist
            ValueError: if the file extension is not supported
            ValidationError: if the payload fails model validation
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"The file {str(p)!r} does not exist")
        if p.suffix.lower() not in SUPPORTED_SCHEMA_EXT:
            raise ValueError(
                f"Invalid schema file extension for {p.name!r}; expected one of {sorted(SUPPORTED_SCHEMA_EXT)}"
            )
        data = json.loads(p.read_text(encoding=DEFAULT_TEXT_ENCODING))
        return cls(**data)
