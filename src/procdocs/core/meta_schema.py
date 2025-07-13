#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Dict, Union, Iterable, Optional

from .field_descriptor import FieldDescriptor


class MetaSchema:

    def __init__(self):
        self._metadata: Optional[Dict] = None
        self._structure: Optional[Dict[int, FieldDescriptor]] = None

    @property
    def metadata(self) -> Dict:
        return self._metadata

    @property
    def structure(self) -> Dict[int, FieldDescriptor]:
        return self._structure

    @classmethod
    def from_dict(cls, data: Dict, strict: bool = True) -> "MetaSchema":
        ms = cls()
        ms._metadata = data.get("metadata", {})
        raw_structure = data.get("structure", [])
        field_descriptors = [FieldDescriptor.from_dict(fielddata) for fielddata in raw_structure]
        ms._structure = {idx: fd for idx, fd in enumerate(field_descriptors)}
        if strict:
            ms.validate()
        return ms

    @classmethod
    def from_file(cls, filepath: Union[str, Path], strict: bool = True) -> "MetaSchema":
        if not isinstance(filepath, (str, Path)):
            raise TypeError(f"The filepath argument must be of type Path or str, not '{type(filepath)}'")
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"The file '{filepath}' does not exist")

        with filepath.open('r') as f:
            data = json.load(f)

        return cls.from_dict(data, strict)

    def validate(self) -> None:
        self._validate_metadata()
        self._validate_structure()

    def _validate_metadata(self) -> None:
        if not isinstance(self.metadata, dict):
            raise ValueError("The 'metadata' must be a dictionary")

        required_keys = ("filetype", "meta_schema_version")
        for key in required_keys:
            if key not in self.metadata:
                raise ValueError(f"Metadata must contain '{key}'")

    def _validate_structure(self) -> None:
        if not isinstance(self.structure, dict):
            raise ValueError("The 'structure' must be a dict.")

        self._validate_field_descriptors(self.structure.values())

    def _validate_field_descriptors(self, descriptors: Iterable[FieldDescriptor]) -> None:
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
