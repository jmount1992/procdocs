#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Dict, Union, Iterable, Optional

from procdocs.core.field_descriptor import FieldDescriptor
from procdocs.core.metadata import BaseMetadata
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

    def to_dict(self) -> Dict[str, str]:
        data = super().to_dict()
        data["schema_name"] = self.schema_name
        data["schema_version"] = self.schema_version
        return data

    def _required(self):
        return ("schema_name", "format_version")


class DocumentSchema:
    """
    Represents a meta-schema that defines the structure of document instances.

    A meta-schema includes required metadata and a structure defining the shape of a document instance.
    """

    def __init__(self):
        """
        Initializes an empty MetaSchema. Use `from_dict()` or `from_file()` to load data.
        """
        self._metadata: DocumentSchemaMetadata = DocumentSchemaMetadata()
        self._structure: Optional[Dict[int, FieldDescriptor]] = None

    @property
    def metadata(self) -> DocumentSchemaMetadata:
        """Returns the metadata dictionary for the schema."""
        return self._metadata

    @property
    def structure(self) -> Dict[int, FieldDescriptor]:
        """Returns the ordered structure of the schema as a dict of meta field descriptors."""
        return self._structure

    @property
    def schema_name(self) -> Optional[str]:
        if self.metadata:
            return self.metadata["schema_name"]
        return None

    @property
    def version(self) -> Optional[str]:
        if self.metadata:
            return self.metadata["meta_schema_version"]
        return None

    @classmethod
    def from_dict(cls, data: Dict, strict: bool = True) -> "DocumentSchema":
        """
        Loads a DocumentSchema from a dictionary.

        Args:
            data (Dict): The raw JSON-like structure.
            strict (bool): If True, validates the structure after loading.

        Returns:
            DocumentSchema: A fully parsed schema instance.
        """
        ms = cls()
        ms._metadata = DocumentSchemaMetadata.from_dict(data.get("metadata", {}))
        raw_structure = data.get("structure", [])
        field_descriptors = [FieldDescriptor.from_dict(fielddata) for fielddata in raw_structure]
        ms._structure = {idx: fd for idx, fd in enumerate(field_descriptors)}
        if strict:
            ms.validate()
        return ms

    @classmethod
    def from_file(cls, filepath: Union[str, Path], strict: bool = True) -> "DocumentSchema":
        """
        Loads a DocumentSchema from a JSON file.

        Args:
            filepath (str or Path): Path to a schema JSON file.
            strict (bool): If True, validates after loading.

        Returns:
            DocumentSchema: Loaded schema.

        Raises:
            FileNotFoundError: If the file does not exist.
            TypeError: If the filepath is of an incorrect type.
        """
        if not isinstance(filepath, (str, Path)):
            raise TypeError(f"The filepath argument must be of type Path or str, not '{type(filepath)}'")
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"The file '{filepath}' does not exist")

        with filepath.open('r') as f:
            data = json.load(f)

        return cls.from_dict(data, strict)

    def validate(self) -> None:
        """
        Validates the full meta-schema:
        - Metadata section must contain required keys.
        - Structure must be well-formed and contain no duplicate field names.
        """
        self.metadata.validate()
        self._validate_structure()

    def _validate_metadata(self) -> None:
        """Validates the metadata dictionary, checking for required fields."""
        if not isinstance(self.metadata, dict):
            raise ValueError("The 'metadata' must be a dictionary")

        required_keys = ("schema_name", "meta_schema_version")
        for key in required_keys:
            if key not in self.metadata:
                raise ValueError(f"Metadata must contain '{key}'")

    def _validate_structure(self) -> None:
        """Validates the structure dictionary and each field descriptor."""
        if not isinstance(self.structure, dict):
            raise ValueError("The 'structure' must be a dict.")

        self._validate_field_descriptors(self.structure.values())

    def _validate_field_descriptors(self, descriptors: Iterable[FieldDescriptor]) -> None:
        """
        Recursively validates a collection of FieldDescriptors.

        Args:
            descriptors: Iterable of FieldDescriptor instances.

        Raises:
            ValueError: If duplicate fieldnames are found.
            TypeError: If non-descriptor items are present.
        """
        fieldnames = []
        for fd in descriptors:
            if not isinstance(fd, FieldDescriptor):
                raise TypeError("All structure entries must be FieldDescriptor instances")

            fieldnames.append(fd.fieldname)
            if fd.is_list() or fd.is_dict():
                self._validate_field_descriptors(fd.fields)

        if len(fieldnames) != len(set(fieldnames)):
            duplicates = [name for name in set(fieldnames) if fieldnames.count(name) > 1]
            raise ValueError(f"Duplicate field names found: {duplicates}")
