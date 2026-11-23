import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HeartPulse, RefreshCw, Settings2 } from "lucide-react";
import { useMemo, useState } from "react";
import { type Bar, type Candle, CandleChart, StatusStrip } from "../components/HealthCharts";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, Notice, PageHeader, SearchInput, Select, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtDateTime, fmtInt, timeAgo } from "../lib/format";

type Incident = { id: number; status: "open" | "resolved"; outcome: string; description: string; started_at: string;
  resolved_at: string | null; duration: string; duration_s: number };
type Health = {
  has_monitor: boolean; period: string; urls: string[]; url: string;
  monitor: { id: number; name: string; interval_minutes: number; enabled: boolean; slow_ms: number; slow_repeat: number; last_run: string | null };
  monitors: { id: number; name: string }[];
  summary: { status: "up" | "slow" | "down" | "unknown"; uptime_pct: number | null; checks: number; avg_ms: number | null; rating: string | null; last_check: string | null };
  bars: Bar[]; candles: Candle[]; incidents: Incident[]; bucket_minutes: number; hours: number;
  overview: { key: string; title: string; description: string; items: { label: string; incidents: number }[] }[];
  method: string;
};

const PERIOD_LABEL: Record<string, string> = { "24h": "Letzte 24 Stunden", "7d": "Letzte 7 Tage", "30d": "Letzte 30 Tage" };
const STATUS_HEAD: Record<string, [string, string]> = {
  up: ["UP", "text-emerald-600 dark:text-emerald-400"], slow: ["LANGSAM", "text-amber-600 dark:text-amber-400"],
  down: ["DOWN", "text-red-600 dark:text-red-400"], unknown: ["–", "text-slate-500"],
};
const RATING_TONE: Record<string, string> = { Gut: "green", Mittel: "amber", Langsam: "amber", "Sehr langsam": "red" };
const PER_PAGE = 20;

function bucketLabel(minutes: number) {
  return minutes < 60 ? `${minutes}m Gruppen` : `${minutes / 60}h Gruppen`;
}

function Settings({ h, onSaved }: { h: Health; onSaved: () => void }) {
  const [slow, setSlow] = useState(String(h.monitor.slow_ms));
  const [repeat, setRepeat] = useState(String(h.monitor.slow_repeat));
  const [interval, setInterval] = useState(String(h.monitor.interval_minutes));
  const save = useMutation({
    mutationFn: () => api.patch(`/monitors/${h.monitor.id}`, {
      interval_hours: Math.max(15, Number(interval)) / 60,
      config: { urls: h.urls, slow_ms: Number(slow), slow_repeat: Number(repeat) },
    }),
    onSuccess: onSaved,
  });
  return (
    <form className="grid gap-3 border-t border-slate-100 p-4 sm:grid-cols-4 sm:items-end dark:border-slate-800"
      onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <Field label="Alert-Grenzwert (ms)"><Input type="number" min={300} max={30000} step={100} value={slow} onChange={(e) => setSlow(e.target.value)} /></Field>
      <Field label="Langsam ab … Prüfungen in Folge"><Input type="number" min={1} max={10} value={repeat} onChange={(e) => setRepeat(e.target.value)} /></Field>
      <Field label="Prüfintervall (Minuten, ab 15)"><Input type="number" min={15} max={1440} step={5} value={interval} onChange={(e) => setInterval(e.target.value)} /></Field>
      <Button type="submit" variant="primary" loading={save.isPending}>Speichern</Button>
      {save.error && <div className="sm:col-span-4"><ErrorBox error={save.error} /></div>}
    </form>
  );
}

