export const fmtInt = (n: number | null | undefined) => (n === null || n === undefined ? "–" : Math.round(n).toLocaleString("de-DE"));

export const fmtNum = (n: number | null | undefined, digits = 1) =>
  n === null || n === undefined ? "–" : n.toLocaleString("de-DE", { maximumFractionDigits: digits });

export const fmtPct = (ratio: number | null | undefined, digits = 1) =>
  ratio === null || ratio === undefined ? "–" : `${(ratio * 100).toFixed(digits).replace(".", ",")} %`;

export function fmtBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "–";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export function fmtMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "–";
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`;
}

/** The API returns naive UTC timestamps; append Z so the browser converts them to local time. */
function parseDate(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) || iso.length <= 10 ? iso : `${iso}Z`);
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "–";
  return parseDate(iso).toLocaleDateString("de-DE", { year: "numeric", month: "short", day: "numeric" });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  return parseDate(iso).toLocaleString("de-DE", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "nie";
  const s = Math.max(0, (Date.now() - parseDate(iso).getTime()) / 1000);
  if (s < 60) return "gerade eben";
  if (s < 3600) return `vor ${Math.floor(s / 60)} Min.`;
  if (s < 86400) return `vor ${Math.floor(s / 3600)} Std.`;
  return `vor ${Math.floor(s / 86400)} Tg.`;
}

export function shortUrl(url: string, base?: string): string {
  try {
    const u = new URL(url);
    if (base && new URL(base).host === u.host) return u.pathname + u.search || "/";
    return u.host + (u.pathname === "/" ? "" : u.pathname) + u.search;
  } catch {
    return url;
  }
}

export const SEVERITIES = ["critical", "high", "medium", "low"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const SEVERITY_COLOR: Record<Severity, string> = { critical: "#dc2626", high: "#ea580c", medium: "#ca8a04", low: "#64748b" };

export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "#94a3b8";
  return score >= 85 ? "#16a34a" : score >= 65 ? "#ca8a04" : "#dc2626";
}

/** Deutsche Bezeichnungen für Werte, die das Backend als englische Schlüssel liefert. */
export const LABELS: Record<string, string> = {
  critical: "kritisch", high: "hoch", medium: "mittel", low: "niedrig",
  availability: "Erreichbarkeit", performance: "Performance", redirects: "Weiterleitungen", links: "Links", images: "Bilder",
  architecture: "Seitenarchitektur", indexability: "Indexierbarkeit", content: "Inhalt", international: "International",
  url: "URL-Struktur", security: "Sicherheit", mobile: "Mobil", html: "HTML", social: "Social Media",
  structured_data: "Strukturierte Daten", sitemap: "Sitemap", geo: "GEO / KI-Suche",
  informational: "informational", commercial: "kommerziell", transactional: "transaktional", navigational: "navigational", local: "lokal",
  queued: "in Warteschlange", running: "läuft", completed: "abgeschlossen", failed: "fehlgeschlagen", cancelled: "abgebrochen",
  pending: "ausstehend", ok: "ok", error: "Fehler", warning: "Warnung", info: "Info",
  page: "Seite", site: "Website", start: "Start", link: "Link", redirect: "Weiterleitung",
  measured: "gemessen", estimated: "geschätzt", imported: "importiert", unavailable: "nicht verfügbar",
  desktop: "Desktop", mobile_strategy: "Mobil", live: "live", lost: "verloren", unknown: "unbekannt",
  uptime: "Erreichbarkeit", metadata: "Metadaten", audit: "Audit",
  question: "Frage", suggestion: "Vorschlag", related: "verwandt",
  canonicalised: "per Canonical verwiesen", noindex: "noindex", blocked: "gesperrt", not_html: "kein HTML",
  pass: "ok", warn: "prüfen", fail: "Problem",
};
export const titleCase = (s: string) => LABELS[s] ?? s.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
