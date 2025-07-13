#!/usr/bin/env python3

from enum import Enum
from typing import Union


class FieldType(str, Enum):
    """
    Enum representing the supported field types in a meta-schema.

    Supported types:
    - STRING: A text string.
    - NUMBER: A numerical value (int or float).
    - BOOLEAN: A true/false value.
    - LIST: A list of nested fields.
    - DICT: A dictionary of named nested fields.
    - ENUM: A string constrained to a fixed set of options.
    - INVALID: An invalid or unrecognized type.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"
    INVALID = "invalid"

    @staticmethod
    def parse(value: Union[str, "FieldType"]) -> "FieldType":
        """
        Parse a string or FieldType into a valid FieldType enum value.

        Args:
            value (Union[str, FieldType]): The raw fieldtype as a string or FieldType.

        Returns:
            FieldType: A valid FieldType enum member. If parsing fails, returns FieldType.INVALID.
        """
        if isinstance(value, FieldType):
            return value
        try:
            return FieldType(str(value).lower().strip())
        except ValueError:
            return FieldType.INVALID
