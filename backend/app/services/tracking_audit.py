"""Deterministic Tracking, Tagging, and Consent Audit.

Inspects raw HTML and Playwright network traces for:
- Analytics/Tag Manager tags (GA4, GTM, Matomo, Clarity, Meta Pixel)
- CMP detection (Borlabs, Cookiebot, Usercentrics, Klaro, OneTrust, Complianz, CCM19)
- Static consent leakage (tags included without CMP blocking attributes)
- Dynamic consent leakage (requests sent in initial state before consent)
- Duplicate tag initialization
- Conversion & contact targets (tel:, mailto:, forms) and tracking readiness
"""
from __future__ import annotations

import re
from typing import Any

import lxml.html

# Tag pattern extractors
GA4_PATTERN = re.compile(r"\b(G-[A-Z0-9]{8,14})\b")
GTM_PATTERN = re.compile(r"\b(GTM-[A-Z0-9]{5,10})\b")
UA_PATTERN = re.compile(r"\b(UA-[0-9]+-[0-9]+)\b")
CLARITY_TAG_PATTERN = re.compile(r"clarity\.ms/tag/([a-z0-9]+)", re.I)
CLARITY_INIT_PATTERN = re.compile(r"""clarity\(\s*["']init["']\s*,\s*["']([a-z0-9]+)["']""", re.I)
CLARITY_BOOTSTRAP_PATTERN = re.compile(r"""["']clarity["']\s*,\s*["']script["']\s*,\s*["']([a-z0-9]+)["']""", re.I)

META_PIXEL_PATTERN = re.compile(r"""fbq\(\s*["']init["']\s*,\s*["']([0-9]{10,20})["']""", re.I)
BING_UET_PATTERN = re.compile(r"""bat\.bing\.com/action/0\?ti=([0-9]+)""")
BING_UET_INIT_PATTERN = re.compile(r"""tagId\s*[:=]\s*["']?([0-9]{6,12})["']?""")
MATOMO_SITE_ID_PATTERN = re.compile(r"""_paq\.push\(\s*\[\s*["']setSiteId["']\s*,\s*["']?([0-9]+)["']?\s*\]\s*\)""")
MATOMO_URL_PATTERN = re.compile(r"""_paq\.push\(\s*\[\s*["']setTrackerUrl["']\s*,\s*["']([^"']+)["']\s*\]\s*\)""")

# CMP signatures in script sources, inline code, or DOM elements
CMP_SIGNATURES: dict[str, list[str]] = {
    "Borlabs Cookie": ["borlabsCookie", "borlabs-cookie", "borlabs_cookie_box"],
    "Cookiebot": ["cookiebot.com", "data-cookieconsent", "Cookiebot"],
    "Usercentrics": ["usercentrics.eu", "app.usercentrics.eu", "data-usercentrics", "uc-block"],
    "Klaro": ["klaro.js", "data-klaro", "klaro-cookie"],
    "OneTrust": ["onetrust.com", "OptanonWrapper", "optanon-cookie-policy"],
    "Complianz": ["complianz.io", "cmplz-cookiebanner", "data-cmplz"],
    "CCM19": ["ccm19", "ccm19.de"],
}

# Domains of third-party trackers for network & static script checks
TRACKER_DOMAINS = {
    "google_analytics": ("google-analytics.com", "analytics.google.com"),
    "google_tag_manager": ("googletagmanager.com",),
    "bing_advertising": ("bat.bing.com",),
    "clarity": ("clarity.ms",),
    "meta_pixel": ("connect.facebook.net", "facebook.com/tr"),
    "matomo": ("matomo.js", "piwik.js"),
    "advertising": ("doubleclick.net", "adservice.google.com", "googleadservices.com"),
}


