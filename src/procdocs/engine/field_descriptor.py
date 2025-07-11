#!/usr/bin/env python3

from enum import Enum
import re
from typing import Any, Dict, List, Optional, Union, Tuple

RESERVED_FIELDS = {"metadata", "structure"}


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"


class FieldDescriptor:
    def __init__(self, data: Dict[str, Any], idx: int=0):

        self._data = data
        
        self.idx = idx
        self.field: str = data.get("field")
        self.fieldtype: Optional[FieldType] = self._get_fieldtype(data.get("fieldtype", "string"), strict=False)
        self.required: bool = data.get("required", True)
        self.default: Optional[Any] = data.get("default")
        self.pattern: Optional[str] = data.get("pattern")
        self.options: Optional[List[Any]] = data.get("options")
        self.description: Optional[str] = data.get("description")

        # Recursively load nested structure (only valid for list/dict)
        if self.fieldtype in ("list", "dict"):
            self.fields: List[FieldDescriptor] = [
                FieldDescriptor(fd) for fd in data.get("fields", [])
            ]
        else:
            self.fields = []

        self._validate()

    def is_fieldtype(self, value: Union[str, FieldType, Tuple[Union[str, FieldType], ...]]) -> bool:
        if isinstance(value, tuple):
            return any(self.is_fieldtype(v) for v in value)
        try:
            return self.fieldtype == self._get_fieldtype(value)
        except ValueError:
            return False
    
    def _get_fieldtype(self, value: Union[str, FieldType], strict: bool = True) -> Optional[FieldType]:
        if isinstance(value, FieldType):
            return value
        try:
            return FieldType(value)
        except ValueError as e:
            if strict:
                raise ValueError(f"Invalid fieldtype '{value}'") from e
        return None

    def _validate(self) -> None:
        if not self.field:
            raise ValueError(f"Field descriptor {self.idx} is invalid. The 'field' key was not set.")
        
        if self.field in RESERVED_FIELDS:
            raise ValueError(f"Field descriptor {self.idx} is invalid. '{self.field}' is a reserved name and cannot be used.")
        
        if not self.fieldtype:
            invalid = self._data.get("fieldtype")
            raise ValueError(f"Field descriptor {self.idx} is invalid. Invalid fieldtype '{invalid}'.")
        
        if self.pattern:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"Field descriptor {self.idx} is invalid. Invalid regex pattern '{e}'.")
            
        if self.fields and self.is_fieldtype((FieldType.LIST, FieldType.DICT)):
            raise ValueError(f"Field descriptor {self.idx} is invalid. Nested 'fields' only allowed for 'list' or 'dict' types ")
        
        if self.required and not isinstance(self.required, bool):
            raise ValueError(f"Field descriptor {self.idx} is invalid. The 'required' must be boolean.")

    def __repr__(self):
        return f"<FieldDescriptor: {self.field} (index={self.idx}, type={self.fieldtype}, required={self.required})>"
