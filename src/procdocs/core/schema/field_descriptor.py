#!/usr/bin/env python3
import hashlib
import re
from typing import Any, Optional

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
    computed_field,
    PrivateAttr,
)

from procdocs.core.schema.field_type import FieldType
from procdocs.core import constants as C
from procdocs.core.utils import is_valid_fieldname_pattern


class FieldDescriptor(BaseModel):
    """
    Pydantic v2 model representing one field in a document meta‑schema.

    - Supports recursion via `fields: list[FieldDescriptor] | None`
    - Enforces: reserved names, allowed name pattern, regex validity, enum options
    - Only `list` / `dict` may have nested `fields`
    - For LIST: exactly one child descriptor describing the element schema
    - UID is computed from canonical path (preferred) or (fieldname, level)
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    _path: str = PrivateAttr(default="")  # excluded from serialization

    # --- Declared fields --- #
    fieldname: str = Field(..., description="The name of the field")
    fieldtype: FieldType = Field(default=FieldType.STRING, description="Field type")
    required: bool = Field(default=True, description="Whether this field is required")
    description: str | None = Field(default=None, description="Human-readable description")
    options: list[str] | None = Field(default=None, description="Valid options for enum fields")
    pattern: str | None = Field(default=None, description="Regex pattern for validation")
    default: Any | None = Field(default=None, description="Default value")
    fields: list["FieldDescriptor"] | None = Field(default=None, description="Nested field descriptors")

    # --- Computed UID --- #
    @computed_field  # type: ignore[prop-decorator]
    @property
    def uid(self) -> str:
        raw_encode = self._path.encode(C.DEFAULT_TEXT_ENCODING)
        return hashlib.sha1(raw_encode).hexdigest()[:10]

    # --- Validators --- #

    @field_validator("fieldtype", mode="before")
    @classmethod
    def _parse_fieldtype(cls, v):
        return FieldType.parse(v)

    @field_validator("fieldname", mode="before")
    @classmethod
    def _normalize_and_validate_fieldname(cls, v) -> str:
        s = "" if v is None else str(v).strip()
        if not s:
            raise ValueError("The 'fieldname' key is not set")
        if s in C.RESERVED_FIELDNAMES:
            raise ValueError(f"'{s}' is a reserved name and cannot be used")
        if not is_valid_fieldname_pattern(s):
            # use pattern text for stable error message
            raise ValueError(
                f"The fieldname '{s}' must match the pattern '{C.FIELDNAME_ALLOWED_PATTERN.pattern}'"
            )
        return s

    @field_validator("pattern")
    @classmethod
    def _validate_regex_pattern(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}") from e
        return v

    @model_validator(mode="after")
    def _post_validate(self) -> "FieldDescriptor":
        # invalid/unknown types must be rejected
        if self.fieldtype == FieldType.INVALID:
            raise ValueError("Unknown fieldtype; valid types are: string, number, boolean, list, dict, enum")

        # ENUM must define options (non-empty, unique)
        if self.fieldtype == FieldType.ENUM:
            if not self.options:
                raise ValueError("ENUM fieldtype must define 'options'")
            opts = [str(o) for o in self.options]
            if any(s.strip() == "" for s in opts):
                raise ValueError("ENUM 'options' must not contain empty strings")
            if len(set(opts)) != len(opts):
                raise ValueError("ENUM 'options' contain duplicates")

        # Nested fields only allowed for LIST or DICT
        if self.fields and self.fieldtype not in (FieldType.LIST, FieldType.DICT):
            raise ValueError("Nested 'fields' only allowed for 'list' or 'dict' types")

        # If container, enforce children shape
        if self.is_list() or self.is_dict():
            if self.fields is not None and len(self.fields) == 0:
                raise ValueError(f"{self.fieldtype.value} must define at least one child in 'fields' if provided")

        return self

    # --- Helpers --- #
    def is_fieldtype(self, *types) -> bool:
        # accept FieldType or str
        targets = {FieldType.parse(t) for t in types}
        return self.fieldtype in targets

    def is_list(self) -> bool:
        return self.fieldtype == FieldType.LIST

    def is_dict(self) -> bool:
        return self.fieldtype == FieldType.DICT

    def is_enum(self) -> bool:
        return self.fieldtype == FieldType.ENUM


# Ensure forward refs work in all import orders
FieldDescriptor.model_rebuild()
