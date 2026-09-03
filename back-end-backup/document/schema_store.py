"""
SchemaStore — single source of truth for all document field schemas.

Replaces the direct file reads in field_extractor.load_schema() so that
schemas edited via PUT /schemas/{type} take effect immediately on the next
extraction call — no server restart required.

Storage: document/schemas/*.json (same folder, same files as before).
Custom schemas added via POST /schemas are also saved there as new JSON files.

Thread safety: a simple dict is sufficient for single-process uvicorn.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SCHEMA_DIR = Path(__file__).parent / "schemas"

# Valid field types accepted by the extractor
VALID_FIELD_TYPES = {"string", "date", "number", "boolean", "email", "phone"}


class SchemaStore:
    """
    In-memory cache of all document schemas, backed by JSON files.

    The store is populated lazily on first access and stays in sync
    with the file system — PUT/POST update both the dict and the file.
    """

    def __init__(self, schema_dir: Path = _SCHEMA_DIR):
        self._dir   = schema_dir
        self._cache: Dict[str, Dict[str, Any]] = {}   # key = normalised doc type
        self._loaded = False

    # ── Loading ────────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._load_all()

    def _load_all(self) -> None:
        """Read every *.json file in the schemas directory into the cache."""
        self._cache.clear()
        for path in sorted(self._dir.glob("*.json")):
            if path.stem == "document_types":
                continue  # Python constants file, not a schema
            try:
                schema = json.loads(path.read_text(encoding="utf-8"))
                doc_type = schema.get("document_type", "")
                if doc_type:
                    self._cache[self._key(doc_type)] = schema
            except Exception as e:
                logger.warning(f"Failed to load schema {path.name}: {e}")
        logger.info(f"SchemaStore loaded {len(self._cache)} schemas from {self._dir}")
        self._loaded = True

    def reload(self) -> None:
        """Force a reload from disk (useful after manual file edits)."""
        self._loaded = False
        self._load_all()

    # ── Public API ─────────────────────────────────────────────────────────

    def list_schemas(self) -> List[Dict[str, Any]]:
        """Return summary info for all schemas (doc_type + field count)."""
        self._ensure_loaded()
        return [
            {
                "document_type": s.get("document_type"),
                "description":   s.get("description", ""),
                "field_count":   len(s.get("fields", [])),
                "fields":        [
                    {"name": f.get("name"), "type": f.get("type"),
                     "required": f.get("required", False)}
                    for f in s.get("fields", [])
                ],
            }
            for s in self._cache.values()
        ]

    def get_schema(self, document_type: str) -> Optional[Dict[str, Any]]:
        """Return the full schema for a document type, or None if not found."""
        self._ensure_loaded()
        return self._cache.get(self._key(document_type))

    def update_schema(
        self,
        document_type: str,
        fields: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update (or create) the field list for an existing document type.
        Validates fields before saving — raises ValueError on bad input.

        Args:
            document_type: e.g. "Identity Proof"
            fields:        list of {"name", "type", "required"?, "description"?}
            description:   optional new description string

        Returns:
            The updated schema dict.
        """
        self._ensure_loaded()
        self._validate_fields(fields)

        key    = self._key(document_type)
        schema = self._cache.get(key)

        if schema is None:
            raise KeyError(
                f"Document type '{document_type}' not found. "
                "Use POST /schemas to add a new type."
            )

        # Merge: keep existing keys, update fields and optionally description
        schema["fields"] = fields
        if description is not None:
            schema["description"] = description

        self._save(schema)
        logger.info(f"Schema updated: {document_type} ({len(fields)} fields)")
        return schema

    def add_schema(
        self,
        document_type: str,
        fields: List[Dict[str, Any]],
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Add a brand-new custom document type + schema.
        Raises ValueError if the type already exists.

        Args:
            document_type: New type name, e.g. "Medical Record"
            fields:        list of {"name", "type", "required"?, "description"?}
            description:   human-readable description of the type

        Returns:
            The newly created schema dict.
        """
        self._ensure_loaded()
        self._validate_fields(fields)

        key = self._key(document_type)
        if key in self._cache:
            raise ValueError(
                f"Document type '{document_type}' already exists. "
                "Use PUT /schemas/{document_type} to update it."
            )

        schema = {
            "document_type": document_type,
            "description":   description,
            "fields":        fields,
        }
        self._cache[key] = schema
        self._save(schema)
        logger.info(f"New schema added: {document_type} ({len(fields)} fields)")
        return schema

    # ── Compatibility shim for field_extractor.load_schema() ───────────────

    def load_schema(self, document_type: str) -> Dict[str, Any]:
        """
        Drop-in replacement for the original load_schema() function.
        Returns {"fields": [...]} — same shape as before.
        """
        schema = self.get_schema(document_type)
        if schema is None:
            logger.warning(f"Schema not found for document type: {document_type}")
            return {"fields": []}
        return schema

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _key(document_type: str) -> str:
        """Normalise a document type name to a stable dict key."""
        return document_type.strip().lower()

    def _save(self, schema: Dict[str, Any]) -> None:
        """Write a schema back to its JSON file."""
        filename = self._type_to_filename(schema["document_type"])
        path     = self._dir / filename
        try:
            path.write_text(
                json.dumps(schema, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"Schema saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save schema to {path}: {e}")
            raise

    @staticmethod
    def _type_to_filename(document_type: str) -> str:
        """Convert 'Identity Proof' → 'identity_proof.json'."""
        return re.sub(r"[^a-z0-9]+", "_", document_type.strip().lower()) + ".json"

    @staticmethod
    def _validate_fields(fields: List[Dict[str, Any]]) -> None:
        """
        Validate that a field list is well-formed.
        Raises ValueError with a descriptive message on the first bad field.
        """
        if not isinstance(fields, list):
            raise ValueError("'fields' must be a list.")
        if len(fields) == 0:
            raise ValueError("Schema must have at least one field.")

        seen_names: set = set()
        for i, field in enumerate(fields):
            if not isinstance(field, dict):
                raise ValueError(f"Field {i} is not an object.")

            name = field.get("name", "").strip()
            if not name:
                raise ValueError(f"Field {i} is missing a 'name'.")
            if name in seen_names:
                raise ValueError(f"Duplicate field name '{name}' at index {i}.")
            seen_names.add(name)

            ftype = field.get("type", "").strip().lower()
            if not ftype:
                raise ValueError(f"Field '{name}' is missing a 'type'.")
            if ftype not in VALID_FIELD_TYPES:
                raise ValueError(
                    f"Field '{name}' has invalid type '{ftype}'. "
                    f"Valid types: {sorted(VALID_FIELD_TYPES)}"
                )


# Shared singleton — import this everywhere
schema_store = SchemaStore()
