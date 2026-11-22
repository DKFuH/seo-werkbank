#!/usr/bin/env python3
"""Cross-platform launcher for the SEO-Werkbank full Docker Compose stack.

Creates missing random secrets in .env without printing them or overwriting existing
credentials. Both the existing SQLite demo and its Compose file remain unchanged.
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
COMPOSE_FILE = "docker-compose.full.yml"
SECRET_KEYS = ("POSTGRES_PASSWORD", "SEARXNG_SECRET")
SAFE_SECRET = re.compile(r"^[A-Za-z0-9_-]{24,128}$")


def _values(lines: str) -> dict[str, str]:
    """Read only plain KEY=value assignments; never interpret or execute .env."""
    result: dict[str, str] = {}
    for line in lines.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        result[key.strip()] = raw.strip().strip('"').strip("'")
    return result


def prepare_env() -> list[str]:
    """Generate missing secrets once; existing secrets are immutable."""
    if not ENV_FILE.exists():
        fd = os.open(ENV_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("# SEO-Werkbank environment (local only; do not commit this file).\n")
    original = ENV_FILE.read_text(encoding="utf-8")
    values = _values(original)
    for key in SECRET_KEYS:
        if key in values and not SAFE_SECRET.fullmatch(values[key]):
            raise ValueError(
                f"{key} is too short or contains URL/Compose-unsafe characters. "
                "Use at least 24 ASCII letters, digits, '_' or '-'; do not set example passwords."
            )
    missing = [key for key in SECRET_KEYS if key not in values]
    if missing:
        additions = ["", "# Random secrets for the full Docker stack; generated once."]
        additions += [f"{key}={secrets.token_hex(32)}" for key in missing]
        with ENV_FILE.open("a", encoding="utf-8") as handle:
            if original and not original.endswith("\n"):
                handle.write("\n")
            handle.write("\n".join(additions) + "\n")
    if os.name == "posix":
        ENV_FILE.chmod(0o600)
    return missing


def command(args: list[str]) -> int:
    try:
        return subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, *args],
                              cwd=ROOT, check=False).returncode
    except FileNotFoundError:
        print("Docker Compose is missing. Install Docker Desktop / Docker Engine with Compose.", file=sys.stderr)
        return 127


def main() -> int:
    parser = argparse.ArgumentParser(description="SEO-Werkbank Docker full-stack launcher")
    parser.add_argument("action", choices=("init", "up", "down", "ps", "logs", "config"),
                        nargs="?", default="up")
    args = parser.parse_args()
    if args.action in ("init", "up", "config"):
        try:
            added = prepare_env()
        except (OSError, ValueError) as exc:
            print(f"Unable to prepare local environment: {exc}", file=sys.stderr)
            return 2
        if added:
            print("Generated local secrets: " + ", ".join(added) + " (values not displayed).")
    if args.action == "init":
        return 0
    if args.action == "up":
        result = command(["up", "-d", "--build"])
        if not result:
            print("Open http://localhost:" + _values(ENV_FILE.read_text(encoding="utf-8")).get("SEO_PORT", "8000"))
            print("First account becomes administrator. SearXNG is internal only.")
        return result
    if args.action == "down":
        print("Stopping without deleting data volumes.")
        return command(["down"])
    if args.action == "ps":
        return command(["ps"])
    if args.action == "logs":
        return command(["logs", "--tail=100", "-f"])
    return command(["config", "--quiet"])


if __name__ == "__main__":
    sys.exit(main())
