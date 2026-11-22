import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, ExternalLink, RefreshCw, Sparkles, Trash2, Unplug } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, chartColors, Checkbox, type Column, DataBadge, DataTable, EmptyState, ErrorBox, Field, FileButton, Input, Modal, NeedsCrawl, Notice,
  PageHeader, Pagination, ProgressBar, SearchInput, Select, Spinner, Stat, Tabs, Url,
} from "../components/ui";
import { api, ApiError } from "../lib/api";
import { type Job, type Site, useJob, useSite } from "../lib/context";
import { fmtDate, fmtInt, fmtNum, fmtPct, shortUrl } from "../lib/format";

const PER_PAGE = 50;
const dash = <span className="text-slate-400">–</span>;

/* ------------------------------------------------------------------ connection */
function ConnectionPanel({ site, onData }: { site: Site; onData: () => void }) {
  const qc = useQueryClient();
  const { refresh } = useSite();
  const [days, setDays] = useState(90);
  const [property, setProperty] = useState(site.gsc_property ?? "");
  const [jobId, setJobId] = useState<number | null>(null);
  const [syncResult, setSyncResult] = useState<Job | null>(null);
  useEffect(() => setProperty(site.gsc_property ?? ""), [site.id, site.gsc_property]);

  const status = useQuery({ queryKey: ["gsc-status"], queryFn: () => api.get("/gsc/status"), refetchOnWindowFocus: true });
  const connected = !!status.data?.connected;
  const properties = useQuery({ queryKey: ["gsc-properties"], queryFn: () => api.get<any[]>("/gsc/properties"), enabled: connected, retry: false });
  const connect = useMutation({
    mutationFn: () => api.get("/gsc/auth-url"),
    onSuccess: (r) => { window.open(r.url, "_blank", "noopener"); },
  });
  const disconnect = useMutation({
    mutationFn: () => api.post("/gsc/disconnect"),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["gsc-status"] }); qc.removeQueries({ queryKey: ["gsc-properties"] }); },
  });
  const saveProperty = useMutation({ mutationFn: (p: string) => api.patch(`/sites/${site.id}`, { gsc_property: p }), onSuccess: refresh });
  const sync = useMutation({
    mutationFn: () => api.post(`/sites/${site.id}/gsc/sync`, { days }),
    onSuccess: (r) => { setSyncResult(null); setJobId(r.job_id); },
  });
  const job = useJob(jobId, (j) => { setJobId(null); setSyncResult(j); onData(); });

  const list: any[] = properties.data ?? [];
  const options = property && !list.some((p) => p.property === property) ? [{ property, permission: null }, ...list] : list;
  const dirty = property !== (site.gsc_property ?? "");
  const syncing = sync.isPending || !!jobId;
  const validDays = Number.isInteger(days) && days >= 3 && days <= 480;

  return (
    <Card title="Google-Search-Console-API" description="Lesezugriff mit deinem eigenen Google-OAuth-Client. Daten bleiben nur in dieser Installation."
      actions={status.data ? <Badge tone={connected ? "green" : "gray"}>{connected ? "connected" : "not connected"}</Badge> : undefined}>
      {status.isLoading ? <Spinner /> : status.error ? <ErrorBox error={status.error} onRetry={() => status.refetch()} /> : !status.data.client_configured ? (
        <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <p>Kein Google-OAuth-Client eingerichtet. Ein Administrator muss Client-ID und Secret unter <Link to="/settings" className="font-medium text-brand-700 hover:underline dark:text-brand-300">Einstellungen</Link> hinterlegen.</p>
          <p>Beim Anlegen des OAuth-Clients (Typ „Webanwendung“) in der Google Cloud Console diese Weiterleitungs-URI eintragen:</p>
          <code className="block break-all rounded-md bg-slate-100 px-2 py-1.5 font-mono text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">{status.data.redirect_uri}</code>
          <p className="text-xs text-slate-500 dark:text-slate-400">Alternativ den CSV-Import nutzen; der braucht keine Google-Zugangsdaten.</p>
        </div>
      ) : !connected ? (
        <div className="space-y-3">
          <p className="text-sm text-slate-600 dark:text-slate-300">Mit einem Google-Konto anmelden, das Zugriff auf die Search-Console-Property hat. Google öffnet sich in einem neuen Tab; dieser Bereich aktualisiert sich bei der Rückkehr.</p>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="primary" icon={<ExternalLink className="h-4 w-4" />} loading={connect.isPending} onClick={() => connect.mutate()}>Google Search Console verbinden</Button>
            <Button variant="ghost" icon={<RefreshCw className="h-4 w-4" />} loading={status.isFetching} onClick={() => status.refetch()}>Verbindung prüfen</Button>
          </div>
          {connect.error && <ErrorBox error={connect.error} />}
          <p className="text-xs text-slate-500 dark:text-slate-400">Die beim OAuth-Client eingetragene Weiterleitungs-URI muss lauten: <code className="break-all font-mono">{status.data.redirect_uri}</code>.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {properties.error && <ErrorBox error={properties.error} onRetry={() => properties.refetch()} />}
          <div className="grid gap-3 md:grid-cols-12 md:items-end">
            <Field label={`Property für ${site.name}`} className="md:col-span-6" hint={properties.isLoading ? "Properties werden geladen…" : !list.length && !properties.error ? "Dieses Google-Konto hat keine Search-Console-Properties." : undefined}>
              <Select value={property} onChange={(e) => setProperty(e.target.value)} disabled={properties.isLoading}>
                <option value="">Property wählen…</option>
                {options.map((p) => <option key={p.property} value={p.property}>{p.property}{p.permission ? ` (${p.permission})` : ""}</option>)}
              </Select>
            </Field>
            <div className="md:col-span-2">
              <Button className="w-full" loading={saveProperty.isPending} disabled={!dirty} onClick={() => saveProperty.mutate(property)}>Property speichern</Button>
            </div>
            <Field label="Tage synchronisieren" className="md:col-span-2">
              <Input type="number" min={3} max={480} value={days} onChange={(e) => setDays(Number(e.target.value))} />
            </Field>
            <div className="md:col-span-2">
              <Button className="w-full" variant="primary" icon={<RefreshCw className="h-4 w-4" />} loading={syncing} disabled={!site.gsc_property || dirty || !validDays}
                title={!site.gsc_property || dirty ? "Zuerst eine Property speichern" : undefined} onClick={() => sync.mutate()}>Jetzt synchronisieren</Button>
            </div>
          </div>
          {saveProperty.error && <ErrorBox error={saveProperty.error} />}
          {sync.error && <ErrorBox error={sync.error} />}
          {jobId && <ProgressBar value={job?.progress ?? 0} label={job?.message ?? "Synchronisierung startet…"} />}
          {syncResult && (syncResult.status === "completed" ? (
            <Notice tone="success">
              Synced {syncResult.result?.property} from {fmtDate(syncResult.result?.start)} to {fmtDate(syncResult.result?.end)}: {Object.entries((syncResult.result?.rows ?? {}) as Record<string, number>).map(([k, v]) => `${fmtInt(v)} ${k.replace("_", "/")} rows`).join(", ")}. Search Console data lags about two days.
            </Notice>
          ) : <ErrorBox error={syncResult.error ?? `Sync ${syncResult.status}.`} />)}
          <div className="flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">Trennen löscht die gespeicherten Google-Tokens. Synchronisierte Daten bleiben erhalten.</span>
            <Button size="sm" variant="ghost" icon={<Unplug className="h-3.5 w-3.5" />} loading={disconnect.isPending} onClick={() => disconnect.mutate()}>Trennen</Button>
          </div>
          {disconnect.error && <ErrorBox error={disconnect.error} />}
        </div>
      )}
    </Card>
  );
}

