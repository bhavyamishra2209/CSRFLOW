"""
User profile routes — CSRFlow

GET  /users/me/profile              — get my profile + csr_role
PUT  /users/me/profile              — update my name / organisation
GET  /admin/users                   — list all users (csr_head only)
PUT  /admin/users/{user_id}/role    — assign a csr_role (csr_head only)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.auth import UserInfo, get_current_user_with_role, require_admin, require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


# ---------------------------------------------------------------------------
# Supabase REST helper
# ---------------------------------------------------------------------------

def _sb_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")

def _sb_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

def _headers() -> Dict[str, str]:
    key = _sb_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=representation",
    }


async def _get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(
            f"{_sb_url()}/rest/v1/user_profiles",
            params={"id": f"eq.{user_id}", "select": "*"},
            headers=_headers(),
        )
    if resp.status_code == 200:
        data = resp.json()
        return data[0] if data else None
    return None


async def _upsert_profile(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(
            f"{_sb_url()}/rest/v1/user_profiles",
            json=payload,
            headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
        )
    if resp.status_code in (200, 201):
        data = resp.json()
        return data[0] if data else None
    logger.error(f"Upsert profile failed {resp.status_code}: {resp.text}")
    return None


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ProfileUpdate(BaseModel):
    full_name:    Optional[str] = None
    organisation: Optional[str] = None


class RoleAssign(BaseModel):
    csr_role: str   # "csr_head" | "project_manager" | "approver"


VALID_ROLES = {"csr_head", "project_manager", "approver"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/users/me/profile", summary="Get my CSR profile")
async def get_my_profile(user: UserInfo = Depends(get_current_user_with_role)):
    profile = await _get_profile(user.user_id)
    if not profile:
        # Auto-create with default role if missing (handles legacy accounts)
        created = await _upsert_profile({
            "id": user.user_id,
            "email": user.email,
            "csr_role": user.csr_role or "project_manager",
        })
        return created or {"id": user.user_id, "email": user.email, "csr_role": "project_manager"}
    return profile


@router.put("/users/me/profile", summary="Update my name / organisation")
async def update_my_profile(
    body: ProfileUpdate,
    user: UserInfo = Depends(get_current_user_with_role),
):
    # Only allow updating non-role fields
    patch: Dict[str, Any] = {}
    if body.full_name is not None:
        patch["full_name"] = body.full_name
    if body.organisation is not None:
        patch["organisation"] = body.organisation

    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update.")

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/user_profiles",
            params={"id": f"eq.{user.user_id}"},
            json=patch,
            headers=_headers(),
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Failed to update profile.")

    return {"message": "Profile updated.", "updated": patch}


@router.get("/admin/users", summary="List all users (CSR Head only)")
async def list_users(_admin: UserInfo = Depends(require_admin)):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_sb_url()}/rest/v1/user_profiles",
            params={"select": "id,email,full_name,organisation,csr_role,is_active,created_at"},
            headers=_headers(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch users.")
    return resp.json()


@router.put(
    "/admin/users/{target_user_id}/role",
    summary="Assign a CSR role to a user (CSR Head only)",
)
async def assign_role(
    target_user_id: str,
    body: RoleAssign,
    admin: UserInfo = Depends(require_admin),
):
    if body.csr_role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.csr_role}'. Valid roles: {list(VALID_ROLES)}",
        )

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/user_profiles",
            params={"id": f"eq.{target_user_id}"},
            json={"csr_role": body.csr_role},
            headers=_headers(),
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Failed to update role.")

    return {
        "message": f"Role updated to '{body.csr_role}'.",
        "user_id": target_user_id,
        "csr_role": body.csr_role,
    }


def register_user_routes(app):
    app.include_router(router)