def inspect_html_tracking(html: str, url: str) -> dict[str, Any]:
    """Deterministically parses an HTML document for tracking tags, CMPs, and conversion targets."""
    if not html:
        return {"error": "Leeres HTML-Dokument"}

    try:
        doc = lxml.html.fromstring(html.encode("utf-8", "replace"))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"HTML-Parsing fehlgeschlagen: {exc}"}

    scripts = doc.xpath("//script")
    script_srcs: list[str] = []
    inline_scripts: list[str] = []

    for s in scripts:
        src = s.get("src", "").strip()
        if src:
            script_srcs.append(src)
        else:
            inline_scripts.append(s.text or "")

    full_html = html

    # 1. Detect tags and measurement IDs
    ga4_ids = sorted(set(GA4_PATTERN.findall(full_html)))
    gtm_ids = sorted(set(GTM_PATTERN.findall(full_html)))
    ua_ids = sorted(set(UA_PATTERN.findall(full_html)))

    clarity_ids = sorted(set(
        CLARITY_TAG_PATTERN.findall(full_html)
        + CLARITY_INIT_PATTERN.findall(full_html)
        + CLARITY_BOOTSTRAP_PATTERN.findall(full_html)
    ))
    meta_pixel_ids = sorted(set(META_PIXEL_PATTERN.findall(full_html)))
    bing_uet_ids = sorted(set(BING_UET_PATTERN.findall(full_html) + BING_UET_INIT_PATTERN.findall(full_html)))


    matomo_sites = sorted(set(MATOMO_SITE_ID_PATTERN.findall(full_html)))
    matomo_urls = sorted(set(MATOMO_URL_PATTERN.findall(full_html)))
    has_matomo = bool(matomo_sites or matomo_urls or any("matomo.js" in s or "piwik.js" in s for s in script_srcs))

    # 2. Detect CMP
    detected_cmps: list[str] = []
    for cmp_name, patterns in CMP_SIGNATURES.items():
        if any(pat.lower() in full_html.lower() for pat in patterns):
            detected_cmps.append(cmp_name)

    # 3. Detect duplicate tags
    duplicate_warnings: list[str] = []
    # Count how often GTM script tags are inserted
    gtm_script_count = sum(1 for src in script_srcs if "googletagmanager.com/gtm.js" in src)
    if gtm_script_count > 1:
        duplicate_warnings.append(f"GTM-Container-Skript ist {gtm_script_count}× im HTML eingebunden (Gefahr doppelter Zählung)")

    # Count how often each GA4 measurement ID is configured
    for gid in ga4_ids:
        config_calls = len(re.findall(r"""gtag\(\s*['"]config['"]\s*,\s*['"]""" + re.escape(gid) + r"""['"]""", full_html))
        if config_calls > 1:
            duplicate_warnings.append(f"GA4 Measurement-ID {gid} wird {config_calls}× konfiguriert ('gtag config')")

    # Matomo trackPageView count
    matomo_pageviews = len(re.findall(r"""_paq\.push\(\s*\[\s*['"]trackPageView['"]""", full_html))
    if matomo_pageviews > 1:
        duplicate_warnings.append(f"Matomo 'trackPageView' wird {matomo_pageviews}× aufgerufen (verfälscht Pageview-Zahlen)")

    # 4. Check for Static Consent Leakage (unblocked static script tags)
    unblocked_tracking_scripts: list[dict[str, str]] = []
    for s in scripts:
        src = s.get("src", "").strip()
        script_type = (s.get("type") or "text/javascript").strip().lower()
        if not src:
            continue
        is_tracker = False
        tracker_kind = ""
        for kind, domains in TRACKER_DOMAINS.items():
            if any(dom in src.lower() for dom in domains):
                is_tracker = True
                tracker_kind = kind
                break

        if is_tracker:
            # Check if blocked by CMP (e.g. type="text/plain" or data-cookieconsent or uc-block)
            is_blocked = (
                script_type in ("text/plain", "text/blocked")
                or bool(s.get("data-cookieconsent"))
                or bool(s.get("data-usercentrics"))
                or bool(s.get("data-klaro"))
                or bool(s.get("data-cmplz"))
                or bool(s.get("data-category"))
            )
            if not is_blocked:
                unblocked_tracking_scripts.append({
                    "src": src[:200],
                    "category": tracker_kind,
                    "warning": "Statisch eingebunden ohne CMP-Blockier-Attribut: Browser lädt Tracker vor Nutzerzustimmung",
                })

    # 5. Interactive Conversion Targets (tel:, mailto:, forms)
    tel_links: list[dict[str, Any]] = []
    mailto_links: list[dict[str, Any]] = []
    for a in doc.xpath("//a[@href]"):
        href = a.get("href", "").strip()
        text = (a.text_content() or "").strip()[:80]
        has_click_handler = bool(a.get("onclick") or a.get("data-track") or a.get("data-event") or a.get("data-action"))
        if href.startswith("tel:"):
            tel_links.append({
                "href": href[:60],
                "text": text,
                "has_event_tracking": has_click_handler,
            })
        elif href.startswith("mailto:"):
            mailto_links.append({
                "href": href[:80],
                "text": text,
                "has_event_tracking": has_click_handler,
            })

    forms: list[dict[str, Any]] = []
    for f in doc.xpath("//form"):
        action = f.get("action", "").strip()
        method = (f.get("method") or "get").upper()
        form_id = f.get("id") or f.get("name") or "unbenannt"
        has_submit_handler = bool(f.get("onsubmit") or f.get("data-track") or f.get("data-event"))
        input_count = len(f.xpath(".//input | .//textarea | .//select"))
        forms.append({
            "id": form_id[:60],
            "action": action[:200],
            "method": method,
            "inputs": input_count,
            "has_event_tracking": has_submit_handler,
        })

    # Summary Health Verdict
    has_any_tracking = bool(ga4_ids or gtm_ids or has_matomo or clarity_ids or meta_pixel_ids)
    return {
        "url": url,
        "tags": {
            "google_analytics_4": ga4_ids,
            "google_tag_manager": gtm_ids,
            "universal_analytics_legacy": ua_ids,
            "matomo": {
                "active": has_matomo,
                "site_ids": matomo_sites,
                "tracker_urls": matomo_urls,
            },
            "clarity": clarity_ids,
            "meta_pixel": meta_pixel_ids,
            "bing_uet": bing_uet_ids,
        },
        "cmps_detected": detected_cmps,
        "duplicates": duplicate_warnings,
        "static_consent_leakage": unblocked_tracking_scripts,
        "conversion_targets": {
            "tel_count": len(tel_links),
            "tel_untracked_count": sum(1 for x in tel_links if not x["has_event_tracking"]),
            "tel_examples": tel_links[:10],
            "mailto_count": len(mailto_links),
            "mailto_untracked_count": sum(1 for x in mailto_links if not x["has_event_tracking"]),
            "mailto_examples": mailto_links[:10],
            "form_count": len(forms),
            "forms": forms[:10],
        },
        "has_tracking": has_any_tracking,
        "recommendations": _build_recommendations(
            ga4_ids, gtm_ids, ua_ids, has_matomo, detected_cmps,
            duplicate_warnings, unblocked_tracking_scripts, tel_links, forms
        ),
    }