function ImportPanel({ site, onData }: { site: Site; onData: () => void }) {
  const [replace, setReplace] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const importCsv = useMutation({ mutationFn: (file: File) => api.upload(`/sites/${site.id}/gsc/import`, file, { replace }), onSuccess: onData });
  const clear = useMutation({
    mutationFn: () => api.del(`/sites/${site.id}/gsc/data`),
    onSuccess: () => { setConfirm(false); importCsv.reset(); onData(); },
  });
  return (
    <Card title="CSV importieren" description="Immer verfügbar, ohne Google-Zugangsdaten.">
      <div className="space-y-3 text-sm text-slate-600 dark:text-slate-300">
        <p>
          Dateien aus dem Leistungs-Export der Search Console hochladen (deutsch oder englisch: Suchanfragen.csv/Queries.csv, Seiten.csv/Pages.csv, Länder, Geräte, Datumsangaben) oder eine beliebige CSV mit
          <span className="font-medium"> Klicks</span> und <span className="font-medium">Impressionen</span> sowie mindestens einer der Spalten
          <span className="font-medium"> Suchanfrage, Seite, Land, Gerät, Darstellung in der Suche</span> oder <span className="font-medium">Datum</span> (JJJJ-MM-TT oder TT.MM.JJJJ). <span className="font-medium">Position</span> ist optional. Deutsche Zahlenformate (1.234 / 8,47) werden erkannt.
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">Verläufe und Zeitraumvergleiche brauchen eine Datumsspalte. Dateien einzeln importieren.</p>
        <Checkbox label="Bisher importierte Zeilen derselben Art ersetzen" checked={replace} onChange={setReplace} hint="Sonst werden Zeilen angehängt; dieselbe Datei zweimal importiert zählt dann doppelt." />
        <div className="flex flex-wrap items-center gap-2">
          <FileButton label="CSV importieren" loading={importCsv.isPending} onFile={(f) => importCsv.mutate(f)} />
          <Button variant="ghost" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirm(true)}>Importierte Daten löschen</Button>
        </div>
        {importCsv.error && <ErrorBox error={importCsv.error} />}
        {importCsv.data && (
          <Notice tone="success">
            {fmtInt(importCsv.data.rows)} Zeilen in den Datensatz {String(importCsv.data.dataset).replace("_", "/")} importiert (Dimensionen: {(importCsv.data.dimensions ?? []).join(", ")}). {importCsv.data.has_dates ? "Die Datei enthält Daten mit Datum, Verläufe sind verfügbar." : "Die Datei hat kein Datum, daher keine Verläufe und Zeitraumvergleiche."}
          </Notice>
        )}
      </div>
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Search-Console-Daten löschen?"
        footer={<>
          <Button onClick={() => setConfirm(false)}>Abbrechen</Button>
          <Button variant="danger" loading={clear.isPending} onClick={() => clear.mutate()}>Daten löschen</Button>
        </>}>
        <p className="text-sm text-slate-600 dark:text-slate-300">Entfernt dauerhaft alle gespeicherten Search-Console-Zeilen für {site.name}, aus CSV-Importen und aus der API-Synchronisierung. Danach kannst du erneut importieren oder synchronisieren.</p>
        {clear.error && <div className="mt-3"><ErrorBox error={clear.error} /></div>}
      </Modal>
    </Card>
  );
}

