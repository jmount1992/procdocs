#!/usr/bin/env python3

from typing import Optional, List, Dict, Any, Callable

from procdocs.core.base.base import Base
from procdocs.core.validation import ValidationResult
from procdocs.core.utils import is_strict_semver


class BaseMetadata(Base):
    """
    Base class for document and schema metadata.
    Stores document type, version, and format version, with validation.
    Additionally stores user-defined metadata information as attributes.
    """
    _ATTRIBUTES: List[str] = ["_format_version"]
    _REQUIRED: List[str] = ["_format_version"]

    def __init__(self):
        self._format_version: Optional[str] = None
        super().__init__()

    @property
    def format_version(self) -> Optional[str]:
        return self._format_version

    @format_version.setter
    def format_version(self, value: str) -> None:
        self._validate_format_version(value)
        self._format_version = value

    @classmethod
    def from_dict(cls, data: Dict, strict: bool = True):
        return super().from_dict(data, strict)

    def _validate_additional(self, collector, strict) -> ValidationResult:
        collector = collector or ValidationResult()
        collector = self._validate_format_version(self.format_version, collector=collector, strict=strict)
        return collector

    def _validate_format_version(self, value: str, collector: ValidationResult = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        if not is_strict_semver(str(value)):
            msg = f"Invalid format version: '{value}'"
            collector.report(msg, strict, ValueError)
        return collector
