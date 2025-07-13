#!/usr/bin/env python3

import hashlib
import re
from typing import Any, Dict, List, Optional, Union, Tuple

from procdocs.core.field_type import FieldType
from procdocs.core.utils import RESERVED_FIELDNAMES


class DocumentFieldDescriptor:
    """
    Represents a single field descriptor in a document schema.

    This class models the constraints, type, and structure of a single field
    within a schema and supports nested definitions for compound types.
    """

    def __init__(self):
        """
        Initializes a new, empty DocumentFieldDescriptor. Fields must be populated via `from_dict()`.
        """
        self._fieldname: Optional[str] = None
        self._raw_fieldtype: Optional[str] = None
        self._fieldtype: Optional[FieldType] = None
        self._required: Optional[bool] = None
        self._description: Optional[str] = None
        self._options: Optional[List[str]] = None
        self._pattern: Optional[str] = None
        self._default: Optional[Any] = None
        self._fields: List["DocumentFieldDescriptor"] = []
        self._uid: Optional[str] = None

    @property
    def fieldname(self) -> Optional[str]:
        """Returns the field name for this descriptor."""
        return self._fieldname

    @property
    def fieldtype(self) -> Optional[FieldType]:
        """Returns the parsed field type (e.g., STRING, NUMBER, LIST)."""
        return self._fieldtype

    @property
    def required(self) -> Optional[bool]:
        """Returns whether the field is required."""
        return self._required

    @property
    def description(self) -> Optional[str]:
        """Returns a human-readable description of the field, if provided."""
        return self._description

    @property
    def options(self) -> Optional[List[str]]:
        """Returns the list of valid options (for enum fields only)."""
        return self._options

    @property
    def pattern(self) -> Optional[str]:
        """Returns the regex pattern constraint, if defined."""
        return self._pattern

    @property
    def default(self) -> Optional[Any]:
        """Returns the default value, if any."""
        return self._default

    @property
    def fields(self) -> List["DocumentFieldDescriptor"]:
        """Returns the list of nested meta field descriptors (for list/dict types)."""
        return self._fields

    @property
    def uid(self) -> Optional[str]:
        """Returns the unique ID of the descriptor, derived from name and nesting level."""
        return self._uid

    def is_list(self) -> bool:
        """Returns True if the fieldtype is LIST."""
        return self.is_fieldtype(FieldType.LIST)

    def is_dict(self) -> bool:
        """Returns True if the fieldtype is DICT."""
        return self.is_fieldtype(FieldType.DICT)

    def is_enum(self) -> bool:
        """Returns True if the fieldtype is ENUM."""
        return self.is_fieldtype(FieldType.ENUM)

    def is_fieldtype(self, value: Union[str, FieldType, Tuple[Union[str, FieldType], ...]]) -> bool:
        """
        Checks if the field's type matches one or more given types.

        Args:
            value: A FieldType, string, or tuple/list of those.

        Returns:
            bool: True if the fieldtype matches any of the given values.
        """
        if isinstance(value, (tuple, list)):
            return any(self.is_fieldtype(v) for v in value)
        return self.fieldtype == FieldType.parse(value)

    def validate(self) -> None:
        """
        Validates the field descriptor against all applicable rules:
        - Field name is present and not reserved.
        - Fieldtype is valid.
        - Pattern is valid regex (if applicable).
        - ENUMs have defined options.
        - Nested fields are only used in LIST or DICT types.

        Raises:
            ValueError or TypeError if validation fails.
        """
        self._validate_fieldname()
        self._validate_fieldtype()
        self._validate_pattern()
        self._validate_required()

    @classmethod
    def from_dict(cls, data: Dict, level: int = 0, validate: bool = True) -> "DocumentFieldDescriptor":
        """
        Creates a DocumentFieldDescriptor from a dictionary.

        Args:
            data (Dict): A dictionary conforming to meta-schema field definition.
            level (int): The nesting level (used for UID computation).
            validate (bool): Whether to validate the field on load.

        Returns:
            DocumentFieldDescriptor: Parsed and optionally validated descriptor.
        """
        fd = cls()
        fd._fieldname = data.get("fieldname")
        fd._raw_fieldtype = data.get("fieldtype", "string")
        fd._fieldtype = FieldType.parse(fd._raw_fieldtype)
        fd._required = data.get("required", True)
        fd._description = data.get("description")
        fd._options = data.get("options")
        fd._pattern = data.get("pattern")
        fd._default = data.get("default")
        fd._uid = fd._compute_uid(fd._fieldname, level)

        fields = data.get("fields", [])
        if fields:
            fd._fields = [cls.from_dict(child, level=level + 1) for child in fields]

        if validate:
            fd.validate()
        return fd

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes this DocumentFieldDescriptor to a dictionary.

        Returns:
            dict: A dictionary representation of the field descriptor.
        """
        return {
            "fieldname": self.fieldname,
            "fieldtype": self._raw_fieldtype,
            "required": self.required,
            "description": self.description,
            "options": self.options,
            "pattern": self.pattern,
            "default": self.default,
            "fields": [f.to_dict() for f in self.fields],
        }

    def _compute_uid(self, fieldname: str, level: int = 0) -> str:
        """
        Generates a short unique identifier for the field.

        Args:
            fieldname (str): The name of the field.
            level (int): Nesting level in the structure.

        Returns:
            str: A 10-character hash.
        """
        raw = f"{fieldname}:{level}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]

    def _validate_fieldname(self) -> None:
        """Checks that the fieldname exists and is not reserved."""
        if not self.fieldname:
            raise ValueError(f"Field descriptor {self.uid} is invalid. The 'fieldname' key is not set.")

        if self.fieldname in RESERVED_FIELDNAMES:
            raise ValueError(f"Field descriptor {self.uid} is invalid. '{self.fieldname}' is a reserved name and cannot be used.")
        
        if '-' in self.fieldname:
            raise ValueError(f"Field descriptor {self.uid} is invalid. '{self.fieldname}' cannot contain '-'.")

    def _validate_fieldtype(self) -> None:
        """Checks the validity of the fieldtype and nested field logic."""
        if self.fieldtype is FieldType.INVALID:
            raise ValueError(f"Field descriptor {self.uid} is invalid. Invalid fieldtype '{self._raw_fieldtype}'.")        

        if len(self.fields) != 0 and not (self.is_list() or self.is_dict()):
            raise ValueError(f"Field descriptor {self.uid} is invalid. Nested 'fields' only allowed for 'list' or 'dict' types ")

        if not self.options and self.is_enum():
            raise ValueError(f"Field descriptor {self.uid} is invalid. The ENUM fieldtype must define 'options'.")

    def _validate_pattern(self) -> None:
        """Validates the regex pattern if specified."""
        if self.pattern:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"Field descriptor {self.uid} is invalid. Invalid regex pattern '{e}'.")

    def _validate_required(self) -> None:
        """Ensures the 'required' attribute is a boolean."""
        if self.required and not isinstance(self.required, bool):
            raise ValueError(f"Field descriptor {self.uid} is invalid. The 'required' must be boolean.")

    def __repr__(self):
        """Returns a compact string representation of the field descriptor."""
        return f"<FieldDescriptor: {self.fieldname} (uid={self.uid}, type={self.fieldtype}, required={self.required}, default={self.default})>"
