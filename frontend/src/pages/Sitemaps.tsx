import { useMutation, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, chartColors, type Column, DataTable, EmptyState, ErrorBox, KeyValue, NeedsCrawl, Notice, PageHeader,
  Pagination, Spinner, Stat, StatusCode, Tabs, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtPct, shortUrl, titleCase } from "../lib/format";

type TabId = "nonindexable" | "missing" | "canonical" | "notcrawled";
const PER_PAGE = 25;
const tooltipStyle = { background: "#0f172a", border: "none", borderRadius: 8, color: "#f8fafc", fontSize: 12 } as const;
const axisTick = { fontSize: 12, fill: "#94a3b8" } as const;

function Paged<T>({ rows, columns, rowKey, onRowClick, empty }: {
  rows: T[]; columns: Column<T>[]; rowKey: (r: T, i: number) => string | number; onRowClick?: (r: T) => void; empty: { title: string; description: string };
}) {
  const [page, setPage] = useState(1);
  return (
    <>
      <DataTable columns={columns} rows={rows.slice((page - 1) * PER_PAGE, page * PER_PAGE)} rowKey={rowKey} onRowClick={onRowClick}
        empty={<EmptyState title={empty.title} description={empty.description} />} />
      {rows.length > 0 && <Pagination page={page} perPage={PER_PAGE} total={rows.length} onPage={setPage} />}
    </>
  );
}

function MessageList({ items, tone }: { items: string[]; tone: "red" | "amber" }) {
  if (!items?.length) return <span className="text-slate-400">–</span>;
  return (
    <ul className="max-w-md space-y-1">
      {items.map((m, i) => (
        <li key={i} className="flex items-start gap-1.5 text-xs"><Badge tone={tone}>{tone === "red" ? "error" : "warning"}</Badge><span className="break-words">{m}</span></li>
      ))}
    </ul>
  );
}

