#!/usr/bin/env python3

from enum import Enum
from typing import Union


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"
    INVALID = "invalid"

    @staticmethod
    def parse(value: Union[str, "FieldType"]) -> "FieldType":
        if isinstance(value, FieldType):
            return value
        try:
            return FieldType(str(value).lower().strip())
        except ValueError:
            return FieldType.INVALID
