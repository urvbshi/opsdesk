import hmac
import hashlib
import os
from typing import Optional
import bcrypt
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Ticket

SECRET_KEY = os.getenv("SECRET_KEY", "opsdesk-super-secret-key-change-in-production-123456")
COOKIE_NAME = "opsdesk_session"


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def sign_user_id(user_id: int) -> str:
    """Generates a tamper-proof signed cookie value: '{user_id}.{hmac_signature}'"""
    sig = hmac.new(SECRET_KEY.encode("utf-8"), str(user_id).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{user_id}.{sig}"


def verify_user_id_token(token: str) -> Optional[int]:
    """Validates the tamper-proof signature and extracts the user_id."""
    if not token or "." not in token:
        return None
    try:
        uid_str, sig = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), uid_str.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return int(uid_str)
    except Exception:
        return None
    return None


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Reads the session cookie and returns the active User object, or None if not logged in.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = verify_user_id_token(token)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_current_user_required(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)) -> User:
    """
    Requires the user to be logged in. Raises 401 if missing/invalid.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"Location": "/login"},
        )
    return current_user


def enforce_agency_access(user: User, ticket: Ticket) -> None:
    """
    Backend role enforcement:
    A Requester can ONLY view or modify tickets belonging to their own agency.
    If a Requester tampers with a URL pointing to another agency's ticket, they receive 403 Forbidden.
    Agents, Escalation Managers, and Leads can view tickets across all agencies.
    """
    if user.role == "Requester":
        if ticket.agency_id != user.agency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Forbidden: You do not have permission to view tickets for another agency."
            )
