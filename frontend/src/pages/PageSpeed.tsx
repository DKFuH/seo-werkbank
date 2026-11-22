import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Gauge, Loader2, XCircle } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, chartColors, type Column, DataBadge, DataTable, EmptyState, ErrorBox, Field, Input, Notice, PageHeader,
  ScoreRing, Select, Spinner, Tabs, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtBytes, fmtDateTime, fmtMs, scoreColor, shortUrl, titleCase } from "../lib/format";

const CATEGORIES: [string, string][] = [["performance", "Performance"], ["accessibility", "Barrierefreiheit"], ["best-practices", "Best Practices"], ["seo", "SEO"]];
const FIELD_ORDER = ["LCP", "INP", "CLS", "FCP", "TTFB"];
const METRIC_NAME: Record<string, string> = {
  LCP: "Largest Contentful Paint", INP: "Interaction to Next Paint", CLS: "Cumulative Layout Shift", FCP: "First Contentful Paint",
  TTFB: "Time to First Byte", TBT: "Total Blocking Time", "Speed Index": "Speed Index", TTI: "Time to Interactive", "TTFB (document)": "Serverantwortzeit",
};
const TOPIC_ORDER = ["images", "javascript", "css", "render-blocking", "caching", "server", "layout", "other"];
const TOPIC_LABEL: Record<string, string> = {
  images: "Bilder", javascript: "JavaScript", css: "CSS", "render-blocking": "Renderblockierende Ressourcen", caching: "Caching & Komprimierung",
  server: "Server & Netzwerk", layout: "Layoutstabilität & Seitengewicht", other: "Sonstiges",
};
const SOURCE_LABEL: Record<string, string> = { psi_api: "PageSpeed Insights API", local_lighthouse: "Lokales Lighthouse" };
const tooltipStyle = { background: "#0f172a", border: "none", borderRadius: 8, color: "#f8fafc", fontSize: 12 } as const;
const axisTick = { fontSize: 12, fill: "#94a3b8" } as const;

const ratingTone = (rating: string | null | undefined) => (rating === "good" ? "green" : rating === "needs improvement" ? "amber" : rating === "poor" ? "red" : "gray");
const ratingText = (rating: string | null | undefined) =>
  rating === "good" ? "text-emerald-600 dark:text-emerald-400" : rating === "needs improvement" ? "text-amber-600 dark:text-amber-400" : rating === "poor" ? "text-red-600 dark:text-red-400" : "text-slate-900 dark:text-slate-50";
