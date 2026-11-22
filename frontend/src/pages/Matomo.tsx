import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Card, type Column, DataTable, EmptyState, ErrorBox, Field, Notice, PageHeader, SearchInput, Select, Spinner, Stat, Url, chartColors,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt } from "../lib/format";

const SITE_KEY = "seotk.matomo.site";
const fmtSec = (s: number | null | undefined) => (s === null || s === undefined ? "–" : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")} min`);
const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${Math.round(v)} %`);

function Bars({ rows }: { rows: { label: string; visits: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.visits));
  if (!rows.length) return <p className="text-sm text-slate-500">keine Daten</p>;
  return (
    <ul className="space-y-1.5 text-sm">
      {rows.map((r) => (
        <li key={r.label}>
          <div className="flex justify-between gap-2"><span className="truncate">{r.label}</span><span className="tabular-nums">{fmtInt(r.visits)}</span></div>
          <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800"><div className="h-full rounded-full bg-brand-600" style={{ width: `${(r.visits / max) * 100}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}

export default function Matomo() {
  const { site } = useSite();
  const [days, setDays] = useState("30");
  const [idSite, setIdSite] = useState<string>(() => { try { return localStorage.getItem(SITE_KEY) ?? ""; } catch { return ""; } });
  const [search, setSearch] = useState("");
  useEffect(() => { try { localStorage.setItem(SITE_KEY, idSite); } catch { /* ignore */ } }, [idSite]);

  const sites = useQuery({ queryKey: ["matomo-sites"], queryFn: () => api.get("/matomo/sites"), retry: false });
  const q = useQuery({
    queryKey: ["matomo", site?.id, days, idSite],
    queryFn: () => api.get(`/sites/${site!.id}/matomo/overview`, { days, ...(idSite ? { id_site: idSite } : {}) }),
    enabled: !!site && !sites.error, retry: false,
  });
  const d = q.data;
  const pages = useMemo(() => (d?.pages ?? []).filter((p: any) => !search || p.url.toLowerCase().includes(search.toLowerCase()) || (p.title ?? "").toLowerCase().includes(search.toLowerCase())), [d, search]);

  const pageColumns: Column<any>[] = [
    { key: "url", header: "Seite", render: (p) => (
      <div className="max-w-md">
        {p.page_id && d?.crawl_id ? <Link to={`/pages/${d.crawl_id}/${p.page_id}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">{p.title || p.label}</Link>
          : <span className="font-medium">{p.title || p.label}</span>}
        <Url href={p.url} className="block text-xs" />
        {!p.in_crawl && <Badge tone="gray">nicht im Crawl</Badge>}
        {p.in_crawl && p.indexable === false && <Badge tone="amber">nicht indexierbar</Badge>}
      </div>
    ) },
    { key: "visits", header: "Besuche", align: "right", render: (p) => fmtInt(p.visits) },
    { key: "entries", header: "Einstiege", align: "right", render: (p) => fmtInt(p.entries) },
    { key: "bounce", header: "Absprung", align: "right", tooltip: "Absprungrate als Einstiegsseite", render: (p) => (p.entries ? pct(p.entry_bounce_rate) : "–") },
    { key: "time", header: "Ø Zeit", align: "right", render: (p) => fmtSec(p.avg_time) },
    { key: "words", header: "Wörter", align: "right", render: (p) => fmtInt(p.word_count) },
    { key: "inlinks", header: "Int. Links", align: "right", tooltip: "Interne Links auf die Seite laut Crawl", render: (p) => fmtInt(p.inlinks) },
    { key: "issues", header: "Befunde", align: "right", render: (p) => fmtInt(p.issues) },
  ];

  return (
    <div>
      <PageHeader title="Matomo" description="Besucherdaten aus Matomo, verknüpft mit dem letzten Crawl: welche Seiten Besuche bekommen, wie sie als Einstieg funktionieren und welche indexierbaren Seiten keinen einzigen Besuch haben." />
      <div className="space-y-4">
        {sites.error ? (
          <Notice tone="warn">{(sites.error as Error).message} <Link to="/settings" className="font-medium underline">Zu den Einstellungen</Link></Notice>
        ) : (
          <Card>
            <div className="flex flex-wrap items-end gap-3">
              <Field label="Zeitraum">
                <Select value={days} onChange={(e) => setDays(e.target.value)}>
                  {[["7", "7 Tage"], ["30", "30 Tage"], ["90", "90 Tage"], ["365", "12 Monate"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </Select>
              </Field>
              <Field label="Matomo-Website">
                <Select value={idSite} onChange={(e) => setIdSite(e.target.value)}>
                  <option value="">automatisch (gleiche Domain)</option>
                  {(sites.data?.sites ?? []).map((s: any) => <option key={s.id} value={s.id}>{s.id} · {s.name}</option>)}
                </Select>
              </Field>
            </div>
          </Card>
        )}

        {!site && <Card><EmptyState title="Keine Website ausgewählt" /></Card>}
        {q.isLoading && <Card><Spinner label="Matomo wird abgefragt…" /></Card>}
        {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}

        {d && (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
              <Stat label="Besuche" value={fmtInt(d.summary.visits)} />
              <Stat label="Besucher" value={fmtInt(d.summary.visitors)} />
              <Stat label="Aktionen/Besuch" value={d.summary.actions_per_visit?.toFixed(1)} />
              <Stat label="Ø Besuchsdauer" value={fmtSec(d.summary.avg_time)} />
              <Stat label="Absprungrate" value={pct(d.summary.bounce_rate)} />
              <Stat label="Conversions" value={fmtInt(d.goals.conversions)} hint={d.goals.rate ? `${d.goals.rate} % Rate` : undefined} />
            </div>

            {d.series?.length > 1 && (
              <Card title="Besuche pro Tag">
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={d.series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <ChartTooltip />
                      <Line dataKey="visits" name="Besuche" stroke={chartColors[0]} dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}

            <div className="grid gap-4 lg:grid-cols-4">
              <Card title="Kanäle"><Bars rows={d.channels} /></Card>
              <Card title="Suchmaschinen"><Bars rows={d.search_engines} /></Card>
              <Card title="Verweisende Websites"><Bars rows={d.websites.slice(0, 10)} /></Card>
              <Card title="Geräte"><Bars rows={d.devices} /></Card>
            </div>

            {d.goals.per_goal?.length > 0 && (
              <Card title="Ziele">
                <div className="flex flex-wrap gap-2">{d.goals.per_goal.map((g: any) => <Badge key={g.id} tone="green">{g.name}: {fmtInt(g.conversions)} ({g.rate} %)</Badge>)}</div>
              </Card>
            )}

            {!d.crawl_id && <Notice tone="warn">Für diese Website gibt es noch keinen abgeschlossenen Crawl; Crawl-Spalten bleiben leer.</Notice>}

            <Card padded={false} title={`Seiten mit Besuchen (${fmtInt(d.pages.length)})`} actions={<SearchInput value={search} onChange={setSearch} placeholder="URL oder Titel filtern…" />}>
              <div className="max-h-[40rem] overflow-y-auto">
                <DataTable dense columns={pageColumns} rows={pages.slice(0, 500)} rowKey={(p: any) => p.key} empty={<EmptyState title="Keine Seiten" />} />
              </div>
            </Card>

            {d.crawl_id && (
              <Card padded={false} title={`Indexierbare Seiten ohne Besuch (${fmtInt(d.no_traffic.length)})`}
                description="Im Zeitraum kein einziger Matomo-Besuch. Kandidaten für bessere interne Verlinkung, Überarbeitung oder Zusammenlegung (wenig interne Links zuerst).">
                <div className="max-h-[28rem] overflow-y-auto">
                  <DataTable dense rows={d.no_traffic} rowKey={(p: any) => p.url} columns={[
                    { key: "u", header: "Seite", render: (p: any) => (
                      <div className="max-w-xl">
                        {p.page_id ? <Link to={`/pages/${d.crawl_id}/${p.page_id}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">{p.title || p.url}</Link> : p.title}
                        <Url href={p.url} className="block text-xs" />
                      </div>
                    ) },
                    { key: "w", header: "Wörter", align: "right", render: (p: any) => fmtInt(p.word_count) },
                    { key: "i", header: "Int. Links", align: "right", render: (p: any) => fmtInt(p.inlinks) },
                  ]} empty={<EmptyState title="Jede indexierbare Seite hatte Besuche" />} />
                </div>
              </Card>
            )}
            <Notice>Matomo zählt nur Besuche mit Einwilligung bzw. ohne Tracking-Blocker; Seiten „ohne Besuch“ können trotzdem Aufrufe haben.</Notice>
          </>
        )}
      </div>
    </div>
  );
}
