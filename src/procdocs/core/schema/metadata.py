#!/usr/bin/env python3

from typing import Dict, Optional

from procdocs.core.base_metadata import BaseMetadata
from procdocs.core.utils import is_valid_version


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

    def _required(self):
        return ["schema_name", "format_version"]

    def _derived_attributes(self):
        return ["schema_name", "schema_version"]