export default function Sitemaps() {
  const { site, crawlId } = useSite();
  const navigate = useNavigate();
  const [tab, setTab] = useState<TabId>("nonindexable");
  const q = useQuery({ queryKey: ["sitemaps", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/sitemaps`), enabled: !!crawlId });
  const generate = useMutation({ mutationFn: () => api.download(`/crawls/${crawlId}/sitemap.xml`, undefined, "sitemap.xml") });

  const header = (
    <PageHeader title="Sitemaps & robots.txt" description="Prüft, ob die XML-Sitemaps genau die Seiten enthalten, die indexiert werden sollen, und ob robots.txt Suchmaschinen darauf hinweist."
      actions={crawlId ? <Button variant="primary" icon={<Download className="h-4 w-4" />} loading={generate.isPending} onClick={() => generate.mutate()}>sitemap.xml erzeugen</Button> : undefined} />
  );
  if (!crawlId) return <>{header}<NeedsCrawl hasSite={!!site} running={!!site?.active_crawl} /></>;
  if (q.isLoading) return <>{header}<Spinner /></>;
  if (q.error) return <>{header}<ErrorBox error={q.error} onRetry={() => q.refetch()} /></>;

  const d = q.data ?? {};
  const files: any[] = d.files ?? [];
  const nonIndexable: any[] = d.non_indexable_in_sitemap ?? [];
  const missing: any[] = d.indexable_missing_from_sitemap ?? [];
  const mismatch: any[] = d.canonical_mismatch ?? [];
  const notCrawled: string[] = d.not_crawled ?? [];
  const robots = d.robots as any | null | undefined;
  const years = Object.entries((d.lastmod_by_year ?? {}) as Record<string, number>).sort(([a], [b]) => a.localeCompare(b)).map(([year, urls]) => ({ year, urls }));
  const base = site?.url;
  const open = (r: any) => navigate(`/pages/${crawlId}/${r.page_id}`);
  const urlCell = (r: any) => <div className="max-w-xl"><Url href={r.url} label={shortUrl(r.url, base)} /></div>;

  const fileColumns: Column<any>[] = [
    { key: "url", header: "Sitemap", render: (f) => <div className="max-w-md"><Url href={f.url} /></div> },
    { key: "status", header: "Status", render: (f) => <StatusCode code={f.status} error="nicht abgerufen" /> },
    { key: "kind", header: "Typ", render: (f) => <Badge tone={f.kind === "unknown" ? "amber" : "gray"}>{f.kind === "index" ? "Sitemap-Index" : titleCase(f.kind)}</Badge> },
    { key: "urls", header: "URLs", align: "right", render: (f) => fmtInt(f.url_count) },
    { key: "source", header: "Gefunden über", render: (f) => f.source ?? "–" },
    { key: "errors", header: "Fehler", render: (f) => <MessageList items={f.errors ?? []} tone="red" /> },
    { key: "warnings", header: "Warnungen", render: (f) => <MessageList items={f.warnings ?? []} tone="amber" /> },
  ];

  return (
    <>
      {header}
      {generate.error ? <div className="mb-4"><ErrorBox error={generate.error} /></div> : null}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="Sitemap-Dateien" value={fmtInt(files.length)} tone={files.length ? undefined : "warn"} />
        <Stat label="Gelistete URLs" value={fmtInt(d.url_count)} hint={`davon ${fmtInt(d.urls_crawled)} gecrawlt`} />
        <Stat label="Mit lastmod" value={fmtInt(d.with_lastmod)} hint={d.url_count ? fmtPct(d.with_lastmod / d.url_count, 0) + " der gelisteten URLs" : undefined} />
        <Stat label="Indexierbare Seiten" value={fmtInt(d.indexable_pages)} tooltip="Vom Crawl gefundene indexierbare Seiten" />
        <Stat label="Nicht indexierbar in Sitemap" value={fmtInt(nonIndexable.length)} tone={nonIndexable.length ? "bad" : "good"} tooltip="Weiterleitungen, Fehler, noindex- oder kanonisierte URLs, die nicht gelistet sein sollten" />
        <Stat label="Indexierbar, fehlt" value={fmtInt(missing.length)} tone={missing.length ? "warn" : "good"} tooltip="Indexierbare Seiten, die in keiner Sitemap stehen" />
      </div>

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <Card title="robots.txt">
          {!robots ? (
            <EmptyState title="robots.txt nicht geprüft" description="Der Crawl hat für diese Website kein robots.txt-Ergebnis erfasst." />
          ) : (
            <KeyValue items={[
              ["Status", <span className="flex flex-wrap items-center gap-2"><StatusCode code={robots.status} />{robots.present ? <Badge tone="green">vorhanden</Badge> : <Badge tone="amber">fehlt</Badge>}
                {robots.blocks_start && <Badge tone="red" title="Die Start-URL ist für den User-Agent des Crawlers gesperrt">sperrt Start-URL</Badge>}</span>],
              ["Sitemap-Zeilen", robots.sitemaps?.length ? (
                <ul className="space-y-1">{robots.sitemaps.map((s: string) => <li key={s}><Url href={s} /></li>)}</ul>
              ) : <span className="text-amber-700 dark:text-amber-300">Keine. Eine Zeile „Sitemap: https://…“ ergänzen, damit Crawler die Sitemap finden.</span>],
              ["Syntaxfehler", robots.errors?.length ? (
                <ul className="list-disc space-y-1 pl-4 text-red-700 dark:text-red-300">{robots.errors.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul>
              ) : <Badge tone="green">keine</Badge>],
              ["Crawl-delay", robots.crawl_delay === null || robots.crawl_delay === undefined ? "nicht gesetzt" : `${robots.crawl_delay} s`],
            ]} />
          )}
        </Card>
        <Card title="lastmod nach Jahr" description="Wie aktuell die gelisteten URLs laut Angabe geändert wurden">
          {years.length === 0 ? (
            <EmptyState title="Keine lastmod-Werte" description="Keine gelistete URL hat ein <lastmod>-Datum. Korrekte lastmod-Werte helfen Suchmaschinen beim Priorisieren des Recrawls." />
          ) : (
            <div className="h-56" role="img" aria-label="Sitemap-URLs nach lastmod-Jahr">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={years} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" vertical={false} />
                  <XAxis dataKey="year" tick={axisTick} tickLine={false} axisLine={{ stroke: "#94a3b855" }} />
                  <YAxis allowDecimals={false} tick={axisTick} tickLine={false} axisLine={false} width={44} />
                  <ChartTooltip cursor={{ fill: "#94a3b822" }} contentStyle={tooltipStyle} labelStyle={{ color: "#f8fafc" }} itemStyle={{ color: "#f8fafc" }} />
                  <Bar dataKey="urls" name="URLs" fill={chartColors[0]} radius={[4, 4, 0, 0]} maxBarSize={56} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <Card padded={false} title="Sitemap-Dateien" className="mb-4">
        <DataTable columns={fileColumns} rows={files} rowKey={(f, i) => `${f.url}-${i}`}
          empty={<EmptyState title="Keine Sitemap gefunden" description="Weder über robots.txt noch unter den üblichen /sitemap.xml-Pfaden gefunden. Mit „sitemap.xml erzeugen“ aus diesem Crawl eine anlegen." />} />
      </Card>

      <Tabs<TabId> value={tab} onChange={setTab} tabs={[
        { id: "nonindexable", label: "Nicht indexierbare URLs in der Sitemap", count: nonIndexable.length },
        { id: "missing", label: "Indexierbare Seiten fehlen in der Sitemap", count: missing.length },
        { id: "canonical", label: "Canonical-Abweichungen", count: mismatch.length },
        { id: "notcrawled", label: "Gelistet, aber nicht gecrawlt", count: notCrawled.length },
      ]} />
      <Card padded={false} className="mb-4">
        {tab === "nonindexable" && (
          <Paged rows={nonIndexable} rowKey={(r) => r.page_id} onRowClick={open}
            empty={{ title: "Sitemap ist sauber", description: "Jede gecrawlte URL aus der Sitemap ist indexierbar." }}
            columns={[
              { key: "url", header: "URL", render: urlCell },
              { key: "status", header: "Status", render: (r) => <StatusCode code={r.status_code} /> },
              { key: "reason", header: "Warum nicht indexierbar", render: (r) => (r.reason ? titleCase(String(r.reason)) : "–") },
            ]} />
        )}
        {tab === "missing" && (
          <Paged rows={missing} rowKey={(r) => r.page_id} onRowClick={open}
            empty={{ title: "Nichts fehlt", description: "Jede indexierbare Seite aus dem Crawl steht in einer Sitemap." }}
            columns={[
              { key: "url", header: "URL", render: urlCell },
              { key: "inlinks", header: "Eingehend", align: "right", render: (r) => fmtInt(r.inlinks) },
            ]} />
        )}
        {tab === "canonical" && (
          <Paged rows={mismatch} rowKey={(r) => r.page_id} onRowClick={open}
            empty={{ title: "Keine Canonical-Abweichungen", description: "Jede gelistete URL ist ihr eigenes Canonical." }}
            columns={[
              { key: "url", header: "URL in der Sitemap", render: urlCell },
              { key: "canonical", header: "Angegebenes Canonical", render: (r) => <div className="max-w-xl"><Url href={r.canonical} label={shortUrl(r.canonical, base)} /></div> },
            ]} />
        )}
        {tab === "notcrawled" && (
          <Paged rows={notCrawled.map((url) => ({ url }))} rowKey={(r, i) => `${r.url}-${i}`}
            empty={{ title: "Alle gelisteten URLs gecrawlt", description: "Der Crawl hat jede URL aus den Sitemaps besucht." }}
            columns={[{ key: "url", header: "URL (bis zu 200)", render: urlCell }]} />
        )}
      </Card>
      {tab === "notcrawled" && notCrawled.length > 0 && (
        <div className="mb-4"><Notice tone="warn">Diese URLs wurden nicht besucht, meist wegen des URL-Limits oder einer Sperre in robots.txt. Auf der Crawler-Seite das Limit erhöhen.</Notice></div>
      )}

      <div className="space-y-3">
        <Notice>
          <strong>sitemap.xml erzeugen</strong> lädt eine aus diesem Crawl gebaute Sitemap herunter. Sie enthält nur indexierbare, kanonische Seiten mit Status 200. Weiterleitungen, Fehler, noindex-Seiten und
          kanonisierte Duplikate bleiben draußen. Websites mit mehr als 50.000 URLs werden aufgeteilt; der Download ist der erste Teil.
        </Notice>
        {d.indexing_note && <Notice>{d.indexing_note}</Notice>}
      </div>
    </>
  );
}
