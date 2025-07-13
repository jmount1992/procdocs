Introduction and Overview
=========================

.. toctree::

ProcDocs is a lightweight, schema-driven framework for authoring, validating, and rendering procedure-based documents (e.g., Standard Operating Procedures, Work Instructions, Manual Test Suites, etc.). 
It was designed to support modular, DRY (Don't Repeat Yourself) principles and promote reuse across rendered documents. 
ProcDocs separates document structure (schema), contents (documents), and presentation (templates) for clarity and long-term maintainability.

.. Core Concepts:
.. --------------
.. - **Document Schema**: Defines the allowed structure and constraints of a document type.
.. - **Document**: A YAML file representing a concrete document instance.
.. - **Render Template**: A Jinja2 HTML template defining how a validated document should be presented.


Design Philosophy
-----------------

ProcDocs is built on the following principles:

- **Separation of Concerns**: Clear boundaries between structure (schema), content (document), and format (template).
- **Modularity**: Support for referencing and reusing document components.
- **Validation**: Rigorous schema-based validation to ensure correctness.
- **Extensibility**: Designed to support additional formats and schemas all without requiring technical know how.
- **Version Control Friendly**: All inputs are text-based and easily diffable.

This makes ProcDocs suitable for use in a range of environments.