const metricValue = (label: string, value: number | null | undefined) => (value === null || value === undefined ? "–" : label === "CLS" ? value.toFixed(2) : fmtMs(value));
/** Lighthouse descriptions contain Markdown links and code ticks; show them as plain text. */
const plain = (s: string | null | undefined) => (s ?? "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/`/g, "");

function MetricTile({ label, value, rating, sub }: { label: string; value: string; rating?: string | null; sub?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-200" title={METRIC_NAME[label]}>{label}</span>
        {rating && <Badge tone={ratingTone(rating)}>{rating}</Badge>}
      </div>
      <div className={`mt-1 text-xl font-semibold tabular-nums ${ratingText(rating)}`}>{value}</div>
      <div className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">{sub ?? METRIC_NAME[label] ?? ""}</div>
    </div>
  );
}

function FieldData({ result }: { result: any }) {
  const page: Record<string, any> = result.field ?? {};
  const origin: Record<string, any> = result.origin_field ?? {};
  const hasPage = Object.keys(page).length > 0;
  const hasOrigin = Object.keys(origin).length > 0;
  const data = hasPage ? page : origin;
  const labels = FIELD_ORDER.filter((l) => data[l]);
  const cwvPass = ["LCP", "INP", "CLS"].every((l) => data[l]?.rating === "good");
  return (
    <Card title="Core Web Vitals: Felddaten" description="75. Perzentil echter Chrome-Nutzer der letzten 28 Tage (Chrome UX Report)"
      actions={hasPage || hasOrigin ? <DataBadge kind="measured" /> : <DataBadge kind="unavailable" />}>
      {!hasPage && !hasOrigin ? (
        <EmptyState icon={<Gauge className="h-6 w-6" />} title="Keine Felddaten für diese Seite"
          description={result.source === "local_lighthouse"
            ? "Lokales Lighthouse liefert nur Labordaten. Für echte Core Web Vitals den Test über die PageSpeed-Insights-API laufen lassen."
            : "Der Chrome UX Report erfasst nur Seiten und Domains mit genug echtem Traffic. Diese URL liegt darunter, daher folgen nur Labordaten. Labordaten sind eine Simulation, nicht das Erlebnis deiner Besucher."} />
      ) : (
        <div className="space-y-3">
          {!hasPage && <Notice tone="warn">Diese URL hat zu wenig Traffic für Felddaten auf Seitenebene. Die Werte unten gelten für die ganze Domain (alle Seiten).</Notice>}
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            {["LCP", "INP", "CLS"].every((l) => data[l]) ? (
              cwvPass ? <><CheckCircle2 className="h-4 w-4 text-emerald-600" /> Core-Web-Vitals-Bewertung: <strong>bestanden</strong></>
                : <><XCircle className="h-4 w-4 text-red-600" /> Core-Web-Vitals-Bewertung: <strong>nicht bestanden</strong></>
            ) : <span className="text-slate-500 dark:text-slate-400">Nicht alle drei Core Web Vitals (LCP, INP, CLS) liegen vor, daher keine Bewertung.</span>}
            {hasPage && result.field_overall && <Badge tone={result.field_overall === "fast" ? "green" : result.field_overall === "average" ? "amber" : "red"}>overall: {result.field_overall}</Badge>}
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            {labels.map((l) => <MetricTile key={l} label={l} value={metricValue(l, data[l].p75)} rating={data[l].rating} />)}
          </div>
        </div>
      )}
    </Card>
  );
}

function Recommendations({ recs }: { recs: any[] }) {
  const topics = TOPIC_ORDER.filter((t) => recs.some((r) => (TOPIC_ORDER.includes(r.topic) ? r.topic : "other") === t));
  const [open, setOpen] = useState<string | null>(null);
  if (!recs.length) return <EmptyState title="Keine Performance-Empfehlungen" description="Lighthouse hat für diese Seite keine Prüfung unter 90 gefunden." />;
  return (
    <div className="space-y-5">
      {topics.map((topic) => {
        const group = recs.filter((r) => (TOPIC_ORDER.includes(r.topic) ? r.topic : "other") === topic);
        return (
          <section key={topic}>
            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {TOPIC_LABEL[topic]} <span className="rounded-full bg-slate-100 px-1.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">{group.length}</span>
            </h3>
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
              {group.map((r) => {
                const expanded = open === r.id;
                const savings = Object.entries((r.metric_savings ?? {}) as Record<string, number>);
                return (
                  <li key={r.id} className="p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: scoreColor(r.score === null || r.score === undefined ? null : r.score * 100) }} aria-hidden />
                          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{plain(r.title)}</span>
                        </div>
                        <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{plain(r.description)}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-1">
                        {r.savings_ms ? <Badge tone="orange" title="Geschätzte Ladezeit-Ersparnis">spart ~{fmtMs(r.savings_ms)}</Badge> : null}
                        {r.savings_bytes ? <Badge tone="orange" title="Geschätzte Ersparnis an Übertragungsgröße">spart ~{fmtBytes(r.savings_bytes)}</Badge> : null}
                        {!r.savings_ms && !r.savings_bytes && r.display ? <Badge>{r.display}</Badge> : null}
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                      {(r.expected_impact ?? []).length > 0 && (
                        <span className="flex flex-wrap items-center gap-1">Expected to improve:
                          {savings.length ? savings.map(([m, v]) => <Badge key={m} tone="blue" title={METRIC_NAME[m] ?? m}>{m}{typeof v === "number" ? ` −${m === "CLS" ? v.toFixed(2) : fmtMs(v)}` : ""}</Badge>)
                            : r.expected_impact.map((m: string) => <Badge key={m} tone="blue">{m}</Badge>)}
                        </span>
                      )}
                      {(r.items ?? []).length > 0 && (
                        <button className="font-medium text-brand-700 hover:underline dark:text-brand-300" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : r.id)}>
                          {r.items.length} {r.items.length === 1 ? "betroffenes Element" : "betroffene Elemente"} {expanded ? "ausblenden" : "anzeigen"}
                        </button>
                      )}
                    </div>
                    {expanded && (
                      <ul className="mt-2 space-y-1 rounded-md bg-slate-50 p-2 text-xs dark:bg-slate-950">
                        {r.items.map((it: any, i: number) => (
                          <li key={i} className="flex flex-wrap items-start justify-between gap-2">
                            <code className="min-w-0 flex-1 break-all text-slate-700 dark:text-slate-300">{it.item}</code>
                            <span className="shrink-0 tabular-nums text-slate-500 dark:text-slate-400">
                              {[it.wasted_ms ? `−${fmtMs(it.wasted_ms)}` : null, it.wasted_bytes ? `−${fmtBytes(it.wasted_bytes)}` : null, it.total_bytes ? `${fmtBytes(it.total_bytes)} gesamt` : null].filter(Boolean).join(" · ")}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function CategoryIssues({ issues }: { issues: Record<string, any[]> }) {
  const cats = CATEGORIES.filter(([id]) => id !== "performance" && issues[id]);
  const [tab, setTab] = useState(cats[0]?.[0] ?? "accessibility");
  if (!cats.length) return null;
  const active = cats.some(([id]) => id === tab) ? tab : cats[0][0];
  const list = issues[active] ?? [];
  return (
    <Card title="Nicht bestandene Prüfungen nach Kategorie" description="Bestanden/nicht bestanden außerhalb der Performance-Kategorie">
      <Tabs value={active} onChange={setTab} tabs={cats.map(([id, label]) => ({ id, label, count: issues[id].length }))} />
      {list.length === 0 ? <Notice tone="success">No failed {titleCase(active).toLowerCase()} audits.</Notice> : (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {list.map((a) => (
            <li key={a.id} className="py-2.5">
              <div className="flex items-start gap-2 text-sm font-medium text-slate-900 dark:text-slate-100"><XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />{plain(a.title)}</div>
              {a.description && <p className="ml-6 mt-0.5 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{plain(a.description)}</p>}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Result({ result }: { result: any }) {
  const lab: Record<string, any> = result.lab ?? {};
  return (
    <div className="space-y-4">
      <Card title="Lighthouse-Scores"
        description={<><Url href={result.final_url ?? result.url} /> · {titleCase(result.strategy ?? "")} · {SOURCE_LABEL[result.source] ?? result.source} · {fmtDateTime(result.created_at)}{result.lighthouse_version ? ` · Lighthouse ${result.lighthouse_version}` : ""}</>}>
        {result.runtime_error && <div className="mb-4"><Notice tone="warn">Lighthouse reported a problem while loading the page: {result.runtime_error}</Notice></div>}
        <div className="grid grid-cols-2 justify-items-center gap-4 sm:grid-cols-4">
          {CATEGORIES.map(([id, label]) => (
            <div key={id} className="flex flex-col items-center gap-2 text-center">
              <ScoreRing score={result.scores?.[id]} size={104} label="/ 100" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span>
            </div>
          ))}
        </div>
      </Card>
      <FieldData result={result} />
      <Card title="Labormesswerte" description="Aus einem simulierten Seitenaufruf. Hilfreich zur Fehlersuche, kein Ersatz für Felddaten." actions={<DataBadge kind="measured" />}>
        {Object.keys(lab).length === 0 ? <EmptyState title="Keine Labormesswerte" description="Der Lighthouse-Lauf lieferte keine Messwerte." /> : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {Object.entries(lab).map(([label, m]) => <MetricTile key={label} label={label} value={m.display ?? metricValue(label, m.value)} rating={m.rating} />)}
          </div>
        )}
      </Card>
      <Card title="Empfehlungen" description="Performance-Prüfungen unter 90, größte geschätzte Ersparnis zuerst" actions={<DataBadge kind="estimated" />}>
        <Recommendations recs={result.recommendations ?? []} />
      </Card>
      <CategoryIssues issues={result.category_issues ?? {}} />
    </div>
  );
}

export default function PageSpeed() {
  const { site } = useSite();
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["pagespeed-status"], queryFn: () => api.get("/pagespeed/status") });
  const [url, setUrl] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<"mobile" | "desktop">("mobile");
  const [source, setSource] = useState<"psi" | "local">("psi");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const resultRef = useRef<HTMLDivElement>(null);
  const effectiveUrl = url ?? site?.url ?? "";
  const siteId = site?.id;

  useEffect(() => { setUrl(null); setSelectedId(null); }, [siteId]);

  const history = useQuery({ queryKey: ["pagespeed-history", siteId ?? null], queryFn: () => api.get<any[]>("/pagespeed/history", { site_id: siteId, limit: 100 }) });
  const detail = useQuery({ queryKey: ["pagespeed-result", selectedId], queryFn: () => api.get(`/pagespeed/${selectedId}`), enabled: selectedId !== null, staleTime: Infinity });
  const run = useMutation({
    mutationFn: () => api.post("/pagespeed/run", { url: effectiveUrl.trim(), strategy, source, site_id: siteId ?? null }),
    onSuccess: (data) => {
      qc.setQueryData(["pagespeed-result", data.id], data);
      setSelectedId(data.id);
      void qc.invalidateQueries({ queryKey: ["pagespeed-history"] });
    },
  });
  useEffect(() => {
    if (!run.isPending) return;
    setElapsed(0);
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [run.isPending]);

  const localAvailable = !!status.data?.local_lighthouse;
  useEffect(() => { if (status.data && !localAvailable && source === "local") setSource("psi"); }, [status.data, localAvailable, source]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    run.mutate();
  };

  const rows: any[] = history.data ?? [];
  const chart = [...rows].reverse().filter((r) => typeof r.scores?.performance === "number")
    .map((r) => ({ t: fmtDateTime(r.created_at), [r.strategy]: r.scores.performance, url: r.url }));
  const strategies = Array.from(new Set(rows.map((r) => r.strategy as string)));
  const scoreCell = (v: number | null | undefined) => (v === null || v === undefined ? <span className="text-slate-400">–</span> : <span className="font-medium tabular-nums" style={{ color: scoreColor(v) }}>{v}</span>);
  const columns: Column<any>[] = [
    { key: "when", header: "Getestet", render: (r) => <span className={r.id === selectedId ? "font-semibold text-brand-700 dark:text-brand-300" : ""}>{fmtDateTime(r.created_at)}</span> },
    { key: "url", header: "URL", render: (r) => <span className="block max-w-xs truncate" title={r.url}>{shortUrl(r.url, site?.url)}</span> },
    { key: "strategy", header: "Gerät", render: (r) => <Badge>{r.strategy === "mobile" ? "Mobil" : titleCase(r.strategy)}</Badge> },
    { key: "source", header: "Quelle", render: (r) => SOURCE_LABEL[r.source] ?? r.source },
    { key: "perf", header: "Perf.", align: "right", render: (r) => scoreCell(r.scores?.performance) },
    { key: "a11y", header: "A11y", align: "right", render: (r) => scoreCell(r.scores?.accessibility) },
    { key: "bp", header: "Best Pr.", align: "right", render: (r) => scoreCell(r.scores?.["best-practices"]) },
    { key: "seo", header: "SEO", align: "right", render: (r) => scoreCell(r.scores?.seo) },
    { key: "lcp", header: "LCP (Labor)", align: "right", render: (r) => metricValue("LCP", r.lab?.LCP?.value) },
    { key: "cls", header: "CLS (Labor)", align: "right", render: (r) => metricValue("CLS", r.lab?.CLS?.value) },
  ];

  return (
    <>
      <PageHeader title="PageSpeed" description="Lighthouse-Scores, Core Web Vitals echter Nutzer und priorisierte Performance-Empfehlungen für beliebige URLs." />

      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Card title="Test starten" className="lg:col-span-2">
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <Field label="URL" className="sm:col-span-4">
                <Input type="url" required value={effectiveUrl} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.de/" disabled={run.isPending} />
              </Field>
              <Field label="Gerät" className="sm:col-span-1">
                <Select value={strategy} onChange={(e) => setStrategy(e.target.value as "mobile" | "desktop")} disabled={run.isPending}>
                  <option value="mobile">Mobil</option>
                  <option value="desktop">Desktop</option>
                </Select>
              </Field>
              <Field label="Quelle" className="sm:col-span-3" hint={!localAvailable && status.data ? "Lokales Lighthouse ist auf dem Server nicht installiert." : undefined}>
                <Select value={source} onChange={(e) => setSource(e.target.value as "psi" | "local")} disabled={run.isPending}>
                  <option value="psi">PageSpeed-Insights-API (Labor- und Felddaten, nur öffentliche URLs)</option>
                  <option value="local" disabled={!localAvailable}>Lokales Lighthouse (nur Labordaten){localAvailable ? "" : " (nicht verfügbar)"}</option>
                </Select>
              </Field>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" variant="primary" loading={run.isPending} icon={<Gauge className="h-4 w-4" />}>{run.isPending ? "Teste…" : "Test starten"}</Button>
              {run.isPending && (
                <span className="inline-flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300" role="status">
                  <Loader2 className="h-4 w-4 animate-spin" /> Lighthouse is loading and measuring the page. This usually takes 15 to 60 seconds ({elapsed} s).
                </span>
              )}
            </div>
            {run.error ? <ErrorBox error={run.error} onRetry={() => run.mutate()} /> : null}
          </form>
        </Card>
        <Card title="Datenquellen">
          {status.isLoading ? <Spinner /> : status.error ? <ErrorBox error={status.error} onRetry={() => status.refetch()} /> : (
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-700 dark:text-slate-300">PageSpeed-Insights-API-Schlüssel</span>
                {status.data.psi_key_configured ? <Badge tone="green">eingerichtet</Badge> : <Badge tone="amber">nicht gesetzt</Badge>}
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-700 dark:text-slate-300">Lokales Lighthouse-CLI</span>
                {localAvailable ? <Badge tone="green">verfügbar</Badge> : <Badge>nicht installiert</Badge>}
              </div>
              <ul className="list-disc space-y-1 pl-4 text-xs text-slate-500 dark:text-slate-400">
                {(status.data.notes ?? []).map((n: string, i: number) => <li key={i}>{n}</li>)}
              </ul>
              {!status.data.psi_key_configured && <Link to="/settings" className="text-xs font-medium text-brand-700 hover:underline dark:text-brand-300">API-Schlüssel in den Einstellungen hinterlegen</Link>}
            </div>
          )}
        </Card>
      </div>

      <div className="mb-4 scroll-mt-4" ref={resultRef}>
        {run.isPending ? (
          <Card><Spinner label={`Lighthouse läuft für ${shortUrl(effectiveUrl)}… ${elapsed} s`} /></Card>
        ) : selectedId === null ? (
          <Card><EmptyState icon={<Gauge className="h-6 w-6" />} title="Kein Ergebnis ausgewählt" description="Oben einen Test starten oder unten einen früheren Lauf wählen." /></Card>
        ) : detail.isLoading ? <Card><Spinner label="Ergebnis wird geladen…" /></Card>
          : detail.error ? <ErrorBox error={detail.error} onRetry={() => detail.refetch()} />
          : detail.data ? <Result result={detail.data} /> : null}
      </div>

      <Card padded={false} title="Verlauf" description={site ? `Frühere Läufe für ${site.name}. Zeile anklicken zum Öffnen.` : "Deine früheren Läufe. Zeile anklicken zum Öffnen."}>
        {history.isLoading ? <Spinner /> : history.error ? <div className="p-4"><ErrorBox error={history.error} onRetry={() => history.refetch()} /></div> : (
          <>
            {chart.length > 1 && (
              <div className="border-b border-slate-100 p-4 dark:border-slate-800">
                <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Performance-Score im Verlauf</div>
                <div className="h-56" role="img" aria-label="Performance-Score im Verlauf">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" vertical={false} />
                      <XAxis dataKey="t" tick={axisTick} tickLine={false} axisLine={{ stroke: "#94a3b855" }} minTickGap={40} />
                      <YAxis domain={[0, 100]} tick={axisTick} tickLine={false} axisLine={false} width={36} />
                      <ChartTooltip contentStyle={tooltipStyle} labelStyle={{ color: "#f8fafc" }} itemStyle={{ color: "#f8fafc" }} />
                      {strategies.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
                      {strategies.map((s, i) => (
                        <Line key={s} type="monotone" dataKey={s} name={`${titleCase(s)} performance`} stroke={chartColors[i % chartColors.length]} strokeWidth={2}
                          dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} dense onRowClick={(r) => { setSelectedId(r.id); resultRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" }); }}
              empty={<EmptyState title="Noch keine Läufe" description="Jedes Testergebnis wird hier gespeichert, damit du Veränderungen verfolgen kannst." />} />
          </>
        )}
      </Card>
    </>
  );
}