def evaluate_consent_requests(samples: list[dict]) -> dict[str, Any]:
    """Analyzes browser network traces across initial, accept, and reject states.
    
    Identifies tracker requests fired before consent (leakage) and after rejection.
    """
    sample_by_choice = {s.get("choice"): s for s in samples if isinstance(s, dict)}

    initial = sample_by_choice.get("initial")
    reject = sample_by_choice.get("reject")

    initial_leakage: list[str] = []
    reject_violations: list[str] = []

    def is_tracking_host(host: str) -> bool:
        h = host.lower()
        return any(d in h for d in (
            "google-analytics", "analytics.google", "googletagmanager", "clarity.ms",
            "doubleclick", "facebook.net", "matomo", "pixel", "hotjar", "bat.bing.com",
        ))

    if initial:
        for r in initial.get("requests", []):
            host = r.get("host", "")
            if r.get("third_party") and is_tracking_host(host):
                if host not in initial_leakage:
                    initial_leakage.append(host)

    if reject:
        for r in reject.get("requests", []):
            host = r.get("host", "")
            if r.get("third_party") and is_tracking_host(host):
                if host not in reject_violations:
                    reject_violations.append(host)

    verdict = "unauffällig"
    if initial_leakage:
        verdict = "kritisch_leakage_vor_consent"
    elif reject_violations:
        verdict = "warnung_tracker_nach_ablehnung"

    return {
        "verdict": verdict,
        "initial_state_leakage": {
            "has_leakage": bool(initial_leakage),
            "tracking_hosts_fired_before_consent": initial_leakage,
        },
        "reject_state_violations": {
            "has_violations": bool(reject_violations),
            "tracking_hosts_fired_after_reject": reject_violations,
        },
        "samples_evaluated": len(sample_by_choice),
    }


def _build_recommendations(
    ga4: list[str], gtm: list[str], ua: list[str], matomo: bool,
    cmps: list[str], duplicates: list[str], unblocked: list[dict],
    tel: list[dict], forms: list[dict]
) -> list[str]:
    recs: list[str] = []
    if ua:
        recs.append(f"Veraltetes Universal Analytics ({', '.join(ua)}) gefunden. Google hat UA eingestellt – Snippet entfernen.")
    if duplicates:
        recs.append("Doppelte Tag-Initialisierungen bereinigen, um künstlich verdoppelte Klicks/Pageviews zu verhindern.")
    if unblocked and not cmps:
        recs.append("Tracking-Skripte sind aktiv, aber kein CMP (Consent Banner) wurde erkannt. DSGVO-Einwilligung vor Ladevorgang sicherstellen.")
    elif unblocked and cmps:
        recs.append(f"Ein CMP ({', '.join(cmps)}) ist vorhanden, aber {len(unblocked)} Tracking-Skripte sind ohne Blockier-Attribute eingebunden. Skripte dem CMP unterordnen.")
    if any(not x["has_event_tracking"] for x in tel):
        recs.append("Telefonklicks (tel:) besitzen keine Klick-Event-Handler. Conversion-Events in GA4/Matomo für Anrufe einrichten.")
    if forms and all(not f["has_event_tracking"] for f in forms):
        recs.append("Kontaktformulare besitzen keine dedizierte Event-Attribution bei Absendung. Formular-Conversions prüfen.")
    return recs
