#!/usr/bin/env python3
from __future__ import annotations

from enum import Enum
from typing import Optional, Type, Union


class FieldType(str, Enum):
    """
    Supported field types in a ProcDocs meta‑schema.

    - string   : textual scalar
    - number   : numeric scalar (int or float)
    - boolean  : true/false scalar
    - list     : homogeneous list, may have nested `fields` describing the element
    - dict     : mapping/object with named nested `fields`
    - enum     : string constrained to a fixed set of options
    - invalid  : unrecognized type (returned by `parse`)
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"
    INVALID = "invalid"

    # --- Parsing helpers --- #

    @classmethod
    def parse(cls, value: Union[str, "FieldType", None]) -> "FieldType":
        """
        Coerce arbitrary input to a FieldType. Unknowns -> FieldType.INVALID.

        Examples:
            >>> FieldType.parse(" String ")
            <FieldType.STRING: 'string'>
            >>> FieldType.parse(None)
            <FieldType.INVALID: 'invalid'>
            >>> FieldType.parse("foo")
            <FieldType.INVALID: 'invalid'>
        """
        if isinstance(value, FieldType):
            return value
        if value is None:
            return cls.INVALID
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return cls.INVALID

    @classmethod
    def try_parse(cls, value: Union[str, "FieldType", None]) -> Optional["FieldType"]:
        """
        Like parse(), but returns None for unknowns instead of FieldType.INVALID.
        Useful when you want to branch on 'known vs unknown' without carrying INVALID.
        """
        ft = cls.parse(value)
        return None if ft is cls.INVALID else ft

    @classmethod
    def from_python_type(cls, t: Type) -> "FieldType":
        """
        Best-effort mapping from a Python type object to a FieldType.
        Unknowns -> FieldType.INVALID.
        """
        if t is str:
            return cls.STRING
        if t in (int, float):
            return cls.NUMBER
        if t is bool:
            return cls.BOOLEAN
        if t is list:
            return cls.LIST
        if t is dict:
            return cls.DICT
        return cls.INVALID

    # --- Introspection helpers --- #

    def is_scalar(self) -> bool:
        """True for string/number/boolean/enum."""
        return self in {FieldType.STRING, FieldType.NUMBER, FieldType.BOOLEAN, FieldType.ENUM}

    def is_container(self) -> bool:
        """True for list/dict."""
        return self in {FieldType.LIST, FieldType.DICT}

    def allows_children(self) -> bool:
        """True when nested `fields` are allowed (list/dict)."""
        return self.is_container()

    def is_numeric(self) -> bool:
        """True when the field is numeric (number)."""
        return self is FieldType.NUMBER
