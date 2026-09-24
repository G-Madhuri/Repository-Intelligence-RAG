import os
import logging
from typing import Dict, Any, Optional
from fastapi import Header, HTTPException, status, Depends
from supabase import create_client, Client

logger = logging.getLogger("auth")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://sjjnisutudwpijfymmgx.supabase.co")

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.s"
        _supabase_client = create_client(SUPABASE_URL, key)
    return _supabase_client

def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Calls supabase.auth.get_user(token)
    Returns {"uid": user.id, "email": user.email}
    Raises HTTPException(401) if invalid.
    STRICT SECURITY: No unverified JWT decoding fallback allowed.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing."
        )
    try:
        sb = get_supabase_client()
        user_response = sb.auth.get_user(token)
        if user_response and getattr(user_response, 'user', None):
            user = user_response.user
            return {
                "uid": str(user.id),
                "email": str(getattr(user, 'email', f"{user.id}@user.supabase"))
            }
        raise ValueError("No valid user returned from Supabase Auth service.")
    except Exception as e:
        logger.warning(f"Supabase token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Supabase authentication token: {str(e)}"
        )

def get_current_user(authorization: str = Header(...)) -> Dict[str, Any]:
    """
    FastAPI dependency:
    Parses 'Bearer <token>'
    Calls verify_supabase_token
    Returns user dict {"uid": ..., "email": ...}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer '"
        )
    token = authorization.split("Bearer ", 1)[1].strip()
    return verify_supabase_token(token)
