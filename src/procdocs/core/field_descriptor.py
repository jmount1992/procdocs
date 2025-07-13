#!/usr/bin/env python3

import hashlib
import re
from typing import Any, Dict, List, Optional, Union, Tuple

from procdocs.core.field_type import FieldType


RESERVED_FIELDS = {"metadata", "structure"}


class FieldDescriptor:

    def __init__(self):
        self._fieldname: Optional[str] = None
        self._raw_fieldtype: Optional[str] = None
        self._fieldtype: Optional[FieldType] = None
        self._required: Optional[bool] = None
        self._description: Optional[str] = None
        self._options: Optional[List[str]] = None
        self._pattern: Optional[str] = None
        self._default: Optional[Any] = None
        self._fields: List["FieldDescriptor"] = []
        self._uid: Optional[str] = None

    @property
    def fieldname(self) -> Optional[str]:
        return self._fieldname

    @property
    def fieldtype(self) -> Optional[FieldType]:
        return self._fieldtype

    @property
    def required(self) -> Optional[bool]:
        return self._required

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def options(self) -> Optional[List[str]]:
        return self._options

    @property
    def pattern(self) -> Optional[str]:
        return self._pattern

    @property
    def default(self) -> Optional[Any]:
        return self._default

    @property
    def fields(self) -> List["FieldDescriptor"]:
        return self._fields

    @property
    def uid(self) -> Optional[str]:
        return self._uid

    def is_list(self) -> bool:
        return self.is_fieldtype(FieldType.LIST)

    def is_dict(self) -> bool:
        return self.is_fieldtype(FieldType.DICT)

    def is_enum(self) -> bool:
        return self.is_fieldtype(FieldType.ENUM)

    def is_fieldtype(self, value: Union[str, FieldType, Tuple[Union[str, FieldType], ...]]) -> bool:
        if isinstance(value, (tuple, list)):
            return any(self.is_fieldtype(v) for v in value)
        return self.fieldtype == FieldType.parse(value)

    def validate(self) -> None:
        self._validate_fieldname()
        self._validate_fieldtype()
        self._validate_pattern()
        self._validate_required()

    @classmethod
    def from_dict(cls, data: Dict, level: int = 0, validate: bool = True) -> "FieldDescriptor":
        fd = cls()
        fd._fieldname = data.get("field")
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
        return {
            "field": self.fieldname,
            "fieldtype": self._raw_fieldtype,
            "required": self.required,
            "description": self.description,
            "options": self.options,
            "pattern": self.pattern,
            "default": self.default,
            "fields": [f.to_dict() for f in self.fields],
        }

    def _compute_uid(self, fieldname: str, level: int = 0) -> str:
        raw = f"{fieldname}:{level}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]

    def _validate_fieldname(self) -> None:
        if not self.fieldname:
            raise ValueError(f"Field descriptor {self.uid} is invalid. The 'fieldname' key is not set.")

        if self.fieldname in RESERVED_FIELDS:
            raise ValueError(f"Field descriptor {self.uid} is invalid. '{self.fieldname}' is a reserved name and cannot be used.")

    def _validate_fieldtype(self) -> None:

        if self.fieldtype is FieldType.INVALID:
            raise ValueError(f"Field descriptor {self.uid} is invalid. Invalid fieldtype '{self._raw_fieldtype}'.")        

        if len(self.fields) != 0 and not (self.is_list() or self.is_dict()):
            raise ValueError(f"Field descriptor {self.uid} is invalid. Nested 'fields' only allowed for 'list' or 'dict' types ")

        if not self.options and self.is_enum():
            raise ValueError(f"Field descriptor {self.uid} is invalid. The ENUM fieldtype must define 'options'.")

    def _validate_pattern(self) -> None:
        if self.pattern:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"Field descriptor {self.uid} is invalid. Invalid regex pattern '{e}'.")

    def _validate_required(self) -> None:
        if self.required and not isinstance(self.required, bool):
            raise ValueError(f"Field descriptor {self.uid} is invalid. The 'required' must be boolean.")

    def __repr__(self):
        return f"<FieldDescriptor: {self.fieldname} (uid={self.uid}, type={self.fieldtype}, required={self.required}, default={self.default})>"
