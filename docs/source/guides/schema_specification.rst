Document Schema Specification
=============================

.. toctree::

Overview
--------

A **Document Schema** defines the structure, constraints, and validation rules for a specific type of document in the ProcDocs framework.

Schemas are written in **JSON** and are used to validate structured YAML documents such as unit tests, composite test plans, and work instruction sections.

Components
----------

Each schema consists of:

- ``metadata``: Provides identifying information about the schema.
- ``structure``: Defines the fields expected in validated documents, using field descriptors.

Metadata Fields
---------------

- ``schema_name`` (str):  
  A user-defined name for this schema (e.g., ``test``, ``wi_section``, ``test_document``).  
  Documents that use this schema must set `document_type` to match this value.

- ``schema_version`` (str):  
  A user-defined version number for the schema itself. Used for tracking and change control.

- ``format_version`` (str):  
  The version of the ProcDocs document schema format this file conforms to (e.g., ``0.0.1``).

Additional metadata fields (e.g., ``author``, ``description``) may be included if needed.

Structure Block
---------------

The ``structure`` block is a list of **field descriptors**, each of which defines a single field that may appear in validated documents.

Field descriptors may represent:

- Flat fields (e.g., strings, numbers)
- Nested structures (e.g., lists or dictionaries of subfields)

Field Descriptor Attributes
---------------------------

Each descriptor in ``structure`` may contain the following keys:

- ``fieldname`` (str, **required**):  
  The field name as it will appear in the document. Must be unique at the same nesting level.

- ``fieldtype`` (str, optional, defaults to ``string``):  
  The expected type of this field. Supported values:

  - ``string`` — UTF-8 text
  - ``number`` — Integer or float
  - ``boolean`` — True or False
  - ``enum`` — A string constrained to predefined values
  - ``list`` — A list of nested subfields
  - ``dict`` — A dictionary with named nested subfields

- ``required`` (bool, optional, default: true):  
  Whether this field must appear in a document that uses this schema.

- ``description`` (str, optional):  
  A human-readable description of the field.

- ``default`` (any, optional):  
  A default value to be applied if the field is missing and not required.

- ``options`` (list of str, required if ``fieldtype`` is ``enum``):  
  Valid values for enum-type fields.

- ``pattern`` (str, optional):  
  Regular expression constraint for string-type fields.

- ``fields`` (list of field descriptors, required for ``list`` and ``dict`` types):  
  Describes the nested structure of compound types.

Reserved Field Names
--------------------

The following field names are reserved and **cannot** be used as `fieldname` values within the schema's structure:

- ``metadata``
- ``structure``
- ``contents``

Validation Rules
----------------

ProcDocs will validate that:

1. The top-level schema includes both ``metadata`` and ``structure`` blocks.
2. ``metadata`` includes:
   - ``schema_name``
   - ``format_version``
3. ``structure`` is a list of valid field descriptors.
4. Each field descriptor:
   - Has a unique ``fieldname`` at its level
   - Uses a valid ``fieldtype``
   - If ``fieldtype`` is ``enum``, includes a non-empty ``options`` list
   - If ``pattern`` is used, it applies only to string fields and is a valid regex
   - If ``fields`` is used, the ``fieldtype`` must be ``list`` or ``dict``
5. Reserved field names are not used.

Example
-------

The following schema defines a simple `test` document with two fields: an ID and a list of steps.

.. code-block:: json

    {
      "metadata": {
        "schema_name": "test",
        "schema_version": "0.1",
        "format_version": "0.0.1"
      },
      "structure": [
        {
          "fieldname": "id",
          "fieldtype": "string",
          "required": true,
          "pattern": "^[A-Z]{3}-\\d{3}$",
          "description": "The test identifier."
        },
        {
          "fieldname": "steps",
          "fieldtype": "list",
          "fields": [
            {
              "fieldname": "step-number",
              "fieldtype": "number"
            },
            {
              "fieldname": "step",
              "fieldtype": "string"
            }
          ]
        }
      ]
    }

