import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Send, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, chartColors, type Column, DataTable, EmptyState, ErrorBox, Field, Notice, PageHeader, SearchInput, Select, Spinner, Stat, Textarea, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum } from "../lib/format";

const SITE_KEY = "seotk.bing.site";
const tooltipStyle = { background: "#0f172a", border: "none", borderRadius: 8, color: "#f1f5f9", fontSize: 12 };
const axisTick = { fontSize: 11, fill: "#94a3b8" };

type Source = "all" | "new_changed" | "new" | "changed" | "removed" | "manual";

function IndexNowPanel({ siteId }: { siteId: number }) {
  const qc = useQueryClient();
  const [source, setSource] = useState<Source>("all");
  const [manual, setManual] = useState("");
  const status = useQuery({ queryKey: ["indexnow", siteId], queryFn: () => api.get(`/sites/${siteId}/indexnow/status`), retry: false });
  const submit = useMutation({
    mutationFn: () => api.post(`/sites/${siteId}/indexnow/submit`, {
      source, urls: source === "manual" ? manual.split(/\s+/).map((u) => u.trim()).filter(Boolean) : [],
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["indexnow", siteId] }),
  });

  if (status.isLoading) return <Card title="IndexNow"><Spinner /></Card>;
  if (status.error) return <Card title="IndexNow"><ErrorBox error={status.error} onRetry={() => status.refetch()} /></Card>;
  const s = status.data;
  const c = s.candidates ?? {};
  const counts: Record<Exclude<Source, "manual">, number> = {
    new: c.new_count ?? 0, changed: c.changed_count ?? 0, removed: c.removed_count ?? 0,
    new_changed: (c.new_count ?? 0) + (c.changed_count ?? 0), all: (c.new_count ?? 0) + (c.changed_count ?? 0) + (c.removed_count ?? 0),
  };
  const lists: Record<Exclude<Source, "manual">, string[]> = {
    new: c.new ?? [], changed: c.changed ?? [], removed: c.removed ?? [],
    new_changed: [...(c.new ?? []), ...(c.changed ?? [])], all: [...(c.new ?? []), ...(c.changed ?? []), ...(c.removed ?? [])],
  };
  const count = source === "manual" ? manual.split(/\s+/).filter(Boolean).length : counts[source];
  const preview: string[] = source === "manual" ? [] : lists[source];

  return (
    <Card title="IndexNow" description="Meldet neue und geänderte URLs an Bing und weitere IndexNow-Suchmaschinen. Ein Hinweis, keine Indexierungsgarantie; Google nimmt nicht teil.">
      {!s.configured ? (
        <Notice tone="warn">Noch kein IndexNow-Schlüssel hinterlegt. <Link to="/settings" className="font-medium underline">Schlüssel in den Einstellungen erzeugen</Link></Notice>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {s.key_file?.ok
              ? <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              : <XCircle className="h-4 w-4 text-red-600" />}
            <span className="font-medium">Schlüsseldatei:</span>
            <span>{s.key_file?.message}</span>
            {s.key_file?.key_location && <Url href={s.key_file.key_location} className="text-xs" />}
          </div>
          {!s.key_file?.ok && <p className="text-xs text-slate-500 dark:text-slate-400">Ohne gültige Schlüsseldatei lehnen die Suchmaschinen Meldungen mit HTTP 403 ab.</p>}
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Welche URLs?">
              <Select value={source} onChange={(e) => setSource(e.target.value as Source)} className="w-auto">
                <option value="all">Neu, geändert und gelöscht seit vorherigem Crawl</option>
                <option value="new_changed">Neu + geändert</option>
                <option value="new">Nur neue URLs</option>
                <option value="changed">Nur geänderte Inhalte</option>
                <option value="removed">Nur gelöschte URLs (404/410)</option>
                <option value="manual">Eigene Liste</option>
              </Select>
            </Field>
            <Button variant="primary" icon={<Send className="h-4 w-4" />} loading={submit.isPending} disabled={!count} onClick={() => submit.mutate()}>
              {fmtInt(count ?? 0)} URL{count === 1 ? "" : "s"} melden
            </Button>
          </div>
          {source === "manual" ? (
            <Textarea rows={5} value={manual} onChange={(e) => setManual(e.target.value)} placeholder="Eine URL pro Zeile, nur von dieser Website" className="w-full font-mono text-xs" />
          ) : !c.previous_crawl_id ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Für den Vergleich braucht es zwei abgeschlossene Crawls. Bis dahin: eigene Liste nutzen.</p>
          ) : (
            <div className="text-sm">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Neu oder inhaltlich geändert: indexierbare HTML-Seiten des letzten Crawls. Gelöscht: im vorherigen Crawl indexierbar, jetzt 404 oder 410.
                Bing empfiehlt, Änderungen möglichst laufend statt gebündelt zu melden („Avoid batch submissions when possible“).
              </p>
              {preview.length ? (
                <ul className="mt-2 max-h-48 space-y-0.5 overflow-auto">
                  {preview.slice(0, 200).map((u) => <li key={u}><Url href={u} className="text-xs" /></li>)}
                </ul>
              ) : <p className="mt-2 text-slate-500">Keine neuen oder geänderten URLs.</p>}
            </div>
          )}
          {submit.error ? <ErrorBox error={submit.error} /> : null}
          {submit.data && (
            <Notice tone={submit.data.ok ? "success" : "warn"}>
              HTTP {submit.data.status_code}: {submit.data.message} {fmtInt(submit.data.submitted)} URL(s) gesendet.
              {submit.data.rejected_count ? ` ${submit.data.rejected_count} URL(s) eines anderen Hosts ausgelassen.` : ""}
            </Notice>
          )}
        </div>
      )}
    </Card>
  );
}

