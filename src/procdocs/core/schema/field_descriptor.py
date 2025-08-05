#!/usr/bin/env python3
import hashlib
import re
from typing import Any, List, Optional

from pydantic import BaseModel, Field, root_validator, validator

from procdocs.core.schema.field_type import FieldType
from procdocs.core.utils import (
    RESERVED_FIELDNAMES,
    FIELDNAME_ALLOWED_PATTERN,
    is_valid_fieldname_pattern
)


class FieldDescriptor(BaseModel):
    """
    Represents a single field descriptor in a document schema.
    """

    fieldname: str = Field(..., description="The name of the field")
    fieldtype: FieldType = Field(FieldType.STRING, description="Field type")
    required: bool = Field(default=True, description="Whether this field is required")
    description: Optional[str] = Field(default=None, description="Human-readable description")
    options: Optional[List[str]] = Field(default=None, description="Valid options for enum fields")
    pattern: Optional[str] = Field(default=None, description="Regex pattern for validation")
    default: Optional[Any] = Field(default=None, description="Default value")
    fields: Optional[List["FieldDescriptor"]] = Field(default=None, description="Nested field descriptors")
    uid: Optional[str] = Field(default=None, description="Unique identifier")

    class Config:
        # Enable recursion for forward references
        arbitrary_types_allowed = True
        validate_assignment = True

    # # --- Validators ---
    # @validator("uid", always=True)
    # def compute_uid(cls, v, values):
    #     """Automatically generate UID if not provided."""
    #     if v:
    #         return v
    #     fieldname = values.get("fieldname", "")
    #     level = values.get("__nesting_level", 0)  # custom injection for recursion if needed
    #     raw = f"{fieldname}:{level}"
    #     return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]

    # @validator("fieldname")
    # def validate_fieldname(cls, v):
    #     if not v:
    #         raise ValueError("The 'fieldname' key is not set")
    #     if v in RESERVED_FIELDNAMES:
    #         raise ValueError(f"'{v}' is a reserved name and cannot be used")
    #     if not is_valid_fieldname_pattern(v):
    #         raise ValueError(
    #             f"The fieldname '{v}' must match the pattern '{FIELDNAME_ALLOWED_PATTERN.pattern}'"
    #         )
    #     return v

    # @validator("fieldtype", pre=True)
    # def parse_fieldtype(cls, v):
    #     # Accepts strings or FieldType enums and converts to FieldType
    #     return FieldType.parse(v)

    # @validator("pattern")
    # def validate_regex_pattern(cls, v):
    #     if v:
    #         try:
    #             re.compile(v)
    #         except re.error as e:
    #             raise ValueError(f"Invalid regex pattern: {e}")
    #     return v

    # @root_validator
    # def validate_fieldtype_logic(cls, values):
    #     fieldtype = values.get("fieldtype")
    #     options = values.get("options")
    #     fields = values.get("fields")

    #     # ENUM must define options
    #     if fieldtype == FieldType.ENUM and not options:
    #         raise ValueError("ENUM fieldtype must define 'options'")

    #     # Nested fields only allowed for list/dict
    #     if fields and not (fieldtype in (FieldType.LIST, FieldType.DICT)):
    #         raise ValueError("Nested 'fields' only allowed for 'list' or 'dict' types")

    #     return values

    def is_fieldtype(self, *types) -> bool:
        """Convenience helper like original implementation."""
        return self.fieldtype in [FieldType.parse(t) for t in types]

    def is_list(self) -> bool:
        return self.fieldtype == FieldType.LIST

    def is_dict(self) -> bool:
        return self.fieldtype == FieldType.DICT

    def is_enum(self) -> bool:
        return self.fieldtype == FieldType.ENUM

    def __repr__(self):
        return (
            f"<FieldDescriptor: {self.fieldname} "
            f"(uid={self.uid}, type={self.fieldtype}, required={self.required}, default={self.default})>"
        )


# Allow self-referencing
FieldDescriptor.update_forward_refs()