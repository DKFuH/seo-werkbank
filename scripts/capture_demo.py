"""Capture genuine application screenshots and a short guided WebM video.

Run against your OWN running installation after a first account is created.
Never use real customer data in the screenshots or video.
Requires: pip install playwright && playwright install chromium

SEO_DEMO_URL=http://127.0.0.1:8000
SEO_DEMO_EMAIL=...
SEO_DEMO_PASSWORD=...
python scripts/capture_demo.py

Outputs locally to docs/media/generated/ (ignored by Git). Review captures
before intentionally committing selected screenshots/videos to the repository.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE = os.getenv("SEO_DEMO_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.getenv("SEO_DEMO_EMAIL")
PASSWORD = os.getenv("SEO_DEMO_PASSWORD")
OUT = Path("docs/media/generated")
SCREENS = [("/", "01-dashboard"), ("/crawler", "02-crawler"),
           ("/keywords", "03-keywords"), ("/search-console", "04-search-console"),
           ("/pagespeed", "05-pagespeed"), ("/help", "06-help")]


async def main() -> None:
    if not EMAIL or not PASSWORD:
        raise SystemExit("Set SEO_DEMO_EMAIL and SEO_DEMO_PASSWORD in the environment")
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900},
                                            record_video_dir=str(OUT), record_video_size={"width": 1440, "height": 900})
        page = await context.new_page()
        try:
            await page.goto(BASE, wait_until="domcontentloaded")
            await page.locator('input[type="email"]').fill(EMAIL)
            await page.locator('input[type="password"]').fill(PASSWORD)
            await page.get_by_role("button", name="Anmelden").click()
            await page.get_by_role("navigation", name="Hauptnavigation").wait_for(timeout=20000)
            if await page.locator('input[type="password"]').count():
                raise RuntimeError("Login did not complete; no demo images were saved.")
            for route, filename in SCREENS:
                await page.goto(BASE + route, wait_until="networkidle")
                await page.screenshot(path=str(OUT / (filename + ".png")), full_page=False)
                await page.wait_for_timeout(500)
        finally:
            await context.close()
            await browser.close()
    print(f"Original captures saved in {OUT}. Review for secrets and personal data before publishing.")


if __name__ == "__main__":
    asyncio.run(main())