/* ------------------------------------------------------------------ performance */
function Change({ now, before, kind }: { now: number | null; before: number | null | undefined; kind: "relative" | "points" | "position" }) {
  if (now === null || before === null || before === undefined) return <span>Keine Daten des Vorzeitraums</span>;
  const diff = now - before;
  let text: string;
  if (kind === "relative") {
    if (!before) return <span>Keine Daten des Vorzeitraums</span>;
    text = `${diff >= 0 ? "+" : ""}${((diff / before) * 100).toFixed(1)}%`;
  } else if (kind === "points") {
    text = `${diff >= 0 ? "+" : ""}${(diff * 100).toFixed(2)} Pkt.`;
  } else {
    text = `${diff >= 0 ? "+" : ""}${diff.toFixed(1)}`;
  }
  const good = kind === "position" ? diff < 0 : diff > 0;
  const flat = Math.abs(diff) < 1e-9;
  return (
    <span>
      <span className={flat ? "" : good ? "font-medium text-emerald-600 dark:text-emerald-400" : "font-medium text-red-600 dark:text-red-400"}>{text}</span> vs previous period
    </span>
  );
}

function DimensionTable({ rows, label, isUrl, siteUrl, emptyHint }: { rows: any[]; label: string; isUrl?: boolean; siteUrl?: string; emptyHint: string }) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const needle = q.trim().toLowerCase();
  const visible = needle ? rows.filter((r) => String(r.key).toLowerCase().includes(needle)) : rows;
  const columns: Column<any>[] = [
    { key: "key", header: label, render: (r) => (isUrl ? <Url href={r.key} label={shortUrl(r.key, siteUrl)} className="block max-w-lg" /> : <span className="block max-w-lg break-words font-medium text-slate-900 dark:text-slate-100">{r.key}</span>) },
    { key: "clicks", header: "Klicks", align: "right", render: (r) => fmtInt(r.clicks) },
    { key: "impressions", header: "Impressionen", align: "right", render: (r) => fmtInt(r.impressions) },
    { key: "ctr", header: "CTR", align: "right", render: (r) => fmtPct(r.ctr) },
    { key: "position", header: "Ø Position", align: "right", render: (r) => (r.position === null ? dash : fmtNum(r.position)) },
  ];
  if (!rows.length) return <EmptyState title={`No ${label.toLowerCase()} data`} description={emptyHint} />;
  return (
    <>
      {rows.length > 10 && <div className="border-b border-slate-100 p-3 dark:border-slate-800"><SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder={`${label} filtern…`} /></div>}
      <DataTable dense columns={columns} rows={visible.slice((page - 1) * PER_PAGE, page * PER_PAGE)} rowKey={(r) => r.key} />
      {visible.length > 0 && <Pagination page={page} perPage={PER_PAGE} total={visible.length} onPage={setPage} />}
    </>
  );
}

