import { Download } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, EmptyState, Notice, PageHeader, Spinner } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtDateTime, fmtInt } from "../lib/format";

interface Format {
  label: string;
  path: string;
  query?: Record<string, string>;
  fallback: string;
}
interface Report {
  title: string;
  description: string;
  formats: Format[];
  needsCrawl?: boolean;
}

function ReportRow({ report, disabled }: { report: Report; disabled: boolean }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = async (f: Format) => {
    setBusy(f.label);
    setError(null);
    try {
      await api.download(f.path, f.query, f.fallback);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <li className="px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1 basis-64">
          <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{report.title}</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">{report.description}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {report.formats.map((f) => (
            <Button key={f.label} size="sm" icon={<Download className="h-3.5 w-3.5" />} loading={busy === f.label} disabled={disabled || busy !== null}
              title={disabled ? "Braucht einen abgeschlossenen Crawl" : undefined} onClick={() => run(f)}>{f.label}</Button>
          ))}
        </div>
      </div>
      {error && <p role="alert" className="mt-1.5 break-words text-xs text-red-600 dark:text-red-400">Download failed: {error}</p>}
    </li>
  );
}

function Group({ title, description, reports, disabled, notice }: { title: string; description: string; reports: Report[]; disabled?: boolean; notice?: ReactNode }) {
  return (
    <Card title={title} description={description} padded={false}>
      {notice && <div className="p-3 pb-0">{notice}</div>}
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {reports.map((r) => <ReportRow key={r.title} report={r} disabled={!!disabled} />)}
      </ul>
    </Card>
  );
}

export default function Reports() {
  const { site, crawlId, loading } = useSite();
  if (loading) return <Spinner />;
  const linkClass = "font-medium text-brand-700 hover:underline dark:text-brand-300";
  if (!site) {
    return (
      <>
        <PageHeader title="Berichte" description="Alle Berichte und Exporte an einem Ort." />
        <Card><EmptyState title="Zuerst eine Website anlegen" description="Berichte werden für die ausgewählte Website erstellt." action={<Link to="/sites" className={`text-sm ${linkClass}`}>Zu den Websites</Link>} /></Card>
      </>
    );
  }

  const crawlPath = `/crawls/${crawlId}`;
  const exp = (dataset: string, format: string, label: string): Format => ({ label, path: `${crawlPath}/export`, query: { dataset, format }, fallback: `${site.domain}-${dataset}.${format}` });
  const crawlReports: Report[] = [
    { title: "Technischer Audit-Bericht", description: "Teilbare Zusammenfassung mit Score, Befunden nach Schweregrad und Beispiel-URLs je Befund.",
      formats: [{ label: "PDF", path: `${crawlPath}/report.pdf`, fallback: `seo-audit-${site.domain}.pdf` }] },
    { title: "Komplette Crawl-Arbeitsmappe", description: "Eine Excel-Datei mit Übersicht, Befunden, Seiten, defekten Links und Weiterleitungen auf eigenen Blättern.", formats: [exp("all", "xlsx", "Excel")] },
    { title: "Seiten", description: "Jede gecrawlte URL mit Status, Indexierbarkeit, Title, Wortzahl, Tiefe, eingehenden Links und Score.", formats: [exp("pages", "csv", "CSV")] },
    { title: "Befunde", description: "Jeder Befund mit Schweregrad, betroffener URL, Details und empfohlener Lösung.", formats: [exp("issues", "csv", "CSV")] },
    { title: "Links", description: "Jeder gefundene Link: Quelle, Ziel, Ankertext, intern/extern, nofollow und Zielstatus.", formats: [exp("links", "csv", "CSV")] },
    { title: "Weiterleitungen", description: "Weiterleitende URLs mit vollständiger Kette, Schrittzahl, Schleifen und Endstatus.", formats: [exp("redirects", "csv", "CSV")] },
    { title: "Crawldaten", description: "Crawl-Statistik und alle Seiten maschinenlesbar für eigene Auswertungen.", formats: [exp("pages", "json", "JSON")] },
    { title: "Erzeugte XML-Sitemap", description: "Hochladefertige Sitemap aus den indexierbaren Seiten des Crawls (erste Datei, falls mehrere nötig sind).",
      formats: [{ label: "XML", path: `${crawlPath}/sitemap.xml`, fallback: "sitemap.xml" }] },
  ];
  const siteReports: Report[] = [
    { title: "Keyword-Bericht", description: "Beobachtete Keywords mit Cluster, Intention, Search-Console-Werten und importierten Volumen. Excel ergänzt die Seitenzuordnung.",
      formats: [
        { label: "Excel", path: `/sites/${site.id}/keywords/export`, query: { format: "xlsx" }, fallback: `keywords-${site.domain}.xlsx` },
        { label: "CSV", path: `/sites/${site.id}/keywords/export`, query: { format: "csv" }, fallback: `keywords-${site.domain}.csv` },
      ] },
    { title: "Wettbewerbervergleich", description: "Direkter Vergleich dieser Website mit den angelegten Wettbewerbern.",
      formats: [{ label: "PDF", path: `/sites/${site.id}/competitors/report.pdf`, fallback: `competitors-${site.domain}.pdf` }] },
    { title: "Backlinks", description: "Importierte Backlinks. Excel ergänzt Übersichten zu Domains und Ankertexten.",
      formats: [
        { label: "Excel", path: `/sites/${site.id}/backlinks/export`, query: { format: "xlsx" }, fallback: `backlinks-${site.domain}.xlsx` },
        { label: "CSV", path: `/sites/${site.id}/backlinks/export`, query: { format: "csv" }, fallback: `backlinks-${site.domain}.csv` },
      ] },
  ];
  const accountReports: Report[] = [
    { title: "Meldungen", description: "Die 500 neuesten Monitoring-Meldungen aller deiner Websites.", formats: [{ label: "CSV", path: "/alerts/export", fallback: "alerts.csv" }] },
  ];

  return (
    <>
      <PageHeader title="Berichte" description={<>Alle Berichte und Exporte für <span className="font-medium text-slate-700 dark:text-slate-200">{site.name}</span>.</>} />
      <div className="space-y-4">
        <Group title="Crawl-Berichte" disabled={crawlId === null} reports={crawlReports}
          description={crawlId !== null && site.last_crawl ? `Aus Crawl #${crawlId} · ${fmtInt(site.last_crawl.pages_crawled)} URLs · ${fmtDateTime(site.last_crawl.finished_at)}` : "Aus dem letzten abgeschlossenen Crawl"}
          notice={crawlId === null ? (
            <Notice tone="warn">
              {site.active_crawl ? "Diese Berichte werden frei, sobald der laufende Crawl fertig ist. " : "Diese Berichte brauchen einen abgeschlossenen Crawl. "}
              <Link to="/crawler" className={linkClass}>{site.active_crawl ? "Fortschritt ansehen" : "Crawl starten"}</Link>
            </Notice>
          ) : undefined} />
        <Group title="Website-Berichte" description="Aus Daten, die du für diese Website erfasst oder importierst. Dateien können leer sein, solange nichts angelegt ist." reports={siteReports} />
        <Group title="Konto" description="Unabhängig von der ausgewählten Website" reports={accountReports} />
        <p className="text-xs text-slate-500 dark:text-slate-400">Älterer Crawl gebraucht? Einzelne Crawls lassen sich auf der Seite <Link to="/crawler" className={linkClass}>Crawler</Link> exportieren.</p>
      </div>
    </>
  );
}
