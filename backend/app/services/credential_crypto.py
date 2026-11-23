"""At-rest encryption for integration credentials and private OAuth data.

Ciphertext is versioned and authenticated (Fernet). The key is supplied through
SEO_MASTER_KEY for managed hosting, otherwise a process-local owner-readable file
under SEO_DATA_DIR for single-node installs. Losing the key loses the credentials.
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from ..config import get_settings

PREFIX = "enc:v1:"


def _key_file() -> Path:
    return get_settings().data_path / ".integration_master_key"


def master_key() -> bytes:
    explicit = get_settings().master_key.strip()
    if explicit:
        key = explicit.encode("ascii")
    else:
        path = _key_file()
        if not path.exists():
            # Single-host convenience only: managed deployments should set SEO_MASTER_KEY.
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "wb") as fh:
                    fh.write(Fernet.generate_key())
        with contextlib.suppress(OSError):
            path.chmod(0o600)
        key = path.read_bytes().strip()
    try:
        Fernet(key)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("SEO_MASTER_KEY ist kein gültiger Fernet-Schlüssel") from exc
    return key


def _cipher(key: bytes | None = None) -> Fernet:
    return Fernet(key if key is not None else master_key())


def encrypt_secret(value: str, *, key: bytes | None = None) -> str:
    if value.startswith(PREFIX):
        return value
    return PREFIX + _cipher(key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str, *, key: bytes | None = None) -> str:
    if not value.startswith(PREFIX):
        return value  # legacy plaintext, supported until startup migration
    try:
        return _cipher(key).decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Integrationsgeheimnis kann nicht entschlüsselt werden. SEO_MASTER_KEY prüfen.") from exc


def encrypt_payload(data: dict, *, key: bytes | None = None) -> dict:
    return {"_ciphertext": encrypt_secret(json.dumps(data, ensure_ascii=False), key=key)}


def decrypt_payload(data: dict, *, key: bytes | None = None) -> dict:
    if "_ciphertext" not in data:
        return dict(data)  # legacy plaintext
    try:
        loaded = json.loads(decrypt_secret(data["_ciphertext"], key=key))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Verschlüsselte Integrationseinstellungen sind beschädigt") from exc
    if not isinstance(loaded, dict):
        raise RuntimeError("Entschlüsselte Integrationsdaten haben ein ungültiges Format")
    return loaded
