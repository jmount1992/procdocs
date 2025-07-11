import json
from pathlib import Path
from typing import Dict, List, Union

from .field_descriptor import FieldDescriptor


class MetaSchema:
    def __init__(self, structure: List[Dict], metadata: Dict):
        self._metadata = metadata
        self._structure: Dict[int, FieldDescriptor] = {idx: FieldDescriptor(fd, idx) for idx, fd in enumerate(structure)}

        self._validate()

    @property
    def metadata(self) -> Dict:
        return self._metadata

    @property
    def structure(self) -> Dict[int, FieldDescriptor]:
        return self._structure

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> "MetaSchema":
        if not isinstance(filepath, (str, Path)):
            raise TypeError(f"The filepath argument must be of type Path or str, not '{type(filepath)}'")
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"The file '{filepath}' does not exist")

        with filepath.open('r') as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        structure = data.get("structure", [])

        return cls(structure=structure, metadata=metadata)

    def _validate(self) -> None:
        self._validate_metadata()
        self._validate_structure()

    def _validate_metadata(self) -> None:
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        required_keys = ("filetype", "meta_schema_version")
        for key in required_keys:
            if key not in self.metadata:
                raise ValueError(f"Metadata must contain '{key}'")

    def _validate_structure(self) -> None:
        if not isinstance(self.structure, dict):
            raise ValueError("'structure' must be a list")

        seen_fields = set()
        for fd in self.structure.values():
            if not isinstance(fd, FieldDescriptor):
                raise TypeError("All structure entries must be FieldDescriptor instances")

            if fd.field in seen_fields:
                raise ValueError(f"Duplicate field name: '{fd.field}'")

            seen_fields.add(fd.field)


