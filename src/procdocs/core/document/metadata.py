#!/usr/bin/env python3

from typing import Optional, Dict

from procdocs.core.base_metadata import BaseMetadata
from procdocs.core.utils import is_valid_version


class DocumentMetadata(BaseMetadata):
    """
    Metadata class for YAML document instances.
    """

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
        if value is not None and not is_valid_version(value):
            raise ValueError(f"Invalid document version: '{value}'")
        self._document_version = value

    def _required(self):
        return ["document_type", "format_version"]

    def _derived_attributes(self):
        return ["document_type", "document_version"]
