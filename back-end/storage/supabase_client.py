"""
Supabase client — thin wrapper that initialises the Supabase SDK once and
exposes a get_client() helper for the rest of the application.

Environment variables required (add to .env):
  SUPABASE_URL              — your project URL
  SUPABASE_SERVICE_ROLE_KEY — service-role secret (never expose to clients)
"""

import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Availability flag — set to False when supabase-py is not installed so the
# rest of the app can degrade gracefully rather than crash on import.
# ---------------------------------------------------------------------------
SUPABASE_AVAILABLE = False
_supabase_client = None


def _init() -> None:
    """Initialise the module-level client on first use."""
    global SUPABASE_AVAILABLE, _supabase_client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — "
            "Supabase features disabled."
        )
        return

    try:
        from supabase import create_client, Client  # type: ignore
        _supabase_client = create_client(url, key)
        SUPABASE_AVAILABLE = True
        logger.info("Supabase client initialised successfully")
    except ImportError:
        logger.warning(
            "supabase-py not installed — run: pip install supabase==2.4.2"
        )
    except Exception as e:
        logger.error(f"Failed to initialise Supabase client: {e}")


# Initialise eagerly at import time
_init()


def get_client():
    """
    Return the initialised Supabase client.

    Raises RuntimeError if Supabase is not configured, so callers can
    catch it and return a 503 rather than crashing.
    """
    if _supabase_client is None:
        raise RuntimeError(
            "Supabase client not available. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file."
        )
    return _supabase_client
