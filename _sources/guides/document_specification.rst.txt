Document Specification
======================

.. toctree::

Overview
--------

A **Document** is a YAML file that conforms to a ProcDocs **Document Schema**.  
It contains structured metadata and user-defined content, validated against a schema definition.

Documents are designed to be simple, human-readable, and version-controlled.  
Each document must declare its intended schema and versioning information in the metadata.

Components
----------

A Document must contain two top-level blocks:

- ``metadata``: Provides context and identity for the document.
- ``contents``: The actual data, which is validated against the schema defined by ``document_type``.

Metadata Fields
---------------

- ``document_type`` (str):  
  Must match the ``schema_name`` of the schema used to validate this document.

- ``document_version`` (str):  
  A user-defined version for this document. Not interpreted by ProcDocs, but useful for change tracking.

- ``format_version`` (str):  
  Specifies the version of the ProcDocs document format used by the document.

Users may define additional metadata fields as needed (e.g., ``author``, ``date_created``).

Contents
--------

The ``contents`` block must exactly match the field structure defined in the associated Document Schema.  
It may include nested lists, dictionaries, or referenced includes, depending on the schema.

Example
-------

Below is a minimal example of a document schema and a document that conforms to it.

**Example Schema** (JSON):

.. code-block:: json

   {
     "metadata": {
       "schema_name": "simple_note",
       "schema_version": "1.0",
       "format_version": "0.0.1"
     },
     "structure": [
       { "field": "title", "fieldtype": "string", "required": true },
       { "field": "note", "fieldtype": "string", "required": true }
     ]
   }

**Example Document** (YAML):

.. code-block:: yaml

   metadata:
     document_type: simple_note
     document_version: "1.0"
     format_version: "0.0.1"

   contents:
     title: Startup Safety Notes
     note: Always check e-stop before enabling motors.

