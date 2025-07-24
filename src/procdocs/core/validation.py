#!/usr/bin/env python3

from typing import List


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []

    def add(self, message: str):
        self.errors.append(message)

    def report(self, msg: str, strict: bool = False, exc_type: type = ValueError):
        """
        Add an error to the result, or raise an exception if in strict mode.

        Args:
            msg (str): The error message.
            strict (bool): Whether to raise immediately.
            exc_type (type): Exception type to raise if strict. Default is ValueError.
        """
        if strict:
            raise exc_type(msg)
        self.add(msg)

    def is_valid(self) -> bool:
        return not self.errors

    def __len__(self):
        return len(self.errors)

    def __iter__(self):
        return iter(self.errors)

    def __repr__(self):
        return f"<ValidationResult valid={self.is_valid()} errors={len(self.errors)}>"