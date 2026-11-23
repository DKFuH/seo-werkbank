"""Instance-wide integration settings stored in the database (set from the Settings page).

Secrets are write-only through the API. The stored values are encrypted with a
versioned master key; the public API always returns masked placeholders.
"""
from __future__ import annotations

import os

from sqlalchemy.orm import Session

from ..models import Setting
from .credential_crypto import decrypt_payload, encrypt_payload, master_key

SECRET_FIELDS = {"api_key", "client_secret", "access_token", "refresh_token", "tokens", "token_auth"}
MASK = "********"

DEFAULTS: dict[str, dict] = {
    "serp": {"provider": "none", "searxng_url": "", "google_cse_key": "", "google_cse_cx": "", "brave_key": ""},
    "pagespeed": {"api_key": ""},
    "ai": {"provider": "none", "base_url": "http://localhost:11434", "model": "llama3.1", "api_key": ""},
    "gsc": {"client_id": "", "client_secret": ""},
    "matomo": {"url": "", "token_auth": ""},
    "bing": {"api_key": ""},
    "indexnow": {"key": "", "key_location": ""},
    "notifications": {"enabled": "false", "min_severity": "high", "smtp_host": "", "smtp_port": "587",
                      "smtp_user": "", "smtp_password": "", "from_email": "", "to_email": "", "webhook_url": ""},
}
_SECRET_KEYS = {"serp": {"google_cse_key", "brave_key"}, "pagespeed": {"api_key"}, "ai": {"api_key"}, "gsc": {"client_secret"}, "matomo": {"token_auth"}, "bing": {"api_key"}, "notifications": {"smtp_password", "webhook_url"}}


def get_setting(db: Session, key: str) -> dict:
    row = db.get(Setting, key)
    value = dict(DEFAULTS.get(key, {}))
    # Optional Docker full-stack integration: an environment default is applied
    # ONLY when the administrator has never saved SERP settings. Explicit
    # provider=none or a chosen external provider always wins.
    if key == "serp" and row is None:
        searxng_url = os.getenv("SEO_SEARXNG_URL", "").strip()
        if searxng_url:
            value.update({"provider": "searxng", "searxng_url": searxng_url})
    if row and isinstance(row.value, dict):
        value.update(decrypt_payload(row.value))
    return value


def set_setting(db: Session, key: str, value: dict) -> dict:
    current = get_setting(db, key)
    for k, v in value.items():
        if k in _SECRET_KEYS.get(key, set()) and v == MASK:
            continue  # unchanged secret echoed back by the UI
        if key in DEFAULTS and k not in DEFAULTS[key]:
            continue
        current[k] = v
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=encrypt_payload(current)))
    else:
        row.value = encrypt_payload(current)
    db.flush()
    return current


def masked(key: str, value: dict) -> dict:
    out = dict(value)
    for k in _SECRET_KEYS.get(key, set()):
        if out.get(k):
            out[k] = MASK
    return out


def get_private(db: Session, key: str) -> dict:
    """Internal state that is never exposed through the settings API (OAuth tokens)."""
    row = db.get(Setting, f"_private:{key}")
    return decrypt_payload(row.value) if row and isinstance(row.value, dict) else {}


def set_private(db: Session, key: str, value: dict) -> None:
    row = db.get(Setting, f"_private:{key}")
    if row is None:
        db.add(Setting(key=f"_private:{key}", value=encrypt_payload(value)))
    else:
        row.value = encrypt_payload(value)
    db.flush()


def migrate_integration_secrets() -> int:
    """Encrypt existing setting rows atomically and fail on an unreadable master key.

    This is also a startup integrity check for already-encrypted values. It must
    run before background workers start; a lost key fails closed.
    """
    from sqlalchemy import select

    from ..db import session_scope

    key = master_key()
    changed = 0
    with session_scope() as db:
        rows = list(db.scalars(select(Setting)))
        for row in rows:
            if not row.key.startswith("_private:") and row.key not in DEFAULTS:
                continue
            decoded = decrypt_payload(row.value, key=key)
            if "_ciphertext" not in row.value:
                row.value = encrypt_payload(decoded, key=key)
                changed += 1
    return changed
