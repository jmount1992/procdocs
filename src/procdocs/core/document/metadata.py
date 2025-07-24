#!/usr/bin/env python3

from typing import Optional, List

from procdocs.core.base.base_metadata import BaseMetadata
from procdocs.core.utils import is_valid_version
from procdocs.core.validation import ValidationResult


class DocumentMetadata(BaseMetadata):
    """
    Metadata class for YAML document instances.
    """
    _REQUIRED: List[str] = ["_document_type"]
    _ATTRIBUTES: List[str] = ["_document_type", "_document_version"]

    def __init__(self):
        super().__init__()
        self._document_type: Optional[str] = None
        self._document_version: Optional[str] = None

    @property
    def document_type(self) -> Optional[str]:
        return self._document_type

    @document_type.setter
    def document_type(self, value: Optional[str]) -> None:
        self._document_type = value

    @property
    def document_version(self) -> Optional[str]:
        return self._document_version

    @document_version.setter
    def document_version(self, value: Optional[str]) -> None:
        self._document_version = value

    @classmethod
    def from_dict(cls, data, strict = True) -> "DocumentMetadata":
        return super().from_dict(data, strict)
    
    def _validate_additional(self, collector, strict) -> ValidationResult:
        collector = collector or ValidationResult()
        collector = super()._validate_additional(collector, strict)
        return collector
