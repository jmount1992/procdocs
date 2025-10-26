#!/usr/bin/env python3
"""
Purpose:
    Defines the FieldType enumeration for ProcDocs JSON document schemas,
    along with helpers for parsing, type mapping, and introspection of
    field types.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class FieldType(str, Enum):
    """
    Supported field types in a ProcDocs schema.

    - string  : textual scalar
    - number  : numeric scalar (int or float)
    - boolean : true/false scalar
    - list    : homogeneous list, may have nested item schema
    - dict    : mapping/object with named nested fields
    - enum    : string constrained to a fixed set of options
    - ref     : reference(s) to file paths and/or globs
    - invalid : unrecognized/unsupported type (returned by `parse`)
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"
    REF = "ref"
    INVALID = "invalid"

    # --- Parsing helpers --- #

    @classmethod
    def parse(cls, value: str | FieldType | None) -> FieldType:
        """
        Coerce arbitrary input to a `FieldType`.

        - `FieldType` instance → returned as-is
        - `None` or unknown strings → `FieldType.INVALID`
        - strings are trimmed and lowercased before lookup

        Examples
        --------
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
    def try_parse(cls, value: str | FieldType | None) -> FieldType | None:
        """
        Like `parse`, but returns `None` for unknowns instead of `FieldType.INVALID`.
        """
        ft = cls.parse(value)
        return None if ft is cls.INVALID else ft

    @classmethod
    def from_python_type(cls, t: type[Any]) -> FieldType:
        """
        Best-effort mapping from a Python type object to a `FieldType`.
        Unknowns -> `FieldType.INVALID`.
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
        """True if the field is a scalar (string, number, boolean, or enum)."""
        return self in {FieldType.STRING, FieldType.NUMBER, FieldType.BOOLEAN, FieldType.ENUM}

    def is_container(self) -> bool:
        """True if the field is a container (list or dict)."""
        return self in {FieldType.LIST, FieldType.DICT}

    def allows_children(self) -> bool:
        """True if nested content is allowed (list or dict)."""
        return self.is_container()

    def is_numeric(self) -> bool:
        """True if the field is numeric (`number`)."""
        return self is FieldType.NUMBER