type PerfTab = "queries" | "pages" | "countries" | "devices" | "appearance";

function Performance({ site }: { site: Site }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [tab, setTab] = useState<PerfTab>("queries");
  const perf = useQuery({
    queryKey: ["gsc", site.id, "performance", start, end],
    queryFn: () => api.get(`/sites/${site.id}/gsc/performance`, { start, end }),
    placeholderData: (prev) => prev,
  });
  const invalidRange = !!start && !!end && start > end;

  if (perf.isLoading) return <Card><Spinner /></Card>;
  if (perf.error) return <ErrorBox error={perf.error} onRetry={() => perf.refetch()} />;
  const d = perf.data;
  if (!d?.has_data) {
    return <Card><EmptyState icon={<BarChart3 className="h-6 w-6" />} title="Noch keine Search-Console-Daten"
      description="Search Console verbinden und synchronisieren oder oben eine Leistungs-CSV importieren. Ohne echte Daten wird nichts angezeigt." /></Card>;
  }
  const t = d.totals ?? {};
  const p = d.previous;
  const range = d.range ?? {};
  const hasPrev = !!p && (p.impressions > 0 || p.clicks > 0);

  return (
    <div className="space-y-4">
      <Card padded={false}
        title={<span className="inline-flex items-center gap-2">Leistung <DataBadge kind="measured" /></span>}
        description={d.dated ? `${fmtDate(range.start)} bis ${fmtDate(range.end)} · Daten vorhanden ${fmtDate(range.available_start)} bis ${fmtDate(range.available_end)}` : "Die gespeicherten Daten haben kein Datum, die Summen umfassen alles Importierte."}
        actions={d.dated ? (
          <div className="flex flex-wrap items-center gap-2">
            <Input type="date" aria-label="Startdatum" className="h-8 w-auto text-xs" value={start} min={range.available_start ?? undefined} max={range.available_end ?? undefined} onChange={(e) => setStart(e.target.value)} />
            <span className="text-xs text-slate-400">to</span>
            <Input type="date" aria-label="Enddatum" className="h-8 w-auto text-xs" value={end} min={range.available_start ?? undefined} max={range.available_end ?? undefined} onChange={(e) => setEnd(e.target.value)} />
            {(start || end) && <Button size="sm" variant="ghost" onClick={() => { setStart(""); setEnd(""); }}>Zurücksetzen</Button>}
          </div>
        ) : undefined}>
        <div className="space-y-4 p-4">
          {invalidRange && <Notice tone="warn">Das Startdatum liegt nach dem Enddatum.</Notice>}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Klicks" value={fmtInt(t.clicks)} hint={d.dated ? <Change now={t.clicks} before={hasPrev ? p.clicks : null} kind="relative" /> : undefined} />
            <Stat label="Impressionen" value={fmtInt(t.impressions)} hint={d.dated ? <Change now={t.impressions} before={hasPrev ? p.impressions : null} kind="relative" /> : undefined} />
            <Stat label="CTR" value={fmtPct(t.ctr)} hint={d.dated ? <Change now={t.ctr} before={hasPrev ? p.ctr : null} kind="points" /> : undefined} />
            <Stat label="Ø Position" value={t.position === null || t.position === undefined ? "–" : fmtNum(t.position)} tooltip="Nach Impressionen gewichteter Durchschnitt. Niedriger ist besser."
              hint={d.dated ? <Change now={t.position ?? null} before={hasPrev ? p.position : null} kind="position" /> : undefined} />
          </div>
          {d.dated ? ((d.series ?? []).length ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={d.series} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} tickLine={false} minTickGap={32} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis yAxisId="clicks" tick={{ fontSize: 11, fill: chartColors[0] }} tickLine={false} axisLine={false} width={44} allowDecimals={false} />
                <YAxis yAxisId="impressions" orientation="right" tick={{ fontSize: 11, fill: chartColors[3] }} tickLine={false} axisLine={false} width={52} allowDecimals={false} />
                <ChartTooltip contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8, color: "#f8fafc", fontSize: 12 }} labelFormatter={(v) => fmtDate(String(v))}
                  formatter={(value: any) => fmtInt(Number(value))} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line yAxisId="clicks" type="monotone" dataKey="clicks" name="Klicks" stroke={chartColors[0]} strokeWidth={2} dot={false} />
                <Line yAxisId="impressions" type="monotone" dataKey="impressions" name="Impressionen" stroke={chartColors[3]} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <EmptyState title="Keine Zeilen in diesem Zeitraum" description="Einen Zeitraum innerhalb der vorhandenen Daten wählen." />) : (
            <Notice>Verlauf und Zeitraumvergleich fehlen, weil die gespeicherten Zeilen kein Datum haben. Über die API synchronisieren oder eine CSV mit Datumsspalte importieren.</Notice>
          )}
          {d.note && <Notice>{d.note}</Notice>}
        </div>
      </Card>

      <Card padded={false}>
        <div className="px-3 pt-2">
          <Tabs<PerfTab> value={tab} onChange={setTab} tabs={[
            { id: "queries", label: "Suchanfragen", count: (d.queries ?? []).length },
            { id: "pages", label: "Seiten", count: (d.pages ?? []).length },
            { id: "countries", label: "Länder", count: (d.countries ?? []).length },
            { id: "devices", label: "Geräte", count: (d.devices ?? []).length },
            { id: "appearance", label: "Darstellung in der Suche", count: (d.appearance ?? []).length },
          ]} />
        </div>
        {tab === "queries" && <DimensionTable key="q" rows={d.queries ?? []} label="Suchanfrage" emptyHint="Die gespeicherten Daten haben keine Suchanfragen. Suchanfragen.csv importieren oder über die API synchronisieren." />}
        {tab === "pages" && <DimensionTable key="p" rows={d.pages ?? []} label="Seite" isUrl siteUrl={site.url} emptyHint="Die gespeicherten Daten haben keine Seiten. Seiten.csv importieren oder über die API synchronisieren." />}
        {tab === "countries" && <DimensionTable key="c" rows={d.countries ?? []} label="Land" emptyHint="Keine Länderdaten. Länder.csv importieren oder über die API synchronisieren." />}
        {tab === "devices" && <DimensionTable key="d" rows={d.devices ?? []} label="Gerät" emptyHint="Keine Gerätedaten. Geräte.csv importieren oder über die API synchronisieren." />}
        {tab === "appearance" && <DimensionTable key="a" rows={d.appearance ?? []} label="Darstellung in der Suche" emptyHint="Keine Daten zur Darstellung. Google meldet sie nur, wenn besondere Ergebnistypen für deine Website erscheinen." />}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ insights */
