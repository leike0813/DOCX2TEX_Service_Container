"""
Core infrastructure package for the docx2tex-service refactor.

Modules:
- config   : Environment and path configuration model.
- db       : SQLite connection and schema initialization helpers.
- models   : Pydantic domain models used across services.
- logging  : Lightweight console/file logging helpers consistent with server behavior.
- storage  : Filesystem utilities (atomic JSON write, safe filenames, file URIs, etc.).
"""

