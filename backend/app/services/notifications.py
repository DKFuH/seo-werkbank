"""Opt-in, bounded alert delivery. No delivery if disabled or not configured."""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit

import httpx

from ..security.ssrf import resolve_and_check, validate_url
from .settings_store import get_setting

log = logging.getLogger("seo.notify")


def _smtp_send(cfg: dict, subject: str, message: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject[:190]
    msg["From"] = cfg["from_email"]
    msg["To"] = cfg["to_email"]
    msg.set_content(message[:6500])
    with smtplib.SMTP(cfg["smtp_host"], int(cfg.get("smtp_port") or 587), timeout=15) as client:
        client.ehlo()
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
        if cfg.get("smtp_user"):
            client.login(cfg["smtp_user"], cfg.get("smtp_password") or "")
        client.send_message(msg)


async def deliver_alerts(db, site_name: str, alerts: list[dict]) -> dict:
    """Send one aggregate event per monitor run, not one message per alert."""
    cfg = get_setting(db, "notifications")
    if cfg.get("enabled") != "true" or not alerts:
        return {"sent": False, "reason": "disabled"}
    level = cfg.get("min_severity", "high")
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    selected = [a for a in alerts if order.get(a.get("severity", ""), 0) >= order.get(level, 2)][:12]
    if not selected:
        return {"sent": False, "reason": "severity_filtered"}
    subject = f"SEO-Werkbank: {len(selected)} Meldung(en) – {site_name}"
    body = "\n\n".join(f"[{a['severity']}] {a['title']}\n{a.get('message', '')}" for a in selected)[:6000]
    outcomes: dict[str, str] = {}
    if cfg.get("smtp_host") and cfg.get("to_email") and cfg.get("from_email"):
        try:
            await asyncio.to_thread(_smtp_send, cfg, subject, body)
            outcomes["smtp"] = "sent"
        except (OSError, smtplib.SMTPException, TimeoutError) as exc:
            log.warning("SMTP delivery failed (%s)", type(exc).__name__)
            outcomes["smtp"] = "failed"
    hook = cfg.get("webhook_url", "")
    if hook:
        try:
            validate_url(hook, allow_private=False)
            parts = urlsplit(hook)
            if parts.scheme != "https" or parts.port not in (None, 443):
                raise ValueError("HTTPS (port 443) required")
            await resolve_and_check(parts.hostname or "", 443, False)
            async with httpx.AsyncClient(timeout=12, follow_redirects=False, trust_env=False) as client:
                r = await client.post(hook, json={"text": subject + "\n" + body,
                      "event": "seo_alerts", "site": site_name, "count": len(selected)})
                r.raise_for_status()
            outcomes["webhook"] = "sent"
        except Exception as exc:  # noqa: BLE001 - DNS/SSRF checks and HTTP delivery must never invalidate alerts
            log.warning("Webhook delivery failed (%s)", type(exc).__name__)
            outcomes["webhook"] = "failed"
    return {"sent": bool(outcomes) and all(x == "sent" for x in outcomes.values()), "channels": outcomes,
            "selected": len(selected)}
