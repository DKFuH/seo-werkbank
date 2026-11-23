"""robots.txt parsing and matching following RFC 9309 (wildcards, ``$`` anchors, longest match wins)."""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .globmatch import MAX_PATTERN_LENGTH, robots_match


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[bool, str]] = field(default_factory=list)  # (allow, pattern)
    crawl_delay: float | None = None


class RobotsRules:
    def __init__(self, text: str = "", status: int | None = 200) -> None:
        self.status = status
        self.sitemaps: list[str] = []
        self.groups: list[_Group] = []
        self.errors: list[str] = []
        self.present = bool(text.strip()) and status == 200
        # Content-Signal lines (contentsignals.org, used by Cloudflare): [(agents of the group, {key: value})]
        self.content_signals: list[tuple[list[str], dict[str, str]]] = []
        # Agents fully disallowed inside a "# BEGIN Cloudflare Managed content" section (added by Cloudflare's
        # AI crawl control, often without the site owner editing robots.txt). None = no managed section.
        self.cloudflare_managed_blocks: list[str] | None = None
        # RFC 9309: 4xx => no restrictions; 5xx/unreachable => assume complete disallow.
        self.disallow_all = status is not None and status >= 500
        if self.present:
            self._parse(text)
            self._cloudflare_section(text)

    def _cloudflare_section(self, text: str) -> None:
        lower = text.lower()
        marker = "# begin cloudflare managed content"
        start = lower.find(marker)
        if start < 0:
            return
        end = lower.find("# end cloudflare managed content", start)
        # Parse only the part after the marker; the marker itself would trigger this method again.
        section = RobotsRules(text[start + len(marker):end if end > 0 else len(text)], 200)
        self.cloudflare_managed_blocks = sorted({a for g in section.groups for a in g.agents
                                                 if a != "*" and any(not allow and pat == "/" for allow, pat in g.rules)})

    def _parse(self, text: str) -> None:
        group: _Group | None = None
        expecting_agents = False
        for n, raw in enumerate(text.splitlines()[:5000], 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if ":" not in line:
                self.errors.append(f"Zeile {n}: kein Paar 'Feld: Wert'")
                continue
            key, value = (x.strip() for x in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if group is None or not expecting_agents:
                    group = _Group()
                    self.groups.append(group)
                group.agents.append(value.lower())
                expecting_agents = True
                continue
            if key == "sitemap":
                if value:
                    self.sitemaps.append(value)
                continue
            expecting_agents = False
            if key in ("allow", "disallow"):
                if group is None:
                    self.errors.append(f"Zeile {n}: Regel steht vor jeder User-agent-Zeile")
                    continue
                if value and len(value) > MAX_PATTERN_LENGTH:
                    self.errors.append(f"Zeile {n}: Regel länger als {MAX_PATTERN_LENGTH} Zeichen, ignoriert")
                elif value:
                    if not value.startswith(("/", "*")):
                        self.errors.append(f"Zeile {n}: Pfad '{value}' sollte mit '/' beginnen")
                        value = "/" + value
                    group.rules.append((key == "allow", value))
            elif key == "crawl-delay":
                try:
                    if group:
                        group.crawl_delay = float(value)
                except ValueError:
                    self.errors.append(f"Zeile {n}: ungültiges Crawl-delay '{value}'")
            elif key == "content-signal":
                signals = {}
                for part in value.split(","):
                    if "=" in part:
                        k, v = (x.strip().lower() for x in part.split("=", 1))
                        if k:
                            signals[k] = v
                if signals:
                    self.content_signals.append((list(group.agents) if group else ["*"], signals))
            elif key not in ("host", "clean-param", "request-rate", "visit-time", "noindex"):
                self.errors.append(f"Zeile {n}: unbekannte Anweisung '{key}'")

    def _group_for(self, user_agent: str) -> list[_Group]:
        ua = user_agent.lower()
        best: list[_Group] = []
        best_len = -1
        for g in self.groups:
            for a in g.agents:
                if a != "*" and a in ua and len(a) > best_len:
                    best, best_len = [g], len(a)
                elif a != "*" and a in ua and len(a) == best_len:
                    best.append(g)
        if best:
            return best
        return [g for g in self.groups if "*" in g.agents]

    def allowed(self, url: str, user_agent: str = "*") -> bool:
        if self.disallow_all:
            return False
        if not self.present:
            return True
        p = urlsplit(url)
        path = (p.path or "/") + (f"?{p.query}" if p.query else "")
        if path == "/robots.txt":
            return True
        verdict, length = True, -1
        for g in self._group_for(user_agent):
            for allow, pattern in g.rules:
                if robots_match(pattern, path):
                    plen = len(pattern)
                    if plen > length or (plen == length and allow):
                        verdict, length = allow, plen
        return verdict

    def crawl_delay(self, user_agent: str = "*") -> float | None:
        delays = [g.crawl_delay for g in self._group_for(user_agent) if g.crawl_delay is not None]
        return max(delays) if delays else None

    def blocks_everything(self, user_agent: str = "*") -> bool:
        return not self.allowed("https://x/", user_agent)
