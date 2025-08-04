#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Dict, Union, Iterable, Optional

from procdocs.core.schema.field_descriptor import FieldDescriptor
from procdocs.core.schema.metadata import DocumentSchemaMetadata
from procdocs.core.validation import ValidationResult


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
        """Returns the ordered structure of the schema as a dict of field descriptors."""
        return self._structure

    @property
    def schema_name(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.schema_name
        return None

    @property
    def format_version(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.format_version
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

        # Document Metadata
        ms._metadata = DocumentSchemaMetadata.from_dict(data.get("metadata", {}), strict=strict)

        # Document Schema Structure
        raw_structure = data.get("structure", [])
        field_descriptors = [FieldDescriptor.from_dict(fielddata, strict=strict) for fielddata in raw_structure]
        ms._structure = {idx: fd for idx, fd in enumerate(field_descriptors)}

        # Validate
        ms.validate(strict=strict)
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

    def validate(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        """
        Validates the full meta-schema:
        - Metadata section must contain required keys.
        - Structure must be well-formed and contain no duplicate field names.
        """
        collector = collector or ValidationResult()
        collector = self._validate_metadata(collector=collector, strict=strict)
        collector = self._validate_structure(collector=collector, strict=strict)
        return collector

    def _validate_metadata(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        if not isinstance(self.metadata, DocumentSchemaMetadata):
            msg = "The 'metadata' must be of type 'DocumentSchemaMetadata'"
            collector.report(msg, strict, TypeError)
        collector = self.metadata.validate(collector=collector, strict=strict)
        return collector

    def _validate_structure(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        """Validates the structure dictionary and each field descriptor."""
        collector = collector or ValidationResult()
        if not isinstance(self.structure, dict):
            msg = "The 'structure' must be a dict."
            collector.report(msg, strict, TypeError)
        collector = self._validate_field_descriptors(self.structure.values(), collector=collector, strict=strict)
        return collector

    def _validate_field_descriptors(self, descriptors: Iterable[FieldDescriptor], collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        """
        Recursively validates a collection of FieldDescriptors.

        Args:
            descriptors: Iterable of FieldDescriptor instances.

        Raises:
            ValueError: If duplicate fieldnames are found.
            TypeError: If non-descriptor items are present.
        """
        collector = collector or ValidationResult()
        fieldnames = []
        for fd in descriptors:
            if not isinstance(fd, FieldDescriptor):
                msg = "All structure entries must be FieldDescriptor instances"
                collector.report(msg, strict, TypeError)

            fieldnames.append(fd.fieldname)
            if fd.is_list() or fd.is_dict():
                self._validate_field_descriptors(fd.fields, collector=collector, strict=strict)

        if len(fieldnames) != len(set(fieldnames)):
            duplicates = [name for name in set(fieldnames) if fieldnames.count(name) > 1]
            msg = f"Duplicate field names found: {duplicates}"
            collector.report(msg, strict, ValueError)

        return collector
