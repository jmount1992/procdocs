#!/usr/bin/env python3
"""
Purpose:
    Defines Pydantic specification models for each supported ProcDocs field
    type, including nested structure and constraint details, for use in schema
    validation.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union, List, TYPE_CHECKING
from pydantic import BaseModel, Field

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