type InsightTab = "opportunities" | "declining_queries" | "declining_pages" | "new_queries" | "lost_queries" | "cannibalisation";

function PagedTable({ columns, rows, rowKey, empty }: { columns: Column<any>[]; rows: any[]; rowKey: (r: any, i: number) => string | number; empty: ReactNode }) {
  const [page, setPage] = useState(1);
  if (!rows.length) return <>{empty}</>;
  return (
    <>
      <DataTable dense columns={columns} rows={rows.slice((page - 1) * PER_PAGE, page * PER_PAGE)} rowKey={rowKey} />
      <Pagination page={page} perPage={PER_PAGE} total={rows.length} onPage={setPage} />
    </>
  );
}

function AiDecline({ siteId }: { siteId: number }) {
  const run = useMutation({ mutationFn: () => api.post("/ai/run", { task: "ranking_decline", site_id: siteId }) });
  return (
    <Card title="KI-Erklärung für Rückgänge" description="Nutzt die rückläufigen und verlorenen Suchanfragen oben sowie Audit-Befunde rückläufiger Seiten, falls ein Crawl existiert."
      actions={<Button size="sm" icon={<Sparkles className="h-3.5 w-3.5" />} loading={run.isPending} onClick={() => run.mutate()}>Rückgang mit KI erklären</Button>}>
      {run.isPending ? <Spinner label="Wird erstellt…" /> : run.error ? (
        <div className="space-y-2">
          <ErrorBox error={run.error} onRetry={() => run.mutate()} />
          {run.error instanceof ApiError && run.error.status === 400 && (
            <p className="text-xs text-slate-500 dark:text-slate-400">Dafür braucht es einen KI-Anbieter in den <Link to="/settings" className="font-medium text-brand-700 hover:underline dark:text-brand-300">Einstellungen</Link> und datierte Search-Console-Daten für zwei Vergleichszeiträume.</p>
          )}
        </div>
      ) : run.data ? (
        <div className="space-y-3">
          <div className="prose-ai whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{run.data.output}</div>
          <p className="border-t border-slate-100 pt-2 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">{run.data.provider}{run.data.model ? ` · ${run.data.model}` : ""}. {run.data.grounding}</p>
        </div>
      ) : <p className="text-sm text-slate-500 dark:text-slate-400">Fragt das eingerichtete Sprachmodell nach wahrscheinlichen Ursachen und nächsten Schritten auf Basis der gemessenen Daten.</p>}
    </Card>
  );
}

