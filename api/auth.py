"""
auth.py — Supabase JWT authentication middleware for FastAPI backend with offline/dev fallback.
"""

import os
import logging
from typing import Dict, Any, Optional

from fastapi import Header, HTTPException, Depends

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = Any

logger = logging.getLogger(__name__)

def get_supabase_client() -> Optional[Any]:
    """Initializes Supabase Client using environment variables."""
    if create_client is None:
        return None
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key or url.startswith("https://xxxx"):
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        return None

def verify_jwt(token: str) -> Dict[str, Any]:
    """Verifies Supabase JWT token string and returns investigator user metadata."""
    client = get_supabase_client()
    if client is None:
        # Dev bypass mode
        return {'id': 'dev_investigator_001', 'email': 'investigator@evidra.local', 'role': 'authenticated'}

    try:
        user_response = client.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired JWT token")
        return {
            'id': user.id,
            'email': user.email,
            'role': getattr(user, 'role', 'authenticated')
        }
    except Exception as e:
        logger.error(f"JWT verification failure: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

async def get_current_investigator(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """FastAPI dependency: verifies Bearer token header."""
    client = get_supabase_client()
    if client is None:
        return {'id': 'dev_investigator_001', 'email': 'investigator@evidra.local', 'role': 'authenticated'}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header (Bearer token required)")

    token = authorization.split(" ")[1]
    return verify_jwt(token)
