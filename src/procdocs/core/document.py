#!/usr/bin/env python3

import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import yaml

from procdocs.core.metadata import BaseMetadata
from procdocs.core.document_schema import DocumentSchema
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

    def to_dict(self) -> Dict[str, str]:
        data = super().to_dict()
        data["document_type"] = self.document_type
        data["document_version"] = self.document_version
        return data

    def _required(self):
        return ("document_type", "format_version")


class Document:

    def __init__(self, schema: DocumentSchema):
        self._schema = schema
        self._metadata: Optional[DocumentMetadata] = None
        self._contents: Optional[Dict] = None

    @property
    def schema(self) -> DocumentSchema:
        return self._schema

    @property
    def metadata(self) -> DocumentMetadata:
        return self._metadata

    @property
    def contents(self) -> Dict:
        return self._contents

    @classmethod
    def from_dict(cls, data: Dict, schema: DocumentSchema) -> "Document":
        doc = cls(schema)
        doc._metadata = DocumentMetadata.from_dict(data.get("metadata", {}))
        doc._contents = data.get("contents", {})
        return doc

    @classmethod
    def from_file(cls, filepath: Path, schema: DocumentSchema) -> "Document":
        if not isinstance(filepath, (str, Path)):
            raise TypeError(f"The filepath argument must be of type Path or str, not '{type(filepath)}'")
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"The file '{filepath}' does not exist")

        with filepath.open('r') as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data, schema)

    def validate(self) -> list[str]:
        """
        Validates the document instance against its associated schema.

        Returns:
            A list of error strings, where each entry describes a validation issue.
        """
        errors = []

        if self._metadata is None or self._contents is None:
            return ["Document is missing metadata or contents section"]

        # Validate metadata
        try:
            self._metadata.validate()
        except Exception as e:
            errors.append(f"Metadata validation failed: {e}")

        def validate_field(desc, value, path):
            fieldname = desc.fieldname or "<unnamed>"
            full_path = ".".join(path + [fieldname])

            if value is None:
                if desc.required:
                    errors.append(f"{full_path}: Missing required field")
                return

            if desc.is_list():
                if not isinstance(value, list):
                    errors.append(f"{full_path}: Expected list but got {type(value).__name__}")
                    return
                for i, item in enumerate(value):
                    if not isinstance(item, dict):
                        errors.append(f"{full_path}[{i}]: Expected dict items in list")
                        continue
                    for subdesc in desc.fields:
                        validate_field(subdesc, item.get(subdesc.fieldname), path + [f"{fieldname}[{i}]"])

            elif desc.is_dict():
                if not isinstance(value, dict):
                    errors.append(f"{full_path}: Expected dict but got {type(value).__name__}")
                    return
                for subdesc in desc.fields:
                    validate_field(subdesc, value.get(subdesc.fieldname), path + [fieldname])

            else:
                if desc.pattern:
                    val_str = str(value)
                    if not re.match(desc.pattern, val_str):
                        errors.append(f"{full_path}: Value '{val_str}' does not match pattern '{desc.pattern}'")

                if desc.fieldtype.name == "NUMBER":
                    if not isinstance(value, (int, float)):
                        errors.append(f"{full_path}: Expected number but got {type(value).__name__}")

        for desc in self._schema.structure.values():
            value = self._contents.get(desc.fieldname)
            if value is None and desc.default is not None:
                value = desc.default
            validate_field(desc, value, [])

        return errors
