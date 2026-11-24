import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, EmptyState, ErrorBox, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Metric = { impressions: number; clicks: number; ctr: number | null; position: number | null };
type Decay = { url: string; before: Metric; after: Metric; delta: { clicks_pct: number | null; impressions_pct: number | null; position_change: number | null }; signal: string; review: string };
type Cannibal = { query: string; impressions: number; urls: { url: string; impression_share: number; before: Metric; after: Metric }[]; previous_leader: string | null; current_leader: string | null; leader_changed: boolean; interpretation: string };
type Trend = { query: string; before: Metric; after: Metric; growth_pct: number | null; new_in_sample: boolean; interpretation: string };
type Result = { has_data: boolean; reason?: string; source?: string; start_date?: string; split_date?: string; end_date?: string; truncated?: boolean; observations?: number; decay: Decay[]; cannibalisation: Cannibal[]; trends: Trend[]; notes?: string[] };
const fmt = (n: number | null | undefined) => n == null ? "–" : n.toLocaleString("de-DE", { maximumFractionDigits: 2 });

export default function ContentIntelligence() {
  const { site } = useSite();
  const [days, setDays] = useState(28);
  const [tab, setTab] = useState<"decay" | "cannibalisation" | "trends">("decay");
  const result = useQuery<Result>({
    queryKey: ["content-intelligence", site?.id, days],
    enabled: !!site, queryFn: () => api.get(`/sites/${site!.id}/content-intelligence`, { days }),
  });
  const data = result.data;
  return <div className="space-y-4">
    <PageHeader title="Content Intelligence" description="Abnehmende Sichtbarkeit, URL-Überschneidungen und wachsende Suchanfragen aus tatsächlichen GSC-Daten – ohne erfundene Suchvolumina." />
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    <Card title="Vergleichszeitraum">
      <label className="flex items-center gap-3 text-sm">Tage je Vergleichsfenster
        <Select value={days} onChange={e => setDays(Number(e.target.value))} className="w-36">
          {[14, 28, 56, 90].map(d => <option key={d} value={d}>{d}</option>)}
        </Select>
      </label>
    </Card>
    {result.isLoading && <Card><Spinner /></Card>}
    {result.error && <ErrorBox error={result.error} onRetry={() => result.refetch()} />}
    {data && !data.has_data && <Card><EmptyState title="Keine datierten GSC-Query-URL-Daten" description={data.reason} /></Card>}
    {data?.has_data && <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Seiten mit Rückgang" value={fmt(data.decay.length)} />
        <Stat label="URL-Überschneidungen" value={fmt(data.cannibalisation.length)} />
        <Stat label="Wachsende Keywords" value={fmt(data.trends.length)} />
        <Stat label="GSC-Zeilen geprüft" value={fmt(data.observations)} />
      </div>
      <Card title="Datenherkunft und Interpretation">
        <p className="text-sm">Quelle: GSC {data.source?.toUpperCase()} · {data.start_date} bis {data.end_date}; neuester Zeitraum ab {data.split_date}.</p>
        {(data.notes ?? []).map((note, i) => <p className="mt-1 text-xs text-slate-500" key={i}>{note}</p>)}
      </Card>
      <div role="tablist" aria-label="Content-Auswertung" className="flex flex-wrap gap-2">
        {([["decay", "Content Decay"], ["cannibalisation", "URL-Überschneidung"], ["trends", "Trend-Radar"]] as const).map(([key, label]) =>
          <button role="tab" aria-selected={tab === key} key={key} onClick={() => setTab(key)}
            className={`rounded-lg border px-3 py-2 text-sm ${tab === key ? "bg-brand-600 text-white" : "border-slate-300 dark:border-slate-700"}`}>{label}</button>)}
      </div>
      {tab === "decay" && <Card title="Seiten mit gemessenem Klickrückgang">
        {!data.decay.length && <EmptyState title="Keine relevanten Rückgänge im Vergleichszeitraum" />}
        {data.decay.map(item => <div className="border-b py-3 text-sm dark:border-slate-800" key={item.url}>
          <a href={item.url} className="break-all font-medium underline" target="_blank" rel="noreferrer">{item.url}</a>
          <p>Clicks: {fmt(item.before.clicks)} → {fmt(item.after.clicks)} ({fmt(item.delta.clicks_pct)} %) · Impressionen: {fmt(item.before.impressions)} → {fmt(item.after.impressions)}</p>
          <p>Ø Position: {fmt(item.before.position)} → {fmt(item.after.position)} · Hinweis: {item.signal}</p>
          <p className="text-xs text-slate-500">{item.review}</p>
        </div>)}
      </Card>}
      {tab === "cannibalisation" && <Card title="Mehrere relevante Landingpages derselben Suchanfrage">
        {!data.cannibalisation.length && <EmptyState title="Keine auffällige URL-Überschneidung" />}
        {data.cannibalisation.map(item => <div className="border-b py-3 text-sm dark:border-slate-800" key={item.query}>
          <strong>{item.query}</strong> · {fmt(item.impressions)} Impressionen
          {item.leader_changed && <p className="font-medium text-amber-600">Die meistgezeigte URL hat zwischen den Zeitfenstern gewechselt.</p>}
          <div className="mt-2 space-y-1">{item.urls.map(u => <p key={u.url} className="break-all text-xs">
            <a href={u.url} target="_blank" rel="noreferrer" className="underline">{u.url}</a> · Anteil {fmt(u.impression_share * 100)} % · {fmt(u.before.impressions)} → {fmt(u.after.impressions)} Impressionen
          </p>)}</div>
          <p className="mt-1 text-xs text-slate-500">{item.interpretation}</p>
        </div>)}
      </Card>}
      {tab === "trends" && <Card title="Neue oder stärker sichtbare Suchanfragen">
        {!data.trends.length && <EmptyState title="Keine passenden Keywords in der Stichprobe" />}
        {data.trends.map(item => <div className="border-b py-3 text-sm dark:border-slate-800" key={item.query}>
          <strong>{item.query}</strong> · {fmt(item.before.impressions)} → {fmt(item.after.impressions)} Impressionen
          {item.new_in_sample ? " · Neu in der Stichprobe" : ` · +${fmt(item.growth_pct)} %`}
          <p className="text-xs text-slate-500">{item.interpretation}</p>
        </div>)}
      </Card>}
    </>}
  </div>;
}
