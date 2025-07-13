Meta-Schema Specification
=========================

Overview
--------

The ProcDocs **JSON meta-schema** defines the structure and constraints of a **YAML-based schema**.  
This YAML schema is used to validate a specific document type (e.g., test definitions, work instructions, calibration flows).  
The meta-schema enables rigorous schema validation, reuse of definitions, and format stability.

Each meta-schema consists of:

- A ``metadata`` block that provides identifying information about the schema.
- A ``structure`` block that defines one or more **field descriptors** for the target document format.

The meta-schema itself is stored in JSON. The YAML schemas it defines are used to validate YAML documents for your application domain.

Semantic Components
-------------------

**metadata**
    A dictionary that describes the schema file itself. It must contain the following fields:

    - ``schema_name`` (str):  
      A user-defined name for this document schema. This is used to identify the purpose of the schema (e.g., "test", "wi_section").

    - ``procdocs_format_version`` (str):  
      The version of the ProcDocs meta-schema format. This version determines which fields and rules are valid.
      Schemas using incompatible versions may not validate correctly.

    - ``schema_version`` (str, optional but recommended):  
      A user-defined version number for the document schema itself. This is **not used by ProcDocs**, but is included for version control and user-defined compatibility checks.

    Users may also define additional metadata fields to support their own tooling or documentation needs.

**structure**
    A list of field descriptors that define the structure and constraints of the YAML document.  
    Each descriptor defines one field in the target document and may contain type, validation rules, and nested subfields.

**field descriptor**
    A dictionary that defines the rules and expectations for a single field. Field descriptors are the building blocks of the document schema.

    Field descriptors may be flat (e.g., strings or numbers) or nested (e.g., dicts or lists of subfields).

Field Descriptor Attributes
---------------------------

Each field descriptor in ``structure`` may contain the following fields:

- ``field`` (str, **required**):  
  The name of the field in the YAML document. Must be unique at the same level.

- ``fieldtype`` (str, optional, defaults to ``string``):  
  The type of the field. Valid types are:

  - ``string`` — UTF-8 text
  - ``number`` — Integer or float
  - ``boolean`` — True or False
  - ``list`` — A list of nested field descriptors
  - ``dict`` — A mapping of named nested field descriptors
  - ``enum`` — A string restricted to a predefined set of options

- ``required`` (bool, optional, defaults to ``true``):  
  Whether the field must appear in the YAML document.

- ``description`` (str, optional):  
  A human-readable explanation of the field’s purpose.

- ``default`` (any, optional):  
  A default value to be used if the field is missing in the document.

- ``options`` (list of str, required if ``fieldtype`` is ``enum``):  
  A list of valid string values for enum fields.

- ``pattern`` (str, optional):  
  A regular expression constraint that applies to ``string`` fields.

- ``fields`` (list of field descriptors, required for ``list`` and ``dict`` types):  
  A list of nested fields that define the structure of compound types.

Reserved Field Names
--------------------

The following field names are reserved at the top level and cannot be used in a field descriptor:

- ``metadata``
- ``structure``
- ``contents``

Validation Rules
----------------

ProcDocs will validate that:

1. The ``metadata`` section exists and contains at least:
   - ``schema_name``
   - ``procdocs_format_version``
2. The ``structure`` section is a list of valid field descriptors.
3. All field names are unique at the same structure level.
4. ``fieldtype`` is one of the supported types.
5. ``options`` is defined for ``enum`` fields.
6. ``pattern`` is a valid regular expression if provided.
7. ``fields`` is only allowed for ``list`` and ``dict`` field types.

Example
-------

.. code-block:: json

    {
      "metadata": {
        "schema_name": "example",
        "schema_version": "0.1",
        "procdocs_format_version": "0.0.1"
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

