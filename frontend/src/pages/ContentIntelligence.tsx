import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Stat, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Metric = { impressions: number; clicks: number; ctr: number | null; position: number | null };
type Decay = {
  url: string;
  before: Metric;
  after: Metric;
  delta: { clicks_pct: number | null; impressions_pct: number | null; position_change: number | null };
  signal: string;
  review: string;
};
type Cannibal = {
  query: string;
  impressions: number;
  urls: { url: string; impression_share: number; before: Metric; after: Metric }[];
  previous_leader: string | null;
  current_leader: string | null;
  leader_changed: boolean;
  interpretation: string;
};
type Trend = {
  query: string;
  before: Metric;
  after: Metric;
  growth_pct: number | null;
  new_in_sample: boolean;
  interpretation: string;
};
type Result = {
  has_data: boolean;
  reason?: string;
  provider?: "google" | "bing";
  provider_label?: string;
  source?: string;
  start_date?: string;
  split_date?: string;
  end_date?: string;
  truncated?: boolean;
  observations?: number;
  decay: Decay[];
  cannibalisation: Cannibal[];
  trends: Trend[];
  notes?: string[];
};

type SeoExperiment = {
  id: number;
  site_id: number;
  title: string;
  category: string;
  hypothesis: string;
  applied_date: string;
  target_url: string | null;
  notes: string;
  conclusions: string;
};

type ExperimentMetrics = {
  has_data: boolean;
  reason?: string;
  title: string;
  category: string;
  target_url: string | null;
  applied_date: string;
  run_status: string;
  window_days: number;
  days_elapsed_post_change: number;
  before_window: { start: string; end: string; metrics: Metric };
  after_window: { start: string; end: string | null; target_end: string; metrics: Metric };
  delta: { clicks_pct: number | null; impressions_pct: number | null; position_change: number | null; ctr_change_pp: number | null };
  timeline: { date: string; is_experiment_marker: boolean; period: string; clicks: number; impressions: number; avg_position: number | null }[];
  interpretation: string;
  provider?: string;
  active_engine?: "google" | "bing";
};

const fmt = (n: number | null | undefined) => (n == null ? "–" : n.toLocaleString("de-DE", { maximumFractionDigits: 2 }));

