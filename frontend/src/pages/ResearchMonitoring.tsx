import { useQuery } from "@tanstack/react-query";
import { Card, EmptyState, ErrorBox, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Timeline = { items: { id: number; title: string; date: string;
  comparison: { keyword: string; before: number; after: number; delta: number; provider: string }[]; warning: string }[]; method: string };
type Serp = { sources: { provider: string; features: Record<string, number> }[]; method: string };
type Indexing = { items: { id: number; url: string; reported_status: string; technically_indexable: boolean | null;
  crawl_found: boolean; discrepancy_to_review: boolean; verified_google_index_status: boolean }[]; method: string };
type Citations = { platforms: { platform: string; citations: { url: string; sample_count: number }[] }[];
  samples_reviewed: number; method: string };

export default function ResearchMonitoring() {
  const { site } = useSite();
  const root = "/sites/" + site?.id + "/research";
  const timeline = useQuery<Timeline>({ queryKey: ["research-timeline", site?.id],
    queryFn: () => api.get(root + "/change-timeline"), enabled: !!site });
  const serp = useQuery<Serp>({ queryKey: ["research-serp-features", site?.id],
    queryFn: () => api.get(root + "/serp-features"), enabled: !!site });
  const indexing = useQuery<Indexing>({ queryKey: ["research-indexing", site?.id],
    queryFn: () => api.get(root + "/indexing-review"), enabled: !!site });
  const geo = useQuery<Citations>({ queryKey: ["research-geo", site?.id],
    queryFn: () => api.get(root + "/geo-citations"), enabled: !!site });
  const queries = [timeline, serp, indexing, geo];
  return <div className="space-y-4">
    <PageHeader title="SEO-Veränderungen & Sichtbarkeitsbelege" description="Ereignisse, SERP-Merkmale, Indexierungsbeobachtungen und KI-Zitationen transparent aus real vorhandenen Stichproben vergleichen." />
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {queries.some((q) => q.isLoading) && <Card><Spinner /></Card>}
    {queries.map((q, i) => q.error ? <ErrorBox key={i} error={q.error} /> : null)}
    <Card title="Ereignis- und Positionshistorie">
      {!timeline.data?.items.length && <EmptyState title="Keine datierten SEO-Ereignisse protokolliert" />}
      {timeline.data?.items.map((event) => <div className="mb-3 text-sm" key={event.id}>
        <strong>{event.date} · {event.title}</strong>
        {event.comparison.map((c, i) => <p key={i} className="text-xs">
          {c.keyword} ({c.provider}): {c.before} → {c.after}, Differenz {c.delta > 0 ? "+" : ""}{c.delta}</p>)}
        <p className="text-xs text-slate-500">{event.warning}</p>
      </div>)}
      <p className="text-xs text-slate-500">{timeline.data?.method}</p>
    </Card>
    <Card title="Beobachtete SERP-Features">
      {!serp.data?.sources.length && <EmptyState title="Keine SERP-Features protokolliert" />}
      {serp.data?.sources.map((x) => <p key={x.provider} className="text-sm">{x.provider}: {Object.entries(x.features)
        .map(([k, n]) => k + " (" + n + ")").join(", ")}</p>)}
      <p className="mt-2 text-xs text-slate-500">{serp.data?.method}</p>
    </Card>
    <Card title="Indexierungsprotokoll im Crawl-Abgleich">
      {!indexing.data?.items.length && <EmptyState title="Keine manuell gemeldeten Indexierungszustände" />}
      {indexing.data?.items.map((x) => <div key={x.id} className="mb-2 text-sm">
        <p className="break-all font-medium">{x.url}</p>
        <p className="text-xs">Gemeldet: {x.reported_status} · Crawl: {x.crawl_found ? "vorhanden" : "nicht gefunden"}
          {" · "}technisch indexierbar: {x.technically_indexable === null ? "unbekannt" : x.technically_indexable ? "ja" : "nein"}
          {x.discrepancy_to_review ? " · Widerspruch prüfen" : ""}</p>
      </div>)}
      <p className="text-xs text-slate-500">{indexing.data?.method}</p>
    </Card>
    <Card title="Dokumentierte KI-Zitationen">
      <p className="mb-2 text-xs text-slate-500">{geo.data?.samples_reviewed ?? 0} erfasste Beobachtungen, keine repräsentative Reichweite.</p>
      {!geo.data?.platforms.length && <EmptyState title="Keine KI-Quellenstichproben" />}
      {geo.data?.platforms.map((p) => <div key={p.platform} className="mb-3 text-sm">
        <strong>{p.platform}</strong>{p.citations.map((c) => <p key={c.url} className="break-all text-xs">
          {c.url} · {c.sample_count} erfasste Nennungen</p>)}
      </div>)}
      <p className="text-xs text-slate-500">{geo.data?.method}</p>
    </Card>
  </div>;
}
