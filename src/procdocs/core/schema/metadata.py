#!/usr/bin/env python3

from typing import Optional, List

from procdocs.core.base.base_metadata import BaseMetadata
from procdocs.core.utils import is_valid_version
from procdocs.core.validation import ValidationResult


class DocumentSchemaMetadata(BaseMetadata):
    """
    Metadata class for JSON document schemas.
    """
    _REQUIRED: List[str] = ["_schema_name"]
    _ATTRIBUTES: List[str] = ["_schema_name", "_schema_version"]

    def __init__(self):
        self._schema_name: Optional[str] = None
        self._schema_version: Optional[str] = None
        super().__init__()

    @property
    def schema_name(self) -> Optional[str]:
        return self._schema_name

    @schema_name.setter
    def schema_name(self, value: Optional[str]) -> None:
        self._validate_schema_name(value, strict=True)
        self._schema_name = value

    @property
    def schema_version(self) -> Optional[str]:
        return self._schema_version

    @schema_version.setter
    def schema_version(self, value: Optional[str]) -> None:
        self._schema_version = value

    @classmethod
    def from_dict(cls, data, strict = True) -> "DocumentSchemaMetadata":
        return super().from_dict(data, strict)
    
    def _validate_additional(self, collector, strict) -> ValidationResult:
        collector = collector or ValidationResult()
        collector = super()._validate_additional(collector, strict)
        collector = self._validate_schema_name(self.schema_name, collector, strict)
        return collector

    def _validate_schema_name(self, value: str, collector: ValidationResult = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        if value is None:
            msg = f"Invalid schema name: '{value}'"
            collector.report(msg, strict, ValueError)
        return collector
