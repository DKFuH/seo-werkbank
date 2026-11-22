"""Security: secrets are never persisted as plaintext, including per-user OAuth tokens."""
from cryptography.fernet import Fernet
import pytest

from app.db import session_scope
from app.models import Setting
from app.services.credential_crypto import decrypt_payload, encrypt_payload, decrypt_secret, encrypt_secret
from app.services.settings_store import get_private, get_setting, migrate_integration_secrets, set_private, set_setting


def test_credential_roundtrip_and_wrong_key():
    key = Fernet.generate_key()
    ciphertext = encrypt_secret("sensitive", key=key)
    assert "sensitive" not in ciphertext
    assert decrypt_secret(ciphertext, key=key) == "sensitive"
    with pytest.raises(RuntimeError, match="SEO_MASTER_KEY"):
        decrypt_secret(ciphertext, key=Fernet.generate_key())
    assert decrypt_payload(encrypt_payload({"access_token": "secret"}, key=key), key=key) == {"access_token": "secret"}


def test_instance_settings_and_private_tokens_are_encrypted():
    with session_scope() as db:
        set_setting(db, "pagespeed", {"api_key": "this-is-a-sensitive-test-api-key"})
        set_private(db, "secure-test", {"refresh_token": "private-refresh-token"})
        db.commit()
        s = db.get(Setting, "pagespeed").value
        p = db.get(Setting, "_private:secure-test").value
        assert list(s) == ["_ciphertext"] and list(p) == ["_ciphertext"]
        assert "sensitive-test" not in str(s)
        assert "private-refresh-token" not in str(p)
        assert get_setting(db, "pagespeed")["api_key"] == "this-is-a-sensitive-test-api-key"
        assert get_private(db, "secure-test")["refresh_token"] == "private-refresh-token"


def test_legacy_migration_runs_once():
    with session_scope() as db:
        db.merge(Setting(key="matomo", value={"url": "https://matomo.example/", "token_auth": "legacy-secret-value"}))
        db.commit()
    assert migrate_integration_secrets() >= 1
    assert migrate_integration_secrets() == 0
    with session_scope() as db:
        raw = db.get(Setting, "matomo").value
        assert "legacy-secret-value" not in str(raw)
        assert get_setting(db, "matomo")["token_auth"] == "legacy-secret-value"
