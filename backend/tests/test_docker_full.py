"""No default credentials, repeatable init and explicit Docker wiring."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "full_stack.py"
_spec = importlib.util.spec_from_file_location("seo_full_stack_launcher", SCRIPT)
assert _spec is not None and _spec.loader is not None
full_stack = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(full_stack)


def test_full_stack_env_initialization(tmp_path, monkeypatch):
    file = tmp_path / ".env"
    monkeypatch.setattr(full_stack, "ENV_FILE", file)
    assert set(full_stack.prepare_env()) == {"POSTGRES_PASSWORD", "SEARXNG_SECRET"}
    text = file.read_text(encoding="utf-8")
    values = full_stack._values(text)
    assert all(len(values[k]) == 64 for k in full_stack.SECRET_KEYS)
    assert values["POSTGRES_PASSWORD"] != values["SEARXNG_SECRET"]
    assert full_stack.prepare_env() == []
    assert file.read_text(encoding="utf-8") == text


def test_full_stack_preserves_unrelated_settings(tmp_path, monkeypatch):
    file = tmp_path / ".env"
    file.write_text("SEO_PORT=8123\n# personal value\n", encoding="utf-8")
    monkeypatch.setattr(full_stack, "ENV_FILE", file)
    full_stack.prepare_env()
    result = file.read_text(encoding="utf-8")
    assert "SEO_PORT=8123" in result
    assert "# personal value" in result
    assert result.count("POSTGRES_PASSWORD=") == 1
    assert result.count("SEARXNG_SECRET=") == 1


def test_full_stack_rejects_insecure_password(tmp_path, monkeypatch):
    import pytest

    file = tmp_path / ".env"
    file.write_text("POSTGRES_PASSWORD=change-me\n", encoding="utf-8")
    monkeypatch.setattr(full_stack, "ENV_FILE", file)
    with pytest.raises(ValueError, match="POSTGRES_PASSWORD"):
        full_stack.prepare_env()
    assert "SEARXNG_SECRET" not in file.read_text(encoding="utf-8")


def test_full_stack_compose_file_uses_private_searxng():
    root = Path(__file__).resolve().parents[2]
    content = (root / "docker-compose.full.yml").read_text(encoding="utf-8")
    assert "SEO_SEARXNG_URL: \"http://searxng:8080\"" in content
    assert "POSTGRES_PASSWORD:?" in content
    assert "searxng:" in content
    assert "seo-postgres:" in content
    assert "    expose:" in content
    assert "SEARXNG_SECRET:" in content