function BingWebmaster({ siteId }: { siteId: number }) {
  const [bingSite, setBingSite] = useState<string>(() => { try { return localStorage.getItem(SITE_KEY) ?? ""; } catch { return ""; } });
  const [search, setSearch] = useState("");
  useEffect(() => { try { localStorage.setItem(SITE_KEY, bingSite); } catch { /* ignore */ } }, [bingSite]);
  const sites = useQuery({ queryKey: ["bing-sites"], queryFn: () => api.get("/bing/sites"), retry: false });
  const q = useQuery({
    queryKey: ["bing", siteId, bingSite],
    queryFn: () => api.get(`/sites/${siteId}/bing/overview`, bingSite ? { site_url: bingSite } : {}),
    enabled: !sites.error && !sites.isLoading, retry: false,
  });
  const d = q.data;
  const queries = useMemo(() => (d?.queries ?? []).filter((r: any) => !search || r.query.toLowerCase().includes(search.toLowerCase())), [d, search]);

  if (sites.isLoading) return <Card title="Bing Webmaster Tools"><Spinner /></Card>;
  if (sites.error) {
    return (
      <Card title="Bing Webmaster Tools">
        <Notice tone="warn">{(sites.error as Error).message} <Link to="/settings" className="font-medium underline">Zu den Einstellungen</Link></Notice>
      </Card>
    );
  }
  const columns: Column<any>[] = [
    { key: "query", header: "Suchanfrage", render: (r) => <span className="font-medium">{r.query}</span> },
    { key: "clicks", header: "Klicks", align: "right", render: (r) => fmtInt(r.clicks) },
    { key: "impressions", header: "Impressionen", align: "right", render: (r) => fmtInt(r.impressions) },
    { key: "ctr", header: "CTR", align: "right", render: (r) => `${fmtNum(r.ctr)} %` },
    { key: "position", header: "Ø Position", align: "right", tooltip: "Impressionsgewichtete Durchschnittsposition", render: (r) => (r.position == null ? "–" : fmtNum(r.position)) },
  ];
  return (
    <div className="space-y-4">
      <Card title="Bing Webmaster Tools" description="Bing liefert Suchanfragen in Wochenwerten der letzten Monate; hier summiert je Anfrage."
        actions={(
          <Select value={bingSite} onChange={(e) => setBingSite(e.target.value)} className="w-auto" aria-label="Bing-Website">
            <option value="">Automatisch (gleiche Domain)</option>
            {(sites.data?.sites ?? []).map((s: any) => <option key={s.url} value={s.url}>{s.url}{s.verified ? "" : " (nicht verifiziert)"}</option>)}
          </Select>
        )}>
        {q.isLoading ? <Spinner /> : q.error ? <ErrorBox error={q.error} onRetry={() => q.refetch()} /> : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Stat label="Klicks" value={fmtInt(d.totals.clicks)} />
            <Stat label="Impressionen" value={fmtInt(d.totals.impressions)} />
            <Stat label="Suchanfragen" value={fmtInt(d.totals.queries)} hint={<Badge>{d.site_url}</Badge>} />
          </div>
        )}
      </Card>
      {d && (
        <>
          <Card title="Crawling durch Bingbot">
            {!d.crawl_stats.length ? <EmptyState title="Keine Crawl-Statistik" description="Bing hat für diese Website noch keine Werte geliefert." /> : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={d.crawl_stats} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                  <XAxis dataKey="date" tick={axisTick} />
                  <YAxis tick={axisTick} allowDecimals={false} />
                  <ChartTooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Line type="monotone" dataKey="crawled" name="Gecrawlt" stroke={chartColors[0]} dot={false} />
                  <Line type="monotone" dataKey="in_index" name="Im Index" stroke={chartColors[1]} dot={false} />
                  <Line type="monotone" dataKey="errors" name="Crawl-Fehler" stroke={chartColors[3]} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
          <Card title="Suchanfragen" padded={false}>
            <div className="flex items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
              <SearchInput value={search} onChange={setSearch} placeholder="Suchanfragen filtern…" />
              <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">{queries.length} von {d.queries.length}</span>
            </div>
            <DataTable columns={columns} rows={queries} rowKey={(r) => r.query}
              empty={<EmptyState title="Keine Suchanfragen" description="Bing hat für diese Website noch keine Suchanfragen gemeldet." />} />
          </Card>
        </>
      )}
    </div>
  );
}

export default function Bing() {
  const { site } = useSite();
  return (
    <>
      <PageHeader title="Bing & IndexNow"
        description="Daten aus Bing Webmaster Tools und URL-Meldungen per IndexNow. Bing wird getrennt von Google betrachtet; die Audit-Zuordnung steht im Site-Audit unter dem Profil „Microsoft Bing“." />
      {!site ? <EmptyState title="Keine Website gewählt" description="Lege zuerst eine Website an." /> : (
        <div className="space-y-4">
          <IndexNowPanel siteId={site.id} />
          <BingWebmaster siteId={site.id} />
        </div>
      )}
    </>
  );
}
