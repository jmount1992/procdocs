#!/usr/bin/env python3

from typing import Optional

from procdocs.core.base.base_metadata import BaseMetadata
from procdocs.core.utils import is_valid_version
from procdocs.core.validation import ValidationResult


class DocumentSchemaMetadata(BaseMetadata):
    """
    Metadata class for JSON document schemas.
    """

    def __init__(self):
        super().__init__()
        self._schema_name: Optional[str] = None
        self._schema_version: Optional[str] = None

    @property
    def schema_name(self) -> Optional[str]:
        return self._schema_name

    @schema_name.setter
    def schema_name(self, value: Optional[str]) -> None:
        self._schema_name = value

    @property
    def schema_version(self) -> Optional[str]:
        return self._schema_version

    @schema_version.setter
    def schema_version(self, value: Optional[str]) -> None:
        if value is not None and not is_valid_version(value):
            raise ValueError(f"Invalid schema version: '{value}'")
        self._schema_version = value

    @classmethod
    def from_dict(cls, data, strict = True) -> "DocumentSchemaMetadata":
        return super().from_dict(data, strict)
    
    def validate(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        collector = super().validate(collector=collector, strict=strict)
        if self.schema_version and not is_valid_version(str(self.schema_version)):
            msg = f"Invalid schema version: '{self.schema_version}'"
            collector.report(msg, strict, ValueError)
        return collector

    def _required(self):
        return ["schema_name", "format_version"]

    def _derived_attributes(self):
        return ["schema_name", "schema_version"]
