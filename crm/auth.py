"""crm.auth — User model + password hashing + token generation."""
import os
from datetime import datetime

import bcrypt
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .db import query, query_one, execute


# ─── Whitelist ────────────────────────────────────────────────


def get_allowed_emails():
    raw = os.getenv("ALLOWED_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_email_allowed(email: str) -> bool:
    return (email or "").strip().lower() in get_allowed_emails()


# ─── Password hashing (bcrypt) ────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─── User model (Flask-Login) ─────────────────────────────────


class User(UserMixin):
    """Flask-Login user, hydraté depuis une row dict de la DB."""

    def __init__(self, row: dict):
        self.id            = row["id"]
        self.email         = row["email"]
        self.password_hash = row["password_hash"]
        self.full_name     = row.get("full_name") or ""
        self.role          = row.get("role") or "user"
        self.email_verified = bool(row.get("email_verified"))
        self._is_active    = bool(row.get("is_active", 1))
        self.created_at    = row.get("created_at")
        self.last_login_at = row.get("last_login_at")

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self._is_active and self.email_verified

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def initials(self):
        if self.full_name:
            parts = self.full_name.split()
            if len(parts) >= 2:
                return (parts[0][0] + parts[-1][0]).upper()
            return parts[0][:2].upper()
        return self.email[:2].upper()


def get_user_by_id(user_id) -> User | None:
    row = query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    return User(row) if row else None


def get_user_by_email(email: str) -> User | None:
    if not email:
        return None
    row = query_one("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    return User(row) if row else None


def create_user(email: str, password: str, full_name: str = "") -> int:
    """Crée un user (non vérifié). Retourne id."""
    pw_hash = hash_password(password)
    role = "admin" if not query_one("SELECT id FROM users LIMIT 1") else "user"
    return execute(
        """INSERT INTO users (email, password_hash, full_name, role, email_verified)
           VALUES (?, ?, ?, ?, 0)""",
        (email.strip().lower(), pw_hash, full_name.strip(), role),
    )


def mark_email_verified(user_id: int):
    execute(
        "UPDATE users SET email_verified = 1, updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), user_id),
    )


def update_password(user_id: int, new_password: str):
    pw_hash = hash_password(new_password)
    execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (pw_hash, datetime.utcnow().isoformat(), user_id),
    )


def touch_last_login(user_id: int):
    execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), user_id),
    )


def touch_verification_sent(user_id: int):
    execute(
        "UPDATE users SET verification_sent_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), user_id),
    )


# ─── Tokens (signed, expiring) via itsdangerous ──────────────


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        raise RuntimeError("FLASK_SECRET_KEY non défini dans .env")
    return URLSafeTimedSerializer(secret_key=secret)


def make_verify_token(user_id: int) -> str:
    """Token signé pour vérification email. Expire en 24h."""
    return _serializer().dumps({"uid": user_id}, salt="verify-email")


def read_verify_token(token: str, max_age_seconds: int = 86400):
    """Returns {"uid": int} ou raise SignatureExpired / BadSignature."""
    return _serializer().loads(token, salt="verify-email", max_age=max_age_seconds)


def make_reset_token(user_id: int) -> str:
    """Token signé pour password reset. Expire en 1h."""
    return _serializer().dumps({"uid": user_id}, salt="reset-password")


def read_reset_token(token: str, max_age_seconds: int = 3600):
    return _serializer().loads(token, salt="reset-password", max_age=max_age_seconds)


# Exposer les erreurs itsdangerous pour usage dans les routes
__all__ = [
    "is_email_allowed", "get_allowed_emails",
    "hash_password", "verify_password",
    "User", "get_user_by_id", "get_user_by_email", "create_user",
    "mark_email_verified", "update_password", "touch_last_login",
    "touch_verification_sent",
    "make_verify_token", "read_verify_token",
    "make_reset_token", "read_reset_token",
    "BadSignature", "SignatureExpired",
]