function Insights({ site }: { site: Site }) {
  const [days, setDays] = useState(28);
  const [tab, setTab] = useState<InsightTab>("opportunities");
  const ins = useQuery({ queryKey: ["gsc", site.id, "insights", days], queryFn: () => api.get(`/sites/${site.id}/gsc/insights`, { days }), placeholderData: (prev) => prev });

  if (ins.isLoading) return <Card><Spinner /></Card>;
  if (ins.error) return <ErrorBox error={ins.error} onRetry={() => ins.refetch()} />;
  const d = ins.data;
  if (!d?.has_data) {
    return <Card title="Auswertungen"><EmptyState title="Keine Suchanfragen für Auswertungen" description="Auswertungen brauchen Search-Console-Zeilen mit Suchanfragen. Über die API synchronisieren oder Suchanfragen.csv importieren." /></Card>;
  }

  const pos = (v: number | null | undefined) => (v === null || v === undefined ? dash : fmtNum(v));
  const keyCell = (isUrl: boolean) => (r: any) => (isUrl ? <Url href={r.key} label={shortUrl(r.key, site.url)} className="block max-w-md" /> : <span className="block max-w-md break-words font-medium text-slate-900 dark:text-slate-100">{r.key}</span>);
  const oppColumns: Column<any>[] = [
    { key: "type", header: "Typ", render: (o) => <Badge tone={o.type === "striking distance" ? "blue" : "purple"}>{o.type === "striking distance" ? "knapp vor Seite 1" : o.type === "low CTR for position" ? "niedrige CTR für Position" : o.type}</Badge> },
    { key: "query", header: "Suchanfrage", render: keyCell(false) },
    { key: "impressions", header: "Impressionen", align: "right", render: (o) => fmtInt(o.impressions) },
    { key: "clicks", header: "Klicks", align: "right", render: (o) => fmtInt(o.clicks) },
    { key: "position", header: "Ø Position", align: "right", render: (o) => pos(o.position) },
    { key: "extra", header: <span className="inline-flex items-center gap-1.5">Zusatzklicks <DataBadge kind="estimated" /></span>, align: "right",
      render: (o) => <span className="font-semibold text-slate-900 dark:text-slate-100">+{fmtInt(o.estimated_extra_clicks)}</span> },
    { key: "basis", header: "Grundlage der Schätzung", render: (o) => <span className="block max-w-xs whitespace-normal text-xs text-slate-500 dark:text-slate-400">{o.basis}</span> },
  ];
  const declineColumns = (isUrl: boolean): Column<any>[] => [
    { key: "key", header: isUrl ? "Seite" : "Suchanfrage", render: keyCell(isUrl) },
    { key: "change", header: "Klickänderung", align: "right", render: (r) => <span className="font-semibold text-red-600 dark:text-red-400">{fmtInt(r.click_change)}</span> },
    { key: "clicks", header: "Klicks jetzt / vorher", align: "right", render: (r) => `${fmtInt(r.clicks)} / ${fmtInt(r.previous_clicks)}` },
    { key: "impressions", header: "Impressionen jetzt / vorher", align: "right", render: (r) => `${fmtInt(r.impressions)} / ${fmtInt(r.previous_impressions)}` },
    { key: "position", header: "Position jetzt / vorher", align: "right", render: (r) => <>{pos(r.position)} / {pos(r.previous_position)}</> },
  ];
  const plainColumns: Column<any>[] = [
    { key: "key", header: "Suchanfrage", render: keyCell(false) },
    { key: "clicks", header: "Klicks", align: "right", render: (r) => fmtInt(r.clicks) },
    { key: "impressions", header: "Impressionen", align: "right", render: (r) => fmtInt(r.impressions) },
    { key: "ctr", header: "CTR", align: "right", render: (r) => fmtPct(r.ctr) },
    { key: "position", header: "Ø Position", align: "right", render: (r) => pos(r.position) },
  ];
  const cannibalColumns: Column<any>[] = [
    { key: "query", header: "Suchanfrage", render: (c) => <span className="block max-w-xs break-words font-medium text-slate-900 dark:text-slate-100">{c.query}</span> },
    { key: "impressions", header: "Impressionen", align: "right", render: (c) => fmtInt(c.impressions) },
    { key: "pages", header: "Seiten, die sich die Impressionen teilen", render: (c) => (
      <ul className="space-y-1">
        {(c.pages ?? []).map((pg: any) => (
          <li key={pg.page} className="flex flex-wrap items-baseline gap-x-2">
            <Url href={pg.page} label={shortUrl(pg.page, site.url)} />
            <span className="text-xs tabular-nums text-slate-500 dark:text-slate-400">{fmtInt(pg.impressions)} impr. · {fmtInt(pg.clicks)} clicks · pos. {pg.position ?? "–"}</span>
          </li>
        ))}
      </ul>
    ) },
  ];
  const needDated = (what: string) => <EmptyState title={d.dated ? `Keine ${what}` : "Braucht zwei Vergleichszeiträume"}
    description={d.dated ? `Nichts erfüllt die Kriterien in den letzten ${d.window_days} Tagen gegenüber den ${d.window_days} Tagen davor.` : `Für Zeitraumvergleiche braucht es datierte Daten über mindestens ${d.window_days * 2} Tage. Mehr Tage synchronisieren, einen längeren Export importieren oder ein kürzeres Fenster wählen.`} />;

  return (
    <div className="space-y-4">
      <Card padded={false} title={<span className="inline-flex items-center gap-2">Auswertungen <DataBadge kind="measured" /></span>}
        description={d.dated ? `Letzte ${d.window_days} Tage gegenüber den ${d.window_days} Tagen davor` : "Aus den gespeicherten Suchanfragen abgeleitet"}
        actions={<Select className="h-8 w-auto text-xs" value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Vergleichsfenster">
          {[7, 14, 28, 56, 90].map((n) => <option key={n} value={n}>{n} Tage</option>)}
        </Select>}>
        <div className="px-3 pt-2">
          <Tabs<InsightTab> value={tab} onChange={setTab} tabs={[
            { id: "opportunities", label: "Chancen", count: (d.opportunities ?? []).length },
            { id: "declining_queries", label: "Rückläufige Suchanfragen", count: (d.declining_queries ?? []).length },
            { id: "declining_pages", label: "Rückläufige Seiten", count: (d.declining_pages ?? []).length },
            { id: "new_queries", label: "Neue Suchanfragen", count: (d.new_queries ?? []).length },
            { id: "lost_queries", label: "Verlorene Suchanfragen", count: (d.lost_queries ?? []).length },
            { id: "cannibalisation", label: "Kannibalisierung", count: (d.cannibalisation ?? []).length },
          ]} />
        </div>
        {tab === "opportunities" && (
          <>
            <div className="px-3 pb-3"><Notice>Impressionen, Klicks und Position misst Google. „Zusatzklicks“ ist eine Schätzung aus einer allgemeinen CTR-Kurve nach Position; die echte CTR hängt von Suchanfrage und SERP-Layout ab, also nur als Richtung verstehen.</Notice></div>
            <PagedTable key="o" columns={oppColumns} rows={d.opportunities ?? []} rowKey={(o, i) => `${o.key}-${i}`}
              empty={<EmptyState title="Keine Chancen gefunden" description="Keine Suchanfrage mit mindestens 20 Impressionen steht auf Position 4–20 oder hat eine auffällig niedrige CTR auf Top-3-Position." />} />
          </>
        )}
        {tab === "declining_queries" && <PagedTable key="dq" columns={declineColumns(false)} rows={d.declining_queries ?? []} rowKey={(r) => r.key} empty={needDated("rückläufigen Suchanfragen")} />}
        {tab === "declining_pages" && <PagedTable key="dp" columns={declineColumns(true)} rows={d.declining_pages ?? []} rowKey={(r) => r.key} empty={needDated("rückläufigen Seiten")} />}
        {tab === "new_queries" && <PagedTable key="nq" columns={plainColumns} rows={d.new_queries ?? []} rowKey={(r) => r.key} empty={needDated("neuen Suchanfragen")} />}
        {tab === "lost_queries" && <PagedTable key="lq" columns={plainColumns} rows={d.lost_queries ?? []} rowKey={(r) => r.key} empty={needDated("verlorenen Suchanfragen")} />}
        {tab === "cannibalisation" && (
          <>
            <div className="px-3 pb-3"><Notice>Suchanfragen, bei denen zwei oder mehr Seiten je mindestens 20 % der Impressionen bekommen (mindestens 50 Impressionen), über alle gespeicherten Daten. Braucht Zeilen mit Suchanfrage und Seite, wie sie die API-Synchronisierung liefert.</Notice></div>
            <PagedTable key="cn" columns={cannibalColumns} rows={d.cannibalisation ?? []} rowKey={(c) => c.query}
              empty={<EmptyState title="Keine Kannibalisierung erkannt" description="Keine Suchanfrage verteilt ihre Impressionen auf mehrere Seiten, oder die Zeilen verbinden Suchanfrage und Seite nicht." />} />
          </>
        )}
      </Card>
      <AiDecline siteId={site.id} />
    </div>
  );
}

