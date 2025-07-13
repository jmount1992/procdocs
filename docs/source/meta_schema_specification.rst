JSON Meta-Schema Specification
==============================

Overview
--------

The ProcDocs **JSON meta-schema** defines the structure and constraints of a **YAML document-schema**.  
This YAML schema is then used to validate a **specific document type**, such as a unit test definition or a modular work instruction.

This two-layer system ensures flexibility and strong validation:
- The **meta-schema** is written in JSON and describes valid YAML schema files.
- Each YAML schema file then describes a category of documents (e.g. unit test, work instructions).
- The actual documents are validated against these YAML schema files.

This separation enables reusable tooling, centralized schema validation, and document-specific constraints.

Semantic Components
-------------------

A valid meta-schema consists of two top-level fields: ``metadata`` and ``structure``.

**metadata**
    A dictionary that describes the meta-information about the schema itself.  
    It must contain the following keys:
    
    - ``filetype``: A string identifier for the type of document (e.g., "unit_test_schema").
    - ``meta_schema_version``: A version string indicating which version of the meta-schema this follows.

**structure**
    A list of field descriptors that define the fields, types, constraints, and nesting of the target YAML document.  
    Each entry in ``structure`` must be a valid **field descriptor**.

**field descriptor**
    A dictionary that defines the behavior and constraints of a single field in the target YAML schema.  
    Field descriptors can represent primitive values, enums, or compound types (lists and dicts), and may be nested recursively.

Each field descriptor may contain the following fields:

Field Descriptor Attributes
---------------------------

These are the valid fields for each Field Descriptor:

- ``fieldname`` (str, **required**):  
  The name of the field in the YAML document. This must be unique at each structure level and must not conflict with reserved keywords.

- ``fieldtype`` (str, optional, defaults to ``string``):  
  The type of the field. Must be one of:

  - ``string`` — UTF-8 text
  - ``number`` — Integer or float
  - ``boolean`` — True/False
  - ``list`` — List of subfields (requires a ``fields`` list)
  - ``dict`` — Mapping of named subfields (requires a ``fields`` list)
  - ``enum`` — String restricted to a set of predefined ``options``

- ``required`` (bool, optional, defaults to ``true``):  
  Whether this field must appear in a valid document.

- ``description`` (str, optional):  
  A human-readable description of the field and its purpose.

- ``default`` (any, optional):  
  A default value for the field, if not provided in the document.

- ``options`` (list of str, required if ``fieldtype`` is ``enum``):  
  Defines the valid values if the field is of type ``enum``.

- ``pattern`` (str, optional):  
  A regex string that applies to ``string`` fields. If specified, all values must match the pattern.

- ``fields`` (list of field descriptors, required for ``list`` or ``dict`` types):  
  A nested list of subfields. Only valid when ``fieldtype`` is ``list`` or ``dict``.

Reserved Field Names
--------------------

The following field names are reserved and cannot be used in any structure definition:

- ``metadata``
- ``structure``

Validation Rules
----------------

A meta-schema is only valid if all of the following hold:

1. The ``metadata`` section exists and contains ``filetype`` and ``meta_schema_version``.
2. The ``structure`` section is a list of valid field descriptors.
3. Each ``fieldname`` is unique at each level.
4. ``fieldtype`` is one of the valid types listed above.
5. ``options`` must be present and non-empty if ``fieldtype`` is ``enum``.
6. ``pattern``, if present, must be a valid regex.
7. The ``fields`` property may only be used when ``fieldtype`` is ``list`` or ``dict``.

Example
-------

.. code-block:: json

    {
      "metadata": {
        "filetype": "unit_test_schema",
        "meta_schema_version": "1.0"
      },
      "structure": [
        {
          "field": "id",
          "fieldtype": "string",
          "required": true,
          "pattern": "^[A-Z]{3}-\\d{3}$",
          "description": "The test identifier."
        },
        {
          "field": "steps",
          "fieldtype": "list",
          "fields": [
            {
              "field": "step-number",
              "fieldtype": "number"
            },
            {
              "field": "step",
              "fieldtype": "string"
            }
          ]
        }
      ]
    }

