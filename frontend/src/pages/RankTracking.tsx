import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import RankProviderMeasurements from "../components/RankProviderMeasurements";
import { fmtPos, Movement, PositionChart, type TrendPoint } from "../components/RankCharts";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, Notice, PageHeader, SearchInput, Select, Spinner, Stat, Tabs } from "../components/ui";
import { api } from "../lib/api";
import LocalRankPanel from "../components/LocalRankPanel";
import { useSite } from "../lib/context";
import { fmtDate, fmtInt } from "../lib/format";

type Row = { id: number; keyword: string; label: string | null; target_url: string | null; measurement: string; priority: number;
  position: number | null; movement: number | null; bucket: string | null; impressions: number; clicks: number; ctr: number | null;
  best_url: string | null; small_sample: boolean; url_mismatch: boolean };
type Portfolio = { has_data: boolean; device_data?: boolean; labels: string[]; rows: Row[]; trend?: TrendPoint[]; granularity?: "day" | "week";
  period?: { start: string; end: string };
  summary?: { position: number | null; movement: number | null; buckets: Record<string, number>; not_observed: number; improved: number;
    worsened: number; impressions: number; clicks: number; ctr: number | null; keywords: number } };
type QueryRow = { query: string; position: number | null; movement: number | null; impressions: number; clicks: number; ctr: number | null;
  tracked: boolean; keyword_id: number | null; top_discovery: boolean; opportunity: boolean; best_url: string | null };
type Queries = { has_data: boolean; device_data?: boolean; rows: QueryRow[]; total: number; page?: number; pages?: number;
  summary: { queries?: number; untracked?: number; top_discoveries?: number; opportunities?: number; untracked_impressions?: number; untracked_clicks?: number } };

type Tab = "portfolio" | "queries" | "provider";
const DAYS: [number, string][] = [[7, "7 Tage"], [28, "28 Tage"], [90, "3 Monate"], [180, "6 Monate"], [365, "12 Monate"]];
const DEVICES: [string, string][] = [["all", "Alle Geräte"], ["desktop", "Desktop"], ["mobile", "Mobil"], ["tablet", "Tablet"]];
const MEASUREMENT: Record<string, string> = { national: "National", lokal: "Lokal", marke: "Marke" };
const path = (u: string | null) => { if (!u) return ""; try { return new URL(u).pathname; } catch { return u; } };

