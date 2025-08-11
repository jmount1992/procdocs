#!/usr/bin/env python3
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Per‑type spec models
# ---------------------------------------------------------------------------

class StringSpec(BaseModel):
    kind: Literal["string"] = "string"
    pattern: Optional[str] = Field(default=None, description="Regex applied to string values only")


class NumberSpec(BaseModel):
    kind: Literal["number"] = "number"
    # room for min/max, integral_only, etc.


class BooleanSpec(BaseModel):
    kind: Literal["boolean"] = "boolean"


class EnumSpec(BaseModel):
    kind: Literal["enum"] = "enum"
    options: List[str] = Field(min_length=1, description="Allowed enum values")


class DictSpec(BaseModel):
    kind: Literal["dict"] = "dict"
    # NOTE: forward ref to FieldDescriptor to avoid import cycle
    fields: List["FieldDescriptor"] = Field(min_length=1, description="Nested named fields")


class ListSpec(BaseModel):
    kind: Literal["list"] = "list"
    # AUTHORING MODEL:
    # - If `fields` is provided: each list element is a dict with these fields
    # - If `fields` is omitted: list of strings (default scalar list)
    # NOTE: forward ref to FieldDescriptor to avoid import cycle
    fields: Optional[List["FieldDescriptor"]] = Field(
        default=None,
        description="Schema of each list element as a dict (omit for list[str])",
    )


class RefSpec(BaseModel):
    kind: Literal["ref"] = "ref"
    cardinality: Literal["one", "many"] = Field(default="one", description="One file or a list of files")
    allow_globs: bool = Field(default=False, description="Permit {glob: pattern} items when many")
    must_exist: bool = Field(default=False, description="Require files to exist at validation time")
    base_dir: Optional[str] = Field(default=None, description="Resolve relative paths from here")
    extensions: Optional[List[str]] = Field(default=None, description="Restrict to these file extensions")


FieldSpec = Annotated[
    Union[StringSpec, NumberSpec, BooleanSpec, EnumSpec, DictSpec, ListSpec, RefSpec],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Forward‑ref rebuild utility (called after FieldDescriptor is defined)
# ---------------------------------------------------------------------------

def rebuild_specs(FieldDescriptor: type) -> None:
    """
    Resolve forward references to FieldDescriptor after it is defined.
    Called from field_descriptor.py once FieldDescriptor exists.

    We inject the class into this module's globals so Pydantic can
    resolve the string annotation "FieldDescriptor" during model_rebuild().
    """
    globals()["FieldDescriptor"] = FieldDescriptor
    for cls in (DictSpec, ListSpec):
        cls.model_rebuild()
