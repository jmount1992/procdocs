#!/usr/bin/env python3

from typing import Optional, Dict, List

from procdocs.core.utils import is_strict_semver, is_valid_version


class CommonMetadata:
    """
    Represents shared metadata fields between meta-schemas and document instances.
    Includes fields for document/document_type, version, and format compatibility.
    """

    # __slots__ = ("_document_type", "_document_version", "_format_version")

    def __init__(self) -> None:
        self._document_type: Optional[str] = None
        self._document_version: Optional[str] = None
        self._format_version: Optional[str] = None
        self._user_defined: List[str] = []

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
            raise ValueError(f"The supplied document version '{value}' is invalid.")
        self._document_version = value

    @property
    def format_version(self) -> Optional[str]:
        return self._format_version

    @format_version.setter
    def format_version(self, value: str) -> None:
        if not is_strict_semver(value):
            raise ValueError(f"The supplied ProcDocs format version '{value}' is invalid.")
        self._format_version = value

    def to_dict(self) -> Dict:
        data = {
            "document_type": self.document_type,
            "document_version": self.document_version,
            "format_version": self.format_version,
        }
        return data

    def _load_from_dict(self, data: Dict, mapping: Dict[str, str] = None) -> None:
        for key, val in data.items():
            key = str(key).replace('-', '_')
            attr = mapping.get(key, key)
            if not hasattr(self, attr):
                self._user_defined.append(attr)
            setattr(self, attr, val)

    def _validate_required(self, required: tuple[str], mapping: Dict[str, str]) -> None:
        for key in required:
            attr = mapping.get(key, key)
            if getattr(self, attr, None) is None:
                raise ValueError(f"Missing required metadata field: '{key}'")