function Filters({ days, setDays, device, setDevice, children }: { days: number; setDays: (v: number) => void; device: string; setDevice: (v: string) => void; children?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="w-36"><Field label="Zeitraum"><Select value={days} onChange={(e) => setDays(Number(e.target.value))}>{DAYS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field></div>
      <div className="w-36"><Field label="Gerät"><Select value={device} onChange={(e) => setDevice(e.target.value)}>{DEVICES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field></div>
      {children}
    </div>
  );
}

function NoGsc() {
  return <Card><EmptyState title="Noch keine Search-Console-Daten" description="Search Console verbinden und synchronisieren oder eine Leistungs-CSV mit Datum und Suchanfrage importieren." action={<Link to="/search-console" className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">Zur Search Console</Link>} /></Card>;
}

function AddKeyword({ siteId, onDone }: { siteId: number; onDone: () => void }) {
  const [keyword, setKeyword] = useState("");
  const [label, setLabel] = useState("");
  const [target, setTarget] = useState("");
  const [measurement, setMeasurement] = useState("national");
  const [priority, setPriority] = useState("2");
  const add = useMutation({
    mutationFn: () => api.post(`/sites/${siteId}/rank-gsc/keywords`, { keyword, label: label || null, target_url: target || null, measurement, priority: Number(priority) }),
    onSuccess: () => { setKeyword(""); setTarget(""); onDone(); },
  });
  return (
    <Card title="Zielkeyword hinzufügen" description="Die GSC-Historie des Keywords ist sofort sichtbar, sofern Google die Website dafür schon ausgespielt hat.">
      <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6 lg:items-end" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Keyword" className="lg:col-span-2"><Input required maxLength={160} value={keyword} onChange={(e) => setKeyword(e.target.value)} /></Field>
        <Field label="Label"><Input maxLength={40} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="z. B. lokal" /></Field>
        <Field label="Ziel-URL"><Input maxLength={2048} value={target} onChange={(e) => setTarget(e.target.value)} placeholder="/zielseite/" /></Field>
        <Field label="Messart"><Select value={measurement} onChange={(e) => setMeasurement(e.target.value)}>{Object.entries(MEASUREMENT).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
        <div className="flex items-end gap-2">
          <Field label="Priorität" className="w-24"><Select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="1">P1</option><option value="2">P2</option><option value="3">P3</option></Select></Field>
          <Button type="submit" variant="primary" loading={add.isPending}>Hinzufügen</Button>
        </div>
        {add.error && <div className="lg:col-span-6"><ErrorBox error={add.error} /></div>}
      </form>
    </Card>
  );
}

function PortfolioTab({ siteId }: { siteId: number }) {
  const qc = useQueryClient();
  const [days, setDays] = useState(28);
  const [device, setDevice] = useState("all");
  const [label, setLabel] = useState("");
  const [find, setFind] = useState("");
  const [bucket, setBucket] = useState("all");
  const [sort, setSort] = useState<{ key: keyof Row; dir: 1 | -1 }>({ key: "priority", dir: 1 });
  const key = ["rank-portfolio", siteId, days, device, label];
  const q = useQuery<Portfolio>({ queryKey: key, queryFn: () => api.get(`/sites/${siteId}/rank-gsc/portfolio`, { days, device, label: label || undefined }) });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["rank-portfolio", siteId] });
  const rows = useMemo(() => {
    const needle = find.trim().toLowerCase();
    const limit: Record<string, number> = { top3: 3, top10: 10, top20: 20, top50: 50 };
    return (q.data?.rows ?? []).filter((r) => (!needle || `${r.keyword} ${r.label ?? ""} ${r.best_url ?? ""}`.toLowerCase().includes(needle))
      && (bucket === "all" || (bucket === "none" ? r.position === null : r.position !== null && r.position <= limit[bucket])))
      .sort((a, b) => {
        const x = a[sort.key], y = b[sort.key];
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
      });
  }, [q.data, find, bucket, sort]);
  const th = (k: keyof Row, l: string, right = false) => (
    <th className={`px-3 py-2 font-medium ${right ? "text-right" : ""}`}>
      <button type="button" className="hover:underline" onClick={() => setSort({ key: k, dir: sort.key === k ? (sort.dir === 1 ? -1 : 1) : (k === "keyword" || k === "position" || k === "priority" ? 1 : -1) })}>
        {l}{sort.key === k ? (sort.dir === 1 ? " ↑" : " ↓") : ""}
      </button>
    </th>
  );
  if (q.isLoading) return <Spinner />;
  if (q.error) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const s = d.summary;
  return (
    <div className="space-y-4">
      <Filters days={days} setDays={setDays} device={device} setDevice={setDevice}>
        <div className="w-40"><Field label="Label"><Select value={label} onChange={(e) => setLabel(e.target.value)}><option value="">Alle Labels</option>{d.labels.map((l) => <option key={l} value={l}>{l}</option>)}</Select></Field></div>
        {d.period && <span className="pb-2 text-xs text-slate-500 dark:text-slate-400">{fmtDate(d.period.start)} – {fmtDate(d.period.end)} · gegen die {days} Tage davor</span>}
      </Filters>
      {device !== "all" && d.has_data && !d.device_data && <Notice tone="warn">Für Geräte liegen noch keine Daten vor. Search Console einmal neu synchronisieren; CSV-Exporte enthalten Suchanfrage und Gerät nicht zusammen.</Notice>}
      {!d.has_data && <NoGsc />}
      {s && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Ø Position" value={fmtPos(s.position)} hint={<><Movement value={s.movement} /> zum Vorzeitraum</>} tooltip="Nach Impressionen gewichtet, kleinere Zahl ist besser" />
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Rankings</div>
            <div className="mt-2 grid grid-cols-5 gap-1 text-center">
              {Object.entries(s.buckets).map(([b, n]) => <div key={b}><div className="text-lg font-semibold tabular-nums">{n}</div><div className="text-[11px] text-slate-500">{b}</div></div>)}
            </div>
            {s.not_observed > 0 && <div className="mt-1 text-xs text-slate-500">{s.not_observed} ohne Ausspielung</div>}
          </div>
          <Stat label="Bewegung" value={<><span className="text-emerald-600 dark:text-emerald-400">{s.improved}</span> / <span className="text-red-600 dark:text-red-400">{s.worsened}</span></>} hint="verbessert / verschlechtert" />
          <Stat label="Reale Nachfrage" value={fmtInt(s.impressions)} hint={`Impressionen · ${fmtInt(s.clicks)} Klicks · ${s.ctr === null ? "–" : s.ctr.toLocaleString("de-DE")} % CTR`} />
        </div>
      )}
      {d.has_data && d.trend && (
        <Card title="Position im Zeitverlauf" description={`Ø Position der gefilterten Zielkeywords, ${d.granularity === "week" ? "wöchentlich" : "täglich"}. Kleinere Zahl ist besser.`}>
          <PositionChart points={d.trend} granularity={d.granularity ?? "day"} />
        </Card>
      )}
      <Card title={`${rows.length} Zielkeywords`} padded={false}
        actions={<div className="flex flex-wrap gap-2">
          <div className="w-56"><SearchInput value={find} onChange={setFind} placeholder="Keyword, Label oder URL" /></div>
          <div className="w-40"><Select aria-label="Ranking-Filter" value={bucket} onChange={(e) => setBucket(e.target.value)}>
            <option value="all">Alle Positionen</option><option value="top3">Top 3</option><option value="top10">Top 10</option><option value="top20">Top 20</option><option value="top50">Top 50</option><option value="none">Nicht beobachtet</option>
          </Select></div>
        </div>}>
        {!d.rows.length ? <EmptyState title="Noch keine Zielkeywords" description="Unten ein Keyword hinzufügen oder unter „Alle GSC-Keywords“ eines übernehmen." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 text-left text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <tr>{th("keyword", "Keyword")}{th("position", "Position", true)}{th("movement", "Bewegung", true)}<th className="px-3 py-2 font-medium">Ranking-URL</th>{th("impressions", "Impressionen", true)}{th("clicks", "Klicks", true)}{th("ctr", "CTR", true)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="px-3 py-2">
                      <Link to={`/rank-tracking/keywords/${r.id}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">{r.keyword}</Link>
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        <Badge tone="gray">P{r.priority}</Badge>{r.label && <Badge tone="blue">{r.label}</Badge>}<Badge tone="gray">{MEASUREMENT[r.measurement] ?? r.measurement}</Badge>
                        {r.small_sample && <Badge tone="amber" title="Weniger als 10 Impressionen im Zeitraum">kleine Stichprobe</Badge>}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums">{fmtPos(r.position)}</td>
                    <td className="px-3 py-2 text-right tabular-nums"><Movement value={r.movement} /></td>
                    <td className="max-w-xs px-3 py-2">
                      {r.best_url ? <a href={r.best_url} target="_blank" rel="noopener noreferrer" className="break-all text-slate-700 hover:underline dark:text-slate-300">{path(r.best_url)}</a> : <span className="text-slate-400">nicht beobachtet</span>}
                      {r.url_mismatch && <div className="text-xs text-amber-600 dark:text-amber-400">Ziel: {r.target_url}</div>}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(r.impressions)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(r.clicks)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{r.ctr === null ? "—" : `${r.ctr.toLocaleString("de-DE")} %`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <AddKeyword siteId={siteId} onDone={refresh} />
    </div>
  );
}

function QueriesTab({ siteId }: { siteId: number }) {
  const qc = useQueryClient();
  const [days, setDays] = useState(28);
  const [device, setDevice] = useState("all");
  const [scope, setScope] = useState("all");
  const [bucket, setBucket] = useState("all");
  const [minImp, setMinImp] = useState(0);
  const [find, setFind] = useState("");
  const [sort, setSort] = useState({ key: "impressions", dir: "desc" });
  const [page, setPage] = useState(1);
  const params = { days, device, scope, bucket, min_impressions: minImp, q: find.trim() || undefined, sort: sort.key, dir: sort.dir, page };
  const q = useQuery<Queries>({ queryKey: ["rank-queries", siteId, params], queryFn: () => api.get(`/sites/${siteId}/rank-gsc/queries`, params), placeholderData: (p) => p });
  const adopt = useMutation({ mutationFn: (query: string) => api.post(`/sites/${siteId}/rank-gsc/adopt`, { query }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["rank-queries", siteId] }); void qc.invalidateQueries({ queryKey: ["rank-portfolio", siteId] }); } });
  const set = <T,>(fn: (v: T) => void) => (v: T) => { fn(v); setPage(1); };
  const th = (k: string, l: string, right = false) => (
    <th className={`px-3 py-2 font-medium ${right ? "text-right" : ""}`}>
      <button type="button" className="hover:underline" onClick={() => { setSort({ key: k, dir: sort.key === k && sort.dir === "desc" ? "asc" : sort.key !== k && (k === "query" || k === "position") ? "asc" : "desc" }); setPage(1); }}>
        {l}{sort.key === k ? (sort.dir === "asc" ? " ↑" : " ↓") : ""}
      </button>
    </th>
  );
  if (q.isLoading) return <Spinner />;
  if (q.error) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const s = d.summary;
  return (
    <div className="space-y-4">
      <Filters days={days} setDays={set(setDays)} device={device} setDevice={set(setDevice)}>
        <div className="w-40"><Field label="Trackingstatus"><Select value={scope} onChange={(e) => set(setScope)(e.target.value)}><option value="all">Alle Keywords</option><option value="untracked">Nur ungetrackte</option><option value="tracked">Nur Zielkeywords</option></Select></Field></div>
        <div className="w-44"><Field label="Ranking"><Select value={bucket} onChange={(e) => set(setBucket)(e.target.value)}>
          <option value="all">Alle Positionen</option><option value="opportunity">Chancen 4–20</option><option value="top3">Top 3</option><option value="top10">Top 10</option><option value="top20">Top 20</option><option value="top50">Top 50</option><option value="51plus">Ab Position 51</option>
        </Select></Field></div>
        <div className="w-44"><Field label="Mind. Impressionen"><Select value={minImp} onChange={(e) => set(setMinImp)(Number(e.target.value))}>{[0, 1, 5, 10, 25, 50, 100].map((v) => <option key={v} value={v}>{v ? `${v}+` : "Keine Grenze"}</option>)}</Select></Field></div>
        <div className="w-56"><Field label="Suchanfrage"><SearchInput value={find} onChange={set(setFind)} placeholder="Keyword filtern" /></Field></div>
      </Filters>
      {!d.has_data ? <NoGsc /> : (
        <>
          {device !== "all" && !d.device_data && <Notice tone="warn">Für Geräte liegen noch keine Daten vor. Search Console einmal neu synchronisieren.</Notice>}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Suchanfragen" value={fmtInt(s.queries)} hint="mit GSC-Daten im Zeitraum" />
            <Stat label="Nicht im Tracking" value={fmtInt(s.untracked)} hint={`${fmtInt(s.top_discoveries)} belastbare Top-3-Funde`} />
            <Stat label="Chancen" value={fmtInt(s.opportunities)} hint="ungetrackt · Position 4–20 · ab 10 Impressionen" />
            <Stat label="Ungetrackte Reichweite" value={fmtInt(s.untracked_impressions)} hint={`Impressionen · ${fmtInt(s.untracked_clicks)} Klicks`} />
          </div>
          <Card title={`${fmtInt(d.total)} Suchanfragen`} padded={false}>
            {!d.rows.length ? <EmptyState title="Keine Suchanfragen entsprechen diesem Filter" /> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-100 text-left text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <tr>{th("query", "Suchanfrage")}{th("position", "Position", true)}{th("movement", "Bewegung", true)}{th("impressions", "Impressionen", true)}{th("clicks", "Klicks", true)}{th("ctr", "CTR", true)}<th className="px-3 py-2 font-medium">Ranking-URL</th><th className="px-3 py-2 font-medium">Aktion</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {d.rows.map((r) => (
                      <tr key={r.query}>
                        <td className="px-3 py-2">
                          <div className="font-medium text-slate-900 dark:text-slate-100">{r.query}</div>
                          {r.tracked ? <Link to={`/rank-tracking/keywords/${r.keyword_id}`}><Badge tone="green">Zielkeyword</Badge></Link>
                            : r.top_discovery ? <Badge tone="blue">Top-3-Fund</Badge> : r.opportunity ? <Badge tone="amber">Chance</Badge> : <Badge tone="gray">ungetrackt</Badge>}
                        </td>
                        <td className="px-3 py-2 text-right font-semibold tabular-nums">{fmtPos(r.position)}</td>
                        <td className="px-3 py-2 text-right tabular-nums"><Movement value={r.movement} /></td>
                        <td className="px-3 py-2 text-right tabular-nums">{fmtInt(r.impressions)}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{fmtInt(r.clicks)}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{r.ctr === null ? "—" : `${r.ctr.toLocaleString("de-DE")} %`}</td>
                        <td className="max-w-xs px-3 py-2">{r.best_url ? <a href={r.best_url} target="_blank" rel="noopener noreferrer" className="break-all hover:underline">{path(r.best_url)}</a> : <span className="text-slate-400">—</span>}</td>
                        <td className="px-3 py-2">{r.tracked ? <span className="text-xs text-slate-500">Im Monitoring</span>
                          : <Button size="sm" loading={adopt.isPending && adopt.variables === r.query} onClick={() => adopt.mutate(r.query)}>Ins Monitoring</Button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {(d.pages ?? 1) > 1 && (
              <div className="flex items-center gap-2 p-4 text-sm">
                <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ Zurück</Button>
                <span>Seite {page} von {d.pages}</span>
                <Button size="sm" disabled={page >= (d.pages ?? 1)} onClick={() => setPage(page + 1)}>Weiter ›</Button>
              </div>
            )}
          </Card>
          {adopt.error && <ErrorBox error={adopt.error} />}
        </>
      )}
    </div>
  );
}

export default function RankTracking() {
  const { site } = useSite();
  const [tab, setTab] = useState<Tab>("portfolio");
  return (
    <>
      <PageHeader title="Ranktracker" description="Zielkeywords mit echten Positionen aus der Search Console, alle Suchanfragen mit Chancen und Top-3-Funden sowie Anbieter-Messungen." />
      {!site ? <Card><EmptyState title="Erst eine Website anlegen" /></Card> : (
        <>
          <Tabs<Tab> value={tab} onChange={setTab} tabs={[
            { id: "portfolio", label: "Portfolio (GSC)" }, { id: "queries", label: "Alle GSC-Keywords" }, { id: "provider", label: "Anbieter-Messungen" },
          ]} />
          {tab === "portfolio" && <PortfolioTab siteId={site.id} />}
          {tab === "queries" && <QueriesTab siteId={site.id} />}
          {tab === "provider" && <><RankProviderMeasurements /><div className="mt-5"><LocalRankPanel /></div></>}
        </>
      )}
    </>
  );
}