type OAuthState = { kind: "working" | "ok" | "error"; message?: string } | null;

/** Google sends the browser back with a one-time code in the URL fragment. It is exchanged here, with the
 *  signed-in user's token, so a consent link started by someone else cannot attach its Google account to you. */
function useOAuthReturn(onDone: () => void): OAuthState {
  const [state, setState] = useState<OAuthState>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const code = params.get("gsc_code");
    const oauthState = params.get("gsc_state");
    const err = params.get("gsc_error");
    if (!code && !oauthState && !err) return;
    window.history.replaceState(null, "", window.location.pathname); // keep the code out of the address bar and history
    if (err) { setState({ kind: "error", message: "Die Google-Verbindung wurde abgebrochen." }); return; }
    if (!code || !oauthState) return;
    setState({ kind: "working" });
    api.post("/gsc/exchange", { code, state: oauthState })
      .then(() => { setState({ kind: "ok" }); onDone(); })
      .catch((e) => setState({ kind: "error", message: e instanceof ApiError ? e.message : "Die Google-Verbindung konnte nicht abgeschlossen werden." }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return state;
}

export default function SearchConsole() {
  const { site } = useSite();
  const qc = useQueryClient();
  const oauth = useOAuthReturn(() => {
    void qc.invalidateQueries({ queryKey: ["gsc-status"] });
    void qc.invalidateQueries({ queryKey: ["gsc-properties"] });
  });
  if (!site) return <NeedsCrawl hasSite={false} />;
  const onData = () => {
    void qc.invalidateQueries({ queryKey: ["gsc", site.id] });
    void qc.invalidateQueries({ queryKey: ["keywords", site.id] });
  };
  return (
    <div>
      <PageHeader title="Search Console"
        description="Klicks, Impressionen, CTR und Position, wie Google sie für deine Website misst, plus Auswertungen daraus. API verbinden oder CSV-Exporte importieren." />
      <div className="space-y-4">
        {oauth?.kind === "working" && <Notice>Google-Verbindung wird abgeschlossen…</Notice>}
        {oauth?.kind === "ok" && <Notice tone="success">Search Console verbunden.</Notice>}
        {oauth?.kind === "error" && <ErrorBox error={oauth.message ?? "Die Google-Verbindung ist fehlgeschlagen."} />}
        <div className="grid gap-4 xl:grid-cols-2">
          <ConnectionPanel key={`c-${site.id}`} site={site} onData={onData} />
          <ImportPanel key={`i-${site.id}`} site={site} onData={onData} />
        </div>
        <Performance key={`p-${site.id}`} site={site} />
        <Insights key={`n-${site.id}`} site={site} />
      </div>
    </div>
  );
}