export default function ContentIntelligence() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [days, setDays] = useState(28);
  const [provider, setProvider] = useState<"google" | "bing">("google");
  const [tab, setTab] = useState<"decay" | "cannibalisation" | "trends" | "experiments">("decay");

  // Experiment form state
  const [showAddExp, setShowAddExp] = useState(false);
  const [expTitle, setExpTitle] = useState("");
  const [expCategory, setExpCategory] = useState("content");
  const [expDate, setExpDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [expUrl, setExpUrl] = useState("");
  const [expHypothesis, setExpHypothesis] = useState("");
  const [expNotes, setExpNotes] = useState("");
  const [activeExpMetricsId, setActiveExpMetricsId] = useState<number | null>(null);
  const providerLabel = provider === "google" ? "Google Search Console" : "Bing Webmaster Tools";

  const result = useQuery<Result>({
    queryKey: ["content-intelligence", site?.id, days, provider],
    enabled: !!site,
    queryFn: () => api.get(`/sites/${site!.id}/content-intelligence`, { days, provider }),
  });

  const experiments = useQuery<{ items: SeoExperiment[]; count: number }>({
    queryKey: ["seo-experiments", site?.id],
    enabled: !!site,
    queryFn: () => api.get(`/sites/${site!.id}/experiments`),
  });

  const activeMetrics = useQuery<ExperimentMetrics>({
    queryKey: ["seo-experiment-metrics", site?.id, activeExpMetricsId, days, provider],
    enabled: !!site && activeExpMetricsId !== null,
    queryFn: () => api.get(`/sites/${site!.id}/experiments/${activeExpMetricsId}/metrics`, { days, engine: provider }),
  });

  const addExperiment = useMutation({
    mutationFn: () =>
      api.post(`/sites/${site!.id}/experiments`, {
        title: expTitle,
        category: expCategory,
        applied_date: expDate,
        target_url: expUrl.trim() || null,
        hypothesis: expHypothesis,
        notes: expNotes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["seo-experiments", site?.id] });
      setShowAddExp(false);
      setExpTitle("");
      setExpHypothesis("");
      setExpNotes("");
      setExpUrl("");
    },
  });

  const deleteExperiment = useMutation({
    mutationFn: (id: number) => api.del(`/sites/${site!.id}/experiments/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["seo-experiments", site?.id] });
      if (activeExpMetricsId) setActiveExpMetricsId(null);
    },
  });

  const data = result.data;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Content Intelligence & SEO-Experimente"
        description="Abnehmende Sichtbarkeit, URL-Überschneidungen, Keyword-Trends und empirisches Vorher-Nachher-Tracking von SEO-Änderungen."
      />
      {!site && (
        <Card>
          <EmptyState title="Website auswählen" />
        </Card>
      )}

      <Card title="Datenquelle und Vergleichszeitraum">
        <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-3 text-sm">
          Suchmaschine
          <Select value={provider} onChange={(e) => setProvider(e.target.value as "google" | "bing")} className="w-52" aria-label="Suchdatenquelle">
            <option value="google">Google Search Console</option>
            <option value="bing">Bing Webmaster Tools</option>
          </Select>
        </label>
        <label className="flex items-center gap-3 text-sm">
          Tage je Vergleichsfenster
          <Select value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-36">
            {[14, 28, 56, 90].map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
        </label>
        </div>
        <p className="mt-2 text-xs text-slate-500">Google und Bing werden getrennt ausgewertet; Durchschnittspositionen werden nicht zwischen Suchmaschinen vermischt.</p>
      </Card>

      <div role="tablist" aria-label="Content-Auswertung" className="flex flex-wrap gap-2">
        {([
          ["decay", "Content Decay"],
          ["cannibalisation", "URL-Überschneidung"],
          ["trends", "Trend-Radar"],
          ["experiments", "SEO-Experimente"],
        ] as const).map(([key, label]) => (
          <button
            role="tab"
            aria-selected={tab === key}
            key={key}
            onClick={() => setTab(key)}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
              tab === key
                ? "bg-brand-600 text-white"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            }`}
          >
            {label}
            {key === "experiments" && experiments.data?.count ? ` (${experiments.data.count})` : ""}
          </button>
        ))}
      </div>

      {tab === "experiments" && (
        <div className="space-y-4">
          <Card
            title="SEO-Experimente & Vorher-Nachher-Messung"
            description={`Datiere deine Maßnahmen und vergleiche Klicks und Positionen vor und nach der Änderung – aktuell aus ${provider === "google" ? "Google Search Console" : "Bing Webmaster Tools"}.`}
            actions={
              <Button variant="primary" onClick={() => setShowAddExp((v) => !v)}>
                {showAddExp ? "Abbrechen" : "Neues Experiment anlegen"}
              </Button>
            }
          >
            {showAddExp && (
              <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                <Field label="Titel der Maßnahme">
                  <Input
                    required
                    placeholder="z. B. Title-Tag und H1 auf Ratgeberseite überarbeitet"
                    value={expTitle}
                    onChange={(e) => setExpTitle(e.target.value)}
                  />
                </Field>

                <div className="grid gap-3 md:grid-cols-3">
                  <Field label="Kategorie">
                    <Select value={expCategory} onChange={(e) => setExpCategory(e.target.value)}>
                      <option value="content">Content & Text</option>
                      <option value="title_meta">Title & Meta Description</option>
                      <option value="internal_links">Interne Verlinkung</option>
                      <option value="schema">Strukturierte Daten (Schema)</option>
                      <option value="technical">Technisches SEO</option>
                      <option value="other">Sonstiges</option>
                    </Select>
                  </Field>

                  <Field label="Änderungsdatum">
                    <Input type="date" required value={expDate} onChange={(e) => setExpDate(e.target.value)} />
                  </Field>

                  <Field label="Ziel-URL (optional, leer = Website-weit)">
                    <Input
                      type="url"
                      placeholder={site?.url ? `${site.url}/seite` : "https://example.org/seite"}
                      value={expUrl}
                      onChange={(e) => setExpUrl(e.target.value)}
                    />
                  </Field>
                </div>

                <Field label="Hypothese (Was soll sich ändern?)">
                  <Input
                    placeholder="z. B. Klickanstieg um 30 % und Positionsverbesserung für Hauptsuchbegriff"
                    value={expHypothesis}
                    onChange={(e) => setExpHypothesis(e.target.value)}
                  />
                </Field>

                <Field label="Dokumentation & Notizen">
                  <Textarea
                    placeholder="Genauere Beschreibung der durchgeführten Optimierungen..."
                    rows={2}
                    value={expNotes}
                    onChange={(e) => setExpNotes(e.target.value)}
                  />
                </Field>

                <div className="flex justify-end gap-2">
                  <Button variant="secondary" onClick={() => setShowAddExp(false)}>
                    Abbrechen
                  </Button>
                  <Button
                    variant="primary"
                    disabled={!expTitle.trim() || !expDate || addExperiment.isPending}
                    onClick={() => addExperiment.mutate()}
                  >
                    Experiment speichern
                  </Button>
                </div>
                {addExperiment.error && <ErrorBox error={addExperiment.error} />}
              </div>
            )}
          </Card>

          {/* Active Experiment Metrics Evaluation Card */}
          {activeExpMetricsId !== null && (
            <Card
              title="Vorher / Nachher Auswertung"
              actions={
                <Button variant="ghost" size="sm" onClick={() => setActiveExpMetricsId(null)}>
                  Schließen
                </Button>
              }
            >
              {activeMetrics.isLoading && <Spinner label={`Berechne Vorher-Nachher-Metriken aus ${provider === "google" ? "Google" : "Bing"}…`} />}
              {activeMetrics.error && <ErrorBox error={activeMetrics.error} />}
              {activeMetrics.data && !activeMetrics.data.has_data && (
                <EmptyState
                  title="Keine Daten für dieses Zeitfenster"
                  description={activeMetrics.data.reason}
                  action={<Badge tone="blue">Geprüfte Quelle: {activeMetrics.data.provider ?? providerLabel}</Badge>}
                />
              )}
              {activeMetrics.data?.has_data && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3 dark:border-slate-800">
                    <div>
                      <h3 className="font-semibold">{activeMetrics.data.title}</h3>
                      <Badge tone="blue">{activeMetrics.data.provider ?? (provider === "google" ? "Google Search Console" : "Bing Webmaster Tools")}</Badge>
                      <p className="text-xs text-slate-500">
                        Änderungsdatum: {activeMetrics.data.applied_date} · Fenster: {activeMetrics.data.window_days} Tage vor vs. nach Änderung
                        {activeMetrics.data.target_url ? ` · Ziel-URL: ${activeMetrics.data.target_url}` : " · Website-weit"}
                      </p>
                    </div>
                    <Badge tone={activeMetrics.data.run_status === "completed" ? "green" : "blue"}>
                      {activeMetrics.data.run_status === "completed"
                        ? "Abgeschlossen"
                        : `Läuft (${activeMetrics.data.days_elapsed_post_change} von ${activeMetrics.data.window_days} Tagen)`}
                    </Badge>
                  </div>

                  {/* Before vs After stats */}
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <Stat
                      label="Klicks (Vorher → Nachher)"
                      value={`${fmt(activeMetrics.data.before_window.metrics.clicks)} → ${fmt(activeMetrics.data.after_window.metrics.clicks)}`}
                      hint={activeMetrics.data.delta.clicks_pct !== null ? `${activeMetrics.data.delta.clicks_pct > 0 ? "+" : ""}${activeMetrics.data.delta.clicks_pct} %` : undefined}
                      tone={
                        activeMetrics.data.delta.clicks_pct !== null && activeMetrics.data.delta.clicks_pct > 0
                          ? "good"
                          : activeMetrics.data.delta.clicks_pct !== null && activeMetrics.data.delta.clicks_pct < 0
                          ? "bad"
                          : undefined
                      }
                    />
                    <Stat
                      label="Impressionen"
                      value={`${fmt(activeMetrics.data.before_window.metrics.impressions)} → ${fmt(activeMetrics.data.after_window.metrics.impressions)}`}
                      hint={activeMetrics.data.delta.impressions_pct !== null ? `${activeMetrics.data.delta.impressions_pct > 0 ? "+" : ""}${activeMetrics.data.delta.impressions_pct} %` : undefined}
                    />
                    <Stat
                      label="Ø Position"
                      value={`${fmt(activeMetrics.data.before_window.metrics.position)} → ${fmt(activeMetrics.data.after_window.metrics.position)}`}
                      hint={
                        activeMetrics.data.delta.position_change !== null
                          ? `${activeMetrics.data.delta.position_change < 0 ? "Verbessert um " : "Verschlechtert um "}${Math.abs(activeMetrics.data.delta.position_change)}`
                          : undefined
                      }
                      tone={
                        activeMetrics.data.delta.position_change !== null && activeMetrics.data.delta.position_change < 0
                          ? "good"
                          : activeMetrics.data.delta.position_change !== null && activeMetrics.data.delta.position_change > 0
                          ? "bad"
                          : undefined
                      }
                    />
                    <Stat
                      label="CTR"
                      value={`${activeMetrics.data.before_window.metrics.ctr ? fmt(activeMetrics.data.before_window.metrics.ctr * 100) + " %" : "–"} → ${
                        activeMetrics.data.after_window.metrics.ctr ? fmt(activeMetrics.data.after_window.metrics.ctr * 100) + " %" : "–"
                      }`}
                      hint={activeMetrics.data.delta.ctr_change_pp !== null ? `${activeMetrics.data.delta.ctr_change_pp > 0 ? "+" : ""}${activeMetrics.data.delta.ctr_change_pp} %-Punkte` : undefined}
                    />
                  </div>

                  <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-950">
                    <strong>Interpretation: </strong>
                    <span className="text-slate-700 dark:text-slate-300">{activeMetrics.data.interpretation}</span>
                  </div>

                  {/* Daily Timeline */}
                  {activeMetrics.data.timeline.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase text-slate-500">Tagesverlauf (Vorher / Nachher)</h4>
                      <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-200 text-xs dark:border-slate-800">
                        <table className="w-full text-left">
                          <thead className="sticky top-0 bg-slate-100 dark:bg-slate-900">
                            <tr>
                              <th className="p-2">Datum</th>
                              <th className="p-2">Phase</th>
                              <th className="p-2 text-right">Klicks</th>
                              <th className="p-2 text-right">Impressionen</th>
                              <th className="p-2 text-right">Ø Position</th>
                            </tr>
                          </thead>
                          <tbody>
                            {activeMetrics.data.timeline.map((point) => (
                              <tr
                                key={point.date}
                                className={`border-b dark:border-slate-800 ${
                                  point.is_experiment_marker
                                    ? "bg-amber-100 font-bold dark:bg-amber-950"
                                    : point.period === "after"
                                    ? "bg-emerald-50/50 dark:bg-emerald-950/20"
                                    : ""
                                }`}
                              >
                                <td className="p-2">
                                  {point.date} {point.is_experiment_marker ? " ★ ÄNDERUNG" : ""}
                                </td>
                                <td className="p-2">{point.period === "before" ? "Vorher" : "Nachher"}</td>
                                <td className="p-2 text-right">{point.clicks}</td>
                                <td className="p-2 text-right">{point.impressions}</td>
                                <td className="p-2 text-right">{fmt(point.avg_position)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}

          {/* List of experiments */}
          <Card title="Erfasste SEO-Experimente">
            {experiments.isLoading && <Spinner label="Lade Experimente…" />}
            {experiments.error && <ErrorBox error={experiments.error} />}
            {experiments.data?.items.length === 0 && (
              <EmptyState
                title="Noch keine SEO-Experimente dokumentiert"
                description="Lege dein erstes Experiment an, um Title-, Content- oder Schema-Änderungen systematisch nachzumessen."
              />
            )}
            <div className="space-y-3">
              {experiments.data?.items.map((exp) => (
                <div
                  key={exp.id}
                  className={`rounded-lg border p-3 text-sm transition dark:border-slate-800 ${
                    activeExpMetricsId === exp.id ? "border-brand-500 bg-brand-50/20 dark:border-brand-400" : ""
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <strong className="text-base">{exp.title}</strong>
                        <Badge tone="blue">{exp.category}</Badge>
                        <span className="text-xs text-slate-500">Änderung: {exp.applied_date}</span>
                      </div>
                      {exp.target_url && (
                        <p className="mt-1 text-xs">
                          <span className="text-slate-500">Ziel-URL: </span>
                          <a href={exp.target_url} target="_blank" rel="noreferrer" className="underline break-all">
                            {exp.target_url}
                          </a>
                        </p>
                      )}
                      {exp.hypothesis && <p className="mt-1 text-xs italic text-slate-600 dark:text-slate-400">Hypothese: {exp.hypothesis}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant={activeExpMetricsId === exp.id ? "primary" : "secondary"}
                        onClick={() => setActiveExpMetricsId(activeExpMetricsId === exp.id ? null : exp.id)}
                      >
                        {activeExpMetricsId === exp.id ? "Ausblenden" : "Vorher/Nachher messen"}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => deleteExperiment.mutate(exp.id)}>
                        Löschen
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {tab !== "experiments" && (
        <>
          {result.isLoading && (
            <Card>
              <Spinner />
            </Card>
          )}
          {result.error && <ErrorBox error={result.error} onRetry={() => result.refetch()} />}
          {data && !data.has_data && <Card><EmptyState
            title="Keine datierten Query-URL-Daten"
            description={data.reason}
            action={<Badge tone="blue">Geprüfte Quelle: {data.provider_label ?? providerLabel}</Badge>}
          /></Card>}
          {data?.has_data && (
            <>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Seiten mit Rückgang" value={fmt(data.decay.length)} />
                <Stat label="URL-Überschneidungen" value={fmt(data.cannibalisation.length)} />
                <Stat label="Wachsende Keywords" value={fmt(data.trends.length)} />
                <Stat label={`${provider === "google" ? "Google" : "Bing"}-Zeilen geprüft`} value={fmt(data.observations)} />
              </div>
              <Card title="Datenherkunft und Interpretation">
                <p className="text-sm">
                  Quelle: {data.provider_label ?? (provider === "google" ? "Google Search Console" : "Bing Webmaster Tools")} ({data.source?.toUpperCase()}) · {data.start_date} bis {data.end_date}; neuester Zeitraum ab {data.split_date}.
                </p>
                {(data.notes ?? []).map((note, i) => (
                  <p className="mt-1 text-xs text-slate-500" key={i}>
                    {note}
                  </p>
                ))}
              </Card>

              {tab === "decay" && (
                <Card title="Seiten mit gemessenem Klickrückgang">
                  {!data.decay.length && <EmptyState title="Keine relevanten Rückgänge im Vergleichszeitraum" />}
                  {data.decay.map((item) => (
                    <div className="border-b py-3 text-sm dark:border-slate-800" key={item.url}>
                      <a href={item.url} className="break-all font-medium underline" target="_blank" rel="noreferrer">
                        {item.url}
                      </a>
                      <p>
                        Clicks: {fmt(item.before.clicks)} → {fmt(item.after.clicks)} ({fmt(item.delta.clicks_pct)} %) · Impressionen:{" "}
                        {fmt(item.before.impressions)} → {fmt(item.after.impressions)}
                      </p>
                      <p>
                        Ø Position: {fmt(item.before.position)} → {fmt(item.after.position)} · Hinweis: {item.signal}
                      </p>
                      <p className="text-xs text-slate-500">{item.review}</p>
                    </div>
                  ))}
                </Card>
              )}
              {tab === "cannibalisation" && (
                <Card title="Mehrere relevante Landingpages derselben Suchanfrage">
                  {!data.cannibalisation.length && <EmptyState title="Keine auffällige URL-Überschneidung" />}
                  {data.cannibalisation.map((item) => (
                    <div className="border-b py-3 text-sm dark:border-slate-800" key={item.query}>
                      <strong>{item.query}</strong> · {fmt(item.impressions)} Impressionen
                      {item.leader_changed && <p className="font-medium text-amber-600">Die meistgezeigte URL hat zwischen den Zeitfenstern gewechselt.</p>}
                      <div className="mt-2 space-y-1">
                        {item.urls.map((u) => (
                          <p key={u.url} className="break-all text-xs">
                            <a href={u.url} target="_blank" rel="noreferrer" className="underline">
                              {u.url}
                            </a>{" "}
                            · Anteil {fmt(u.impression_share * 100)} % · {fmt(u.before.impressions)} → {fmt(u.after.impressions)} Impressionen
                          </p>
                        ))}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{item.interpretation}</p>
                    </div>
                  ))}
                </Card>
              )}
              {tab === "trends" && (
                <Card title="Neue oder stärker sichtbare Suchanfragen">
                  {!data.trends.length && <EmptyState title="Keine passenden Keywords in der Stichprobe" />}
                  {data.trends.map((item) => (
                    <div className="border-b py-3 text-sm dark:border-slate-800" key={item.query}>
                      <strong>{item.query}</strong> · {fmt(item.before.impressions)} → {fmt(item.after.impressions)} Impressionen
                      {item.new_in_sample ? " · Neu in der Stichprobe" : ` · +${fmt(item.growth_pct)} %`}
                      <p className="text-xs text-slate-500">{item.interpretation}</p>
                    </div>
                  ))}
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
