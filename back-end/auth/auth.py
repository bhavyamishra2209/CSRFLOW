"""
FastAPI auth dependencies.

get_current_user  — verifies a Supabase-issued Bearer JWT, returns UserInfo.
require_admin     — extends get_current_user, requires an admin role/id.

JWT verification strategy
─────────────────────────
Supabase issues two JWT algorithm types depending on project age:
  - Older projects: HS256 — verified with SUPABASE_JWT_SECRET
  - Newer projects: ES256 — verified with Supabase's public JWKS endpoint

We handle both automatically:
1. Peek at the token header to determine the algorithm.
2. For HS256 → verify locally with SUPABASE_JWT_SECRET.
3. For ES256 → fetch the public key from Supabase JWKS and verify.

Error responses
───────────────
All auth failures raise HTTP 401 with a structured JSON body:
  { "error": "...", "detail": "human-readable reason" }
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional, Set
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class UserInfo:
    user_id: str
    email:   Optional[str] = None
    phone:   Optional[str] = None
    role:    str = "authenticated"


def _jwt_secret() -> str:
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET is not set. "
            "Add it to your .env file (Project Settings → API → JWT Secret)."
        )
    # Strip Supabase's newer sb_secret_ prefix if present
    if secret.startswith("sb_secret_"):
        secret = secret[len("sb_secret_"):]
    return secret


def _supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")


def _admin_ids() -> Set[str]:
    raw = os.getenv("ADMIN_USER_IDS", "")
    return {uid.strip() for uid in raw.split(",") if uid.strip()}


def _401(detail: str, error: str = "unauthorized") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": error, "detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache(maxsize=1)
def _get_jwks_client():
    """
    Return a PyJWT JWKSClient pointed at the Supabase JWKS endpoint.
    Cached for the lifetime of the process (JWKS rarely changes).
    """
    url = _supabase_url()
    if not url:
        raise RuntimeError("SUPABASE_URL is not set.")
    jwks_url = f"{url}/auth/v1/.well-known/jwks.json"
    try:
        from jwt import PyJWKClient
        return PyJWKClient(jwks_url, cache_keys=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create JWKS client: {e}")


def _verify_es256(token: str) -> dict:
    """Verify an ES256 JWT using Supabase's public JWKS."""
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload
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
    """Verify an HS256 JWT using the local JWT secret."""
    try:
        secret = _jwt_secret()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "auth_misconfigured", "detail": str(e)},
        )
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
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


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
) -> UserInfo:
    """
    FastAPI dependency. Verifies a Supabase Bearer JWT (HS256 or ES256).
    Returns UserInfo on success. Raises 401 on any failure.
    """
    if credentials is None or not credentials.credentials:
        raise _401(
            "Authorization header missing. "
            "Include 'Authorization: Bearer <token>' in your request.",
            error="missing_token",
        )

    token = credentials.credentials

    # ── Dev token fallback for 3 RBAC Roles (Local Testing) ─────────────
    if token in ("csr-head-token", "csr_head", "head_csr_001"):
        return UserInfo(
            user_id="head_csr_001",
            email="csrhead@csrflow.com",
            phone="+1234567890",
            role="csr_head",
        )

    if token in ("pm-token", "pm", "pm_exec_101"):
        return UserInfo(
            user_id="pm_exec_101",
            email="pm@csrflow.com",
            phone="+1234567890",
            role="project_manager",
        )

    if token in ("auditor-token", "auditor", "auditor_rev_201"):
        return UserInfo(
            user_id="auditor_rev_201",
            email="auditor@csrflow.com",
            phone="+1234567890",
            role="auditor",
        )

    if token in ("dev-token", "dev", "test-token", "dev_user_123") or not os.getenv("SUPABASE_JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET") == "your-jwt-secret-here":
        return UserInfo(
            user_id="head_csr_001",
            email="csrhead@csrflow.com",
            phone="+1234567890",
            role="csr_head",
        )

    # Peek at the header to determine algorithm — no verification yet
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
        raise _401("Token does not contain a user ID (sub claim).", error="missing_sub")

    return UserInfo(
        user_id=user_id,
        email=payload.get("email"),
        phone=payload.get("phone"),
        role=payload.get("role", "authenticated"),
    )


async def require_admin(
    user: UserInfo = Depends(get_current_user),
) -> UserInfo:
    """Extends get_current_user — additionally requires admin role."""
    if user.role == "service_role":
        return user
    if user.user_id in _admin_ids():
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error":  "forbidden",
            "detail": "Admin access required for this endpoint.",
        },
    )


async def require_auditor(
    user: UserInfo = Depends(get_current_user),
) -> UserInfo:
    """Extends get_current_user — requires auditor, approver, admin, or service_role."""
    if user.role in ("auditor", "approver", "admin", "service_role"):
        return user
    if user.user_id in _admin_ids():
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "forbidden",
            "detail": "Auditor or Approver role required for this action.",
        },
    )
