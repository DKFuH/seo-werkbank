"""Privacy-conscious access-log import and 404 monitoring."""
from __future__ import annotations

import asyncio
import os
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db, session_scope
from ..jobs import JobLimitError, jobs
from ..models import Log404, LogAggregate, LogImport, Page, RedirectRule, User
from ..security.auth import current_user, get_site_for
from ..services.log_parser import parse_file
from ..services.redirects import normalise_url
from .deps import latest_crawl

router = APIRouter(tags=["log-analysis"])


def _imports(db: Session, site_id: int) -> list[LogImport]:
    return list(db.scalars(select(LogImport).where(LogImport.site_id == site_id).order_by(LogImport.id.desc()).limit(50)))


def _out(record: LogImport) -> dict:
    return {"id": record.id, "filename": record.filename, "format": record.format,
            "state": record.state, "lines_total": record.lines_total,
            "lines_parsed": record.lines_parsed, "lines_skipped": record.lines_skipped,
            "period_start": record.period_start.isoformat() if record.period_start else None,
            "period_end": record.period_end.isoformat() if record.period_end else None,
            "created_at": record.created_at.isoformat()}


def _import_for(db: Session, site_id: int, import_id: int) -> LogImport:
    record = db.scalar(select(LogImport).where(LogImport.site_id == site_id, LogImport.id == import_id))
    if not record:
        raise HTTPException(404, "Log-Import nicht gefunden")
    return record


def _process_import(import_id: int, temp_path: str, compressed: bool, fmt: str) -> dict:
    report = parse_file(temp_path, compressed=compressed, fmt=fmt)
    with session_scope() as db:
        record = db.get(LogImport, import_id)
        if record is None:
            return {"deleted": True}
        record.lines_total = report["lines_total"]
        record.lines_parsed = report["lines_parsed"]
        record.lines_skipped = report["lines_skipped"]
        record.period_start = report["period_start"]
        record.period_end = report["period_end"]
        for (day, path, status, agent), count in report["groups"].items():
            db.add(LogAggregate(import_id=import_id, day=day, path=path, status=status,
                                agent_class=agent, count=count))
        for (path, host, agent), (count, low, high) in report["not_found"].items():
            db.add(Log404(import_id=import_id, path=path, referrer_host=host,
                          agent_class=agent, count=count, first_seen=low, last_seen=high))
        record.state = "completed"
    return {"import_id": import_id, "lines_parsed": report["lines_parsed"]}


@router.post("/sites/{site_id}/logs/import")
async def upload_logs(site_id: int, file: UploadFile = File(...), fmt: str = Form("auto"),
                      user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    filename = Path(file.filename or "access.log").name
    if not filename.lower().endswith((".log", ".txt", ".gz")):
        raise HTTPException(415, "Nur .log, .txt und .gz erlaubt")
    if fmt not in ("auto", "combined", "common"):
        raise HTTPException(422, "Logformat ungültig")
    compressed = filename.lower().endswith(".gz")
    limit = get_settings().max_log_upload_mb * 1024 * 1024
    byte_count = 0
    path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="seo-log-", suffix=".tmp", delete=False) as fh:
            path = fh.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                byte_count += len(chunk)
                if byte_count > limit:
                    raise HTTPException(413, "Logdatei überschreitet das Upload-Limit")
                fh.write(chunk)
        if not byte_count:
            raise HTTPException(422, "Logdatei ist leer")
        record = LogImport(site_id=site.id, filename=filename[:255], format=fmt, state="processing")
        db.add(record)
        db.commit()
        db.refresh(record)

        # Bind the temporary file to its import ID so startup recovery can
        # remove only files belonging to interrupted imports.
        temp_path = os.path.join(tempfile.gettempdir(), f"seo-log-import-{record.id}-{os.path.basename(path)}")
        os.replace(path, temp_path)
        path = None

        async def work(ctx):
            try:
                ctx.update(0.05, "Analysiere Logdatei")
                result = await asyncio.to_thread(_process_import, record.id, temp_path, compressed, fmt)
                ctx.update(1.0, "Nur Aggregate gespeichert", force=True)
                return result
            except Exception:
                with session_scope() as work_db:
                    item = work_db.get(LogImport, record.id)
                    if item is not None:
                        item.state = "failed"
                raise
            finally:
                Path(temp_path).unlink(missing_ok=True)

        try:
            job_id = jobs.start("log_import", work, owner_id=user.id, site_id=site.id)
        except JobLimitError as exc:
            db.delete(record)
            db.commit()
            raise HTTPException(429, str(exc)) from exc
        # The scheduled job owns and deletes the temporary file.
        path = None
        return {"import_id": record.id, "job_id": job_id, "state": "processing",
                "note": "Rohdatei wird nach dem Import gelöscht. IP-Adressen werden nicht gespeichert."}
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


@router.get("/sites/{site_id}/logs")
def list_logs(site_id: int, user: User = Depends(current_user),
              db: Session = Depends(get_db)) -> list[dict]:
    site = get_site_for(db, user, site_id)
    return [_out(x) for x in _imports(db, site.id)]


