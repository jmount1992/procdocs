#!/usr/bin/env python3
"""
Purpose:
    Defines Pydantic specification models for each supported ProcDocs field
    type, including nested structure and constraint details, for use in schema
    validation.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union, List, TYPE_CHECKING
from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from .field_descriptor import FieldDescriptor


# --- Per-type spec models --- #

class StringSpec(BaseModel):
    """Specification for a string field (optional regex constraint)."""
    kind: Literal["string"] = "string"
    pattern: Optional[str] = Field(
        default=None,
        description="Regex applied to string values only.",
    )


class NumberSpec(BaseModel):
    """Specification for a numeric field (int or float)."""
    kind: Literal["number"] = "number"


class BooleanSpec(BaseModel):
    """Specification for a boolean field."""
    kind: Literal["boolean"] = "boolean"


class EnumSpec(BaseModel):
    """Specification for an enum field (string constrained to fixed options)."""
    kind: Literal["enum"] = "enum"
    options: List[str] = Field(
        min_length=1,
        description="Allowed enum values (non-empty list).",
    )


class DictSpec(BaseModel):
    """Specification for a dict/object with named nested fields."""
    kind: Literal["dict"] = "dict"
    fields: List["FieldDescriptor"] = Field(
        min_length=1,
        description="Nested named fields (at least one).",
    )


class ListSpec(BaseModel):
    """Specification for a homogeneous list of items, with one element schema."""
    kind: Literal["list"] = "list"
    item: "FieldDescriptor" = Field(
        ...,
        description="Schema describing each list element.",
    )


class RefSpec(BaseModel):
    """
    Specification for file/path references.

    Semantics (resolution, existence checks) are enforced by higher-level tooling.
    """
    kind: Literal["ref"] = "ref"
    cardinality: Literal["one", "many"] = Field(
        default="one",
        description="Single file ('one') or a list of files ('many').",
    )
    allow_globs: bool = Field(
        default=False,
        description="Permit glob patterns when cardinality is 'many'.",
    )
    must_exist: bool = Field(
        default=False,
        description="Require files to exist at validation time.",
    )
    base_dir: Optional[str] = Field(
        default=None,
        description="Resolve relative paths from this directory.",
    )
    extensions: Optional[List[str]] = Field(
        default=None,
        description="Restrict to these file extensions (e.g., ['.yml', '.yaml']).",
    )
    ref_kind: Literal["file", "procdocs_document"] = Field(
        default="file",
        description="Resolve to a file path only ('file') or load+embed a ProcDocs document ('procdocs_document').",
    )
    document_type: Optional[str] = Field(
        default=None,
        description="If ref_kind='document', the expected metadata.document_type for the referenced YAML document.",
    )
    embed_as: str = Field(
        default="resolved",
        description="Key to store embedded payload under (e.g., 'doc', 'test', 'resolved').",
    )

    @model_validator(mode="after")
    def _validate_ref_semantics(self) -> "RefSpec":
        if self.ref_kind == "procdocs_document":
            if not self.document_type:
                raise ValueError("RefSpec.document_type is required when ref_kind='procdocs_document'")
            if not str(self.embed_as).strip():
                raise ValueError("RefSpec.embed_as must be a non-empty string when ref_kind='procdocs_document'")
        else:
            # ref_kind == "file"
            if self.document_type is not None:
                raise ValueError("RefSpec.document_type must be omitted when ref_kind='file'")
            # Optional: disallow embed_as for files to reduce confusion
            if self.embed_as != "resolved":
                raise ValueError("RefSpec.embed_as is only applicable when ref_kind='procdocs_document'")

        if self.allow_globs and self.cardinality != "many":
            raise ValueError("RefSpec.allow_globs requires cardinality='many'")

        return self


# --- Discriminated union of all per-type specs --- #
# Used by FieldDescriptor to accept/validate the correct spec model
# based on the 'kind' field in schema JSON.

FieldSpec = Annotated[
    Union[StringSpec, NumberSpec, BooleanSpec, EnumSpec, DictSpec, ListSpec, RefSpec],
    Field(discriminator="kind"),
]


# --- Forward-Ref Rebuild Utility --- #

def rebuild_specs(FieldDescriptor: type) -> None:
    """
    Resolve forward references to FieldDescriptor after it is defined.

    Must be called by the module that defines FieldDescriptor, once the class exists.
    Injects FieldDescriptor into this module's globals so Pydantic can resolve the
    string annotations during model_rebuild().
    """
    globals()["FieldDescriptor"] = FieldDescriptor
    for cls in (DictSpec, ListSpec):
        cls.model_rebuild()
