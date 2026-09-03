"""
FastAPI auth dependencies — CSRFlow edition.

Exports:
  UserInfo                  — dataclass returned by all auth deps
  get_current_user          — verifies JWT, no DB call
  get_current_user_with_role— verifies JWT + fetches csr_role from Supabase
  require_admin             — requires csr_head role
  require_role(*roles)      — factory: dependency that gates by csr_role

JWT strategy
────────────
Supabase issues HS256 (older projects) or ES256 (newer projects).
We detect the algorithm from the token header and verify accordingly.
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Set
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# UserInfo dataclass
# ---------------------------------------------------------------------------

@dataclass
class UserInfo:
    user_id:  str
    email:    Optional[str] = None
    phone:    Optional[str] = None
    role:     str = "authenticated"   # Supabase JWT claim
    csr_role: Optional[str] = None    # from user_profiles table


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _jwt_secret() -> str:
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET is not set. "
            "Add it to .env (Supabase Dashboard → Project Settings → API → JWT Secret)."
        )
    if secret.startswith("sb_secret_"):
        secret = secret[len("sb_secret_"):]
    return secret


def _supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")


def _supabase_service_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def _admin_ids() -> Set[str]:
    """Fallback: user IDs that are always treated as csr_head."""
    raw = os.getenv("ADMIN_USER_IDS", "")
    return {uid.strip() for uid in raw.split(",") if uid.strip()}


def _401(detail: str, error: str = "unauthorized") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": error, "detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# JWKS client (ES256)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_jwks_client():
    url = _supabase_url()
    if not url:
        raise RuntimeError("SUPABASE_URL is not set.")
    from jwt import PyJWKClient
    return PyJWKClient(f"{url}/auth/v1/.well-known/jwks.json", cache_keys=True)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def _verify_es256(token: str) -> dict:
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token, signing_key.key,
            algorithms=["ES256"], audience="authenticated",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise _401("Token has expired. Please log in again.", error="token_expired")
    except jwt.InvalidAudienceError:
        raise _401("Token audience is invalid.", error="invalid_audience")
    except jwt.InvalidSignatureError:
        raise _401("Token signature is invalid.", error="invalid_signature")
    except jwt.DecodeError as e:
        raise _401(f"Token is malformed: {e}", error="malformed_token")
    except Exception as e:
        raise _401(f"Token validation failed: {e}", error="token_invalid")


def _verify_hs256(token: str) -> dict:
    try:
        secret = _jwt_secret()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "auth_misconfigured", "detail": str(e)},
        )
    try:
        return jwt.decode(
            token, secret,
            algorithms=["HS256"], audience="authenticated",
            options={"verify_exp": True, "verify_signature": True},
        )
    except jwt.ExpiredSignatureError:
        raise _401("Token has expired. Please log in again.", error="token_expired")
    except jwt.InvalidAudienceError:
        raise _401("Token audience is invalid.", error="invalid_audience")
    except jwt.InvalidSignatureError:
        raise _401("Token signature is invalid.", error="invalid_signature")
    except jwt.DecodeError as e:
        raise _401(f"Token is malformed: {e}", error="malformed_token")
    except jwt.PyJWTError as e:
        raise _401(f"Token validation failed: {e}", error="token_invalid")


# ---------------------------------------------------------------------------
# Supabase profile lookup
# ---------------------------------------------------------------------------

async def _fetch_csr_role(user_id: str) -> Optional[str]:
    """
    Fetch csr_role from user_profiles via Supabase REST API.
    Uses service-role key so RLS is bypassed.
    Returns None on any error — callers handle gracefully.
    """
    url = _supabase_url()
    key = _supabase_service_key()
    if not url or not key:
        logger.warning("Supabase URL/key not set — cannot fetch csr_role")
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/user_profiles",
                params={"id": f"eq.{user_id}", "select": "csr_role"},
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0].get("csr_role")
    except Exception as e:
        logger.warning(f"Failed to fetch csr_role for {user_id}: {e}")
    return None


# ---------------------------------------------------------------------------
# Core FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
) -> UserInfo:
    """
    Verify the Bearer JWT. Returns UserInfo (csr_role is None here).
    Use get_current_user_with_role when you need the CSR role.
    """
    if credentials is None or not credentials.credentials:
        raise _401(
            "Authorization header missing. "
            "Include 'Authorization: Bearer <token>' in your request.",
            error="missing_token",
        )

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
    except jwt.DecodeError as e:
        raise _401(f"Token is malformed: {e}", error="malformed_token")

    if alg == "ES256":
        payload = _verify_es256(token)
    elif alg == "HS256":
        payload = _verify_hs256(token)
    else:
        raise _401(
            f"Unsupported JWT algorithm: {alg}. Expected HS256 or ES256.",
            error="unsupported_algorithm",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise _401("Token missing user ID (sub claim).", error="missing_sub")

    return UserInfo(
        user_id=user_id,
        email=payload.get("email"),
        phone=payload.get("phone"),
        role=payload.get("role", "authenticated"),
        csr_role=None,
    )


async def get_current_user_with_role(
    user: UserInfo = Depends(get_current_user),
) -> UserInfo:
    """
    Extends get_current_user — also loads csr_role from user_profiles.
    Use this on any endpoint that needs role-based decisions.
    """
    if user.role == "service_role":
        user.csr_role = "csr_head"
        return user
    if user.user_id in _admin_ids():
        user.csr_role = "csr_head"
        return user
    user.csr_role = await _fetch_csr_role(user.user_id)
    return user


async def require_admin(
    user: UserInfo = Depends(get_current_user_with_role),
) -> UserInfo:
    """Requires csr_head role (or service_role / ADMIN_USER_IDS)."""
    if user.role == "service_role" or user.user_id in _admin_ids():
        return user
    if user.csr_role == "csr_head":
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error":  "forbidden",
            "detail": "CSR Head access required.",
        },
    )


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.post("/projects")
        async def create_project(
            user: UserInfo = Depends(require_role("csr_head"))
        ):
            ...
    """
    allowed: List[str] = list(allowed_roles)

    async def _dep(
        user: UserInfo = Depends(get_current_user_with_role),
    ) -> UserInfo:
        if user.role == "service_role" or user.user_id in _admin_ids():
            return user
        if user.csr_role in allowed:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error":  "forbidden",
                "detail": (
                    f"Requires role: {' or '.join(allowed)}. "
                    f"Your role: {user.csr_role or 'none'}."
                ),
            },
        )

    return _dep