@router.delete("/sites/{site_id}/logs/{import_id}", status_code=204)
def delete_log(site_id: int, import_id: int, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    record = _import_for(db, site.id, import_id)
    if record.state == "processing":
        raise HTTPException(409, "Laufenden Import nicht löschen")
    db.execute(delete(Log404).where(Log404.import_id == record.id))
    db.execute(delete(LogAggregate).where(LogAggregate.import_id == record.id))
    db.delete(record)
    db.commit()


@router.get("/sites/{site_id}/logs/summary")
def summary(site_id: int, import_id: int | None = None, user: User = Depends(current_user),
            db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    imports = _imports(db, site.id)
    if not imports:
        return {"imports": [], "status_counts": {}, "agent_counts": {}, "top_404": [], "googlebot_days": []}
    record = _import_for(db, site.id, import_id) if import_id else next((r for r in imports if r.state == "completed"), None)
    if record is None:
        return {"imports": [_out(r) for r in imports], "status_counts": {}, "agent_counts": {},
                "top_404": [], "googlebot_days": [], "note": "Import noch nicht abgeschlossen"}
    if record.state != "completed":
        raise HTTPException(409, "Import noch nicht abgeschlossen")
    by_status: Counter = Counter()
    by_agent: Counter = Counter()
    google_days: Counter = Counter()
    urls = set()
    for agg in db.scalars(select(LogAggregate).where(LogAggregate.import_id == record.id)):
        by_status[str(agg.status)] += agg.count
        by_agent[agg.agent_class] += agg.count
        if agg.agent_class == "googlebot_claim":
            google_days[agg.day.isoformat()] += agg.count
            urls.add(agg.path)
    top404 = list(db.scalars(select(Log404).where(Log404.import_id == record.id).order_by(Log404.count.desc()).limit(100)))
    crawl = latest_crawl(db, site.id)
    crawl_summary = {"crawl_id": None, "indexable_without_googlebot": 0, "examples": []}
    if crawl:
        indexable = [p for p in db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.indexable.is_(True)))]
        missing = [p.url for p in indexable if urlsplit(p.url).path not in urls]
        crawl_summary = {"crawl_id": crawl.id, "indexable_without_googlebot": len(missing),
                         "examples": missing[:30], "interpretation": "Kein User-Agent-Treffer im importierten Zeitraum ist kein Indexierungsbeweis"}
    return {"imports": [_out(r) for r in imports], "import_id": record.id,
            "status_counts": dict(by_status), "agent_counts": dict(by_agent),
            "googlebot_days": [{"day": d, "count": count} for d, count in sorted(google_days.items())],
            "top_404": [{"path": x.path, "referrer_host": x.referrer_host,
                         "agent_class": x.agent_class, "count": x.count,
                         "first_seen": x.first_seen.isoformat(),
                         "last_seen": x.last_seen.isoformat()} for x in top404],
            "crawl_comparison": crawl_summary,
            "privacy": "Nur aggregierte und teilweise maskierte Pfade; Bot-Namen basieren ausschließlich auf User-Agent-Angaben."}


class RedirectFrom404(BaseModel):
    path: str = Field(min_length=1, max_length=2048)
    target_url: str = Field(min_length=1, max_length=2048)


@router.post("/sites/{site_id}/logs/404/redirect", status_code=201)
def propose_404_redirect(site_id: int, body: RedirectFrom404, user: User = Depends(current_user),
                         db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if "[redacted]" in body.path:
        raise HTTPException(422, "Maskierte URLs können nicht als Redirect-Quelle verwendet werden")
    path = urlsplit(body.path)
    if path.scheme or path.netloc or path.query or path.fragment or not body.path.startswith("/"):
        raise HTTPException(422, "Nur relative Pfade ohne Querystring erlaubt")
    imports = [r.id for r in _imports(db, site.id) if r.state == "completed"]
    if not imports or not db.scalar(select(Log404.id).where(Log404.import_id.in_(imports), Log404.path == body.path)):
        raise HTTPException(404, "404-Pfad nicht in den Log-Importen gefunden")
    base = site.url.rstrip("/")
    source = normalise_url(site, base + body.path)
    target = normalise_url(site, body.target_url)
    if source == target:
        raise HTTPException(422, "Quelle und Ziel müssen verschieden sein")
    if db.scalar(select(RedirectRule.id).where(RedirectRule.site_id == site.id, RedirectRule.source_url == source)):
        raise HTTPException(409, "Regel für diese URL existiert bereits")
    rule = RedirectRule(site_id=site.id, source_url=source, target_url=target,
                        status_code=301, origin="404", state="proposed",
                        note="Vorschlag aus aggregiertem 404-Log; Ziel fachlich prüfen")
    db.add(rule)
    db.commit()
    return {"id": rule.id, "state": rule.state, "note": "Keine automatische Weiterleitung"}
