"""
Schema management endpoints — Phase 7

GET  /schemas                  — list all document types + their field schemas
GET  /schemas/{document_type}  — get one schema
PUT  /schemas/{document_type}  — update a schema's fields (admin only)
POST /schemas                  — add a brand-new document type (admin only)

PUT and POST validate input before saving so a malformed schema can never
silently break field extraction for that document type.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from auth.auth import UserInfo, get_current_user, require_admin
from document.schema_store import schema_store, VALID_FIELD_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schemas", tags=["Document Schemas"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FieldDefinition(BaseModel):
    name:        str  = Field(..., min_length=1, description="Field name (snake_case)")
    type:        str  = Field(..., description=f"One of: {sorted(VALID_FIELD_TYPES)}")
    description: str  = Field(default="", description="Human-readable description")
    required:    bool = Field(default=False)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_FIELD_TYPES:
            raise ValueError(
                f"Invalid field type '{v}'. "
                f"Must be one of: {sorted(VALID_FIELD_TYPES)}"
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field name cannot be empty.")
        return v


class UpdateSchemaRequest(BaseModel):
    fields:      List[FieldDefinition] = Field(..., min_length=1)
    description: Optional[str]         = Field(None)


class CreateSchemaRequest(BaseModel):
    document_type: str                  = Field(..., min_length=2,
                                                description="New document type name")
    description:   str                  = Field(default="")
    fields:        List[FieldDefinition] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="List all document type schemas",
)
async def list_schemas(
    _user: UserInfo = Depends(get_current_user),
):
    """
    Returns all document type schemas — document type name, description,
    field count, and the field list (name, type, required).
    Requires a valid user token (any authenticated user can read schemas).
    """
    try:
        return {
            "total":   len(schema_store.list_schemas()),
            "schemas": schema_store.list_schemas(),
        }
    except Exception as e:
        logger.error(f"list_schemas failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_type}",
    summary="Get schema for one document type",
)
async def get_schema(
    document_type: str,
    _user: UserInfo = Depends(get_current_user),
):
    """
    Returns the full schema for a single document type including all fields
    with their types, descriptions, and required flags.

    `document_type` is case-insensitive (e.g. `identity proof`, `Identity Proof`).
    """
    schema = schema_store.get_schema(document_type)
    if schema is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error":         "schema_not_found",
                "document_type": document_type,
                "message":       f"No schema found for document type '{document_type}'.",
                "available":     [s["document_type"] for s in schema_store.list_schemas()],
            },
        )
    return schema


@router.put(
    "/{document_type}",
    summary="Update a document type schema (admin only)",
)
async def update_schema(
    document_type: str,
    body: UpdateSchemaRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    Replace the field list for an existing document type.

    - Each field must have a `name` and a `type` (string/date/number/boolean/email/phone).
    - Duplicate field names are rejected.
    - Empty field lists are rejected.
    - Changes take effect on the **next** extraction call — no server restart needed.

    Admin only (requires service_role JWT or ADMIN_USER_IDS in .env).
    """
    try:
        fields_raw = [f.model_dump() for f in body.fields]
        updated = schema_store.update_schema(
            document_type=document_type,
            fields=fields_raw,
            description=body.description,
        )
        logger.info(
            f"Admin {admin.user_id} updated schema for '{document_type}' "
            f"({len(fields_raw)} fields)"
        )
        return {
            "status":        "updated",
            "document_type": document_type,
            "field_count":   len(fields_raw),
            "schema":        updated,
        }
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "schema_not_found", "message": str(e)},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_schema", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"update_schema failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new custom document type + schema (admin only)",
)
async def create_schema(
    body: CreateSchemaRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    Add a brand-new document type with its field schema.

    - `document_type` must not already exist.
    - Same field validation rules as PUT apply.
    - The new type is immediately available for classification and extraction.

    Admin only.
    """
    try:
        fields_raw = [f.model_dump() for f in body.fields]
        created = schema_store.add_schema(
            document_type=body.document_type,
            fields=fields_raw,
            description=body.description,
        )
        logger.info(
            f"Admin {admin.user_id} created new schema '{body.document_type}' "
            f"({len(fields_raw)} fields)"
        )
        return {
            "status":        "created",
            "document_type": body.document_type,
            "field_count":   len(fields_raw),
            "schema":        created,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail={"error": "schema_exists_or_invalid", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"create_schema failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def register_schema_routes(app) -> None:
    """Register schema routes on the FastAPI app. Called from main.py."""
    app.include_router(router)
    logger.info("Schema routes registered: GET/PUT/POST /schemas")