function Incidents({ items }: { items: Incident[] }) {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("new");
  const [page, setPage] = useState(1);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const out = items.filter((i) => (filter === "all" || (filter === "open" ? i.status === "open" : filter === "resolved" ? i.status === "resolved" : i.outcome === filter))
      && (!needle || i.description.toLowerCase().includes(needle)));
    return out.sort((a, b) => sort === "old" ? a.started_at.localeCompare(b.started_at) : sort === "long" ? b.duration_s - a.duration_s : b.started_at.localeCompare(a.started_at));
  }, [items, q, filter, sort]);
  const pages = Math.max(1, Math.ceil(rows.length / PER_PAGE));
  const shown = rows.slice((Math.min(page, pages) - 1) * PER_PAGE, Math.min(page, pages) * PER_PAGE);
  const outcomes = [...new Set(items.map((i) => i.outcome))];
  return (
    <Card title="Vorfälle" description="Zeiträume mit Ausfall oder hoher Antwortzeit, von der ersten bis zur ersten wieder guten Prüfung (90 Tage)" padded={false}>
      <div className="flex flex-wrap items-center gap-2 p-4">
        <div className="w-full sm:w-64"><SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Beschreibung suchen…" /></div>
        <div className="w-48"><Select aria-label="Filter" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1); }}>
          <option value="all">Alle</option><option value="open">Offen</option><option value="resolved">Behoben</option>
          {outcomes.map((o) => <option key={o} value={o}>{items.find((i) => i.outcome === o)?.description.replace(/^HTTP Status Code \d+ \(|\)$/g, "") ?? o}</option>)}
        </Select></div>
        <div className="ml-auto w-44"><Select aria-label="Sortieren" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="new">Neueste zuerst</option><option value="old">Älteste zuerst</option><option value="long">Längste zuerst</option>
        </Select></div>
      </div>
      {!rows.length ? <EmptyState title={items.length ? "Keine Treffer" : "Keine Vorfälle"} description={items.length ? undefined : "Alle Prüfungen waren in Ordnung."} /> : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-y border-slate-100 text-left text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <tr><th className="px-4 py-2 font-medium">Status</th><th className="px-4 py-2 font-medium">Start</th><th className="px-4 py-2 text-right font-medium">Dauer</th><th className="px-4 py-2 font-medium">Beschreibung</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {shown.map((i) => (
                <tr key={i.id}>
                  <td className="px-4 py-2"><Badge tone={i.status === "open" ? "red" : "green"}>{i.status === "open" ? "Offen" : "Behoben"}</Badge></td>
                  <td className="whitespace-nowrap px-4 py-2 tabular-nums">{fmtDateTime(i.started_at)}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-right tabular-nums">{i.duration}{i.status === "open" ? " (läuft)" : ""}</td>
                  <td className="px-4 py-2">{i.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {pages > 1 && (
        <div className="flex items-center gap-2 p-4 text-sm">
          <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</Button>
          <span>{Math.min(page, pages)} von {pages}</span>
          <Button size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>›</Button>
        </div>
      )}
    </Card>
  );
}

export default function Health() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [period, setPeriod] = useState("24h");
  const [url, setUrl] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const key = ["website-health", site?.id, period, url];
  const q = useQuery<Health>({
    queryKey: key, enabled: !!site, refetchInterval: 60_000,
    queryFn: () => api.get(`/sites/${site!.id}/website-health`, { period, url: url ?? undefined }),
  });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["website-health", site?.id] });
  const create = useMutation({ mutationFn: () => api.post(`/sites/${site!.id}/monitors`, { kind: "uptime", name: "Website Health" }), onSuccess: refresh });
  const runNow = useMutation({ mutationFn: (id: number) => api.post(`/monitors/${id}/run`), onSuccess: () => setTimeout(refresh, 4000) });

  const header = <PageHeader title="Website Health" description="Erreichbarkeit und Antwortzeit der Website, regelmäßig von diesem Server aus geprüft. Ausfälle und hohe Antwortzeiten werden als Vorfall erfasst und gemeldet." />;
  if (!site) return <>{header}<Card><EmptyState title="Erst eine Website anlegen" /></Card></>;
  if (q.isLoading) return <>{header}<Spinner /></>;
  if (q.error) return <>{header}<ErrorBox error={q.error} onRetry={() => q.refetch()} /></>;
  const h = q.data!;
  if (!h.has_monitor) {
    return (
      <>{header}
        <Card>
          <EmptyState icon={<HeartPulse className="h-6 w-6" />} title="Website Health ist noch nicht eingerichtet"
            description={`Prüft ${site.url} alle 15 Minuten auf Erreichbarkeit und Antwortzeit. Ab 2.000 ms gilt eine Antwort als langsam.`}
            action={<Button variant="primary" loading={create.isPending} onClick={() => create.mutate()}>Überwachung starten</Button>} />
          {create.error && <ErrorBox error={create.error} />}
        </Card>
      </>
    );
  }
  const s = h.summary;
  const [statusText, statusCls] = STATUS_HEAD[s.status];
  return (
    <>
      {header}
      <div className="space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Website-Status</div>
            <div className="flex items-center gap-2">
              <span className={`text-3xl font-bold ${statusCls}`}>{statusText}</span>
              {s.uptime_pct !== null && <Badge tone={s.uptime_pct >= 99.5 ? "green" : s.uptime_pct >= 98 ? "amber" : "red"}>{s.uptime_pct.toLocaleString("de-DE", { minimumFractionDigits: 2 })} %</Badge>}
            </div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {h.urls.length > 1 && (
              <div className="w-72 max-w-full"><Select aria-label="Geprüfte URL" value={h.url} onChange={(e) => setUrl(e.target.value)}>
                {h.urls.map((u) => <option key={u} value={u}>{u}</option>)}
              </Select></div>
            )}
            <div className="w-48"><Select aria-label="Zeitraum" value={period} onChange={(e) => setPeriod(e.target.value)}>
              {Object.entries(PERIOD_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Select></div>
            <Button icon={<RefreshCw className="h-4 w-4" />} loading={runNow.isPending} onClick={() => runNow.mutate(h.monitor.id)}>Jetzt prüfen</Button>
          </div>
        </div>
        {!h.monitor.enabled && <Notice tone="warn">Diese Überwachung ist pausiert. Unter Monitoring wieder aktivieren.</Notice>}

        <Card>
          <div className="mb-2 flex flex-wrap justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>{PERIOD_LABEL[h.period]}</span>
            <span>{bucketLabel(h.bucket_minutes)} · alle {h.monitor.interval_minutes} min geprüft</span>
            <span>Letzte Prüfung: {s.last_check ? `${fmtDateTime(s.last_check)} (${timeAgo(s.last_check)})` : "noch keine"}</span>
          </div>
          <StatusStrip bars={h.bars} />
        </Card>

        <Card title="Antwortzeit" padded={false}
          actions={<Button size="sm" variant="ghost" icon={<Settings2 className="h-4 w-4" />} onClick={() => setShowSettings(!showSettings)}>Einstellungen</Button>}>
          {showSettings && <Settings h={h} onSaved={() => { setShowSettings(false); refresh(); }} />}
          <div className="p-4">
            {s.checks ? <CandleChart candles={h.candles} threshold={h.monitor.slow_ms} />
              : <EmptyState title="Noch keine Prüfungen" description="Die erste Prüfung läuft spätestens in 15 Minuten, oder „Jetzt prüfen“." />}
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-100 px-4 py-3 text-sm dark:border-slate-800">
            <span className="text-slate-500 dark:text-slate-400">Durchschnittl. Antwortzeit:</span>
            {s.avg_ms !== null ? <Badge tone={RATING_TONE[s.rating ?? ""] ?? "gray"}>{fmtInt(s.avg_ms)} ms | {s.rating}</Badge> : <span>–</span>}
            <span className="ml-auto text-slate-500 dark:text-slate-400">Alert-Grenzwert:</span>
            <Badge tone="blue">{fmtInt(h.monitor.slow_ms)} ms</Badge>
            <span className="text-slate-500 dark:text-slate-400">Langsam ab:</span>
            <Badge tone="blue">{h.monitor.slow_repeat} Prüfung(en) in Folge</Badge>
          </div>
        </Card>

        <Incidents items={h.incidents} />

        <Card title="Monitoring-Übersicht" description="Welche Fehlerarten geprüft werden; die Zahl nennt die Vorfälle im gewählten Zeitraum.">
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {h.overview.map((g) => (
              <div key={g.key} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{g.title}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{g.description}</div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {g.items.map((i) => <Badge key={i.label} tone={i.incidents ? "amber" : "gray"}>{i.label}{i.incidents ? ` · ${i.incidents}` : ""}</Badge>)}
                </div>
              </div>
            ))}
          </div>
        </Card>
        <p className="text-xs text-slate-500 dark:text-slate-400">{h.method} Vorfälle erscheinen als Meldung in der App und gehen über die Benachrichtigungskanäle raus, sofern welche eingerichtet sind.</p>
      </div>
    </>
  );
}
