/* Former "Verzeichnisse & KI-Quellen" page, split by topic: directory quality sits on Lokale Nachweise,
   AI source stability on KI-Erwähnungen. Backend: /api/sites/{id}/authority/... */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, Card, EmptyState, ErrorBox, Spinner } from "./ui";

type Directory = { id: number; directory: string; listing_url: string;
  relevance_assessed: number | null; editorial_value_assessed: number | null;
  cost_eur_reported: number | null; referral_visits_reported: number | null;
  cost_per_visit: number | null; manual_quality_label: string; verified: false;
  listed_in_imported_citations: boolean; matched_backlink_count: number;
  backlink_statuses: Record<string, number> };
type Directories = { items: Directory[]; method: string };
type Group = { platform: string; prompt: string; sample_count: number; sampled_days: number;
  sources: { url: string; distinct_days_cited: number; repeated_on_multiple_days: boolean }[];
  interpretation: string };
type Stability = { observations_considered: number; items: Group[]; method: string };

const muted = "text-xs text-slate-500 dark:text-slate-400";
const box = "mb-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800";

export function DirectoryQualityPanel({ siteId }: { siteId: number }) {
  const q = useQuery<Directories>({ queryKey: ["authority-directories", siteId],
    queryFn: () => api.get("/sites/" + siteId + "/authority/directories") });
  return (
    <Card title="Branchenverzeichnisse bewerten" description="Lohnt sich ein Verzeichniseintrag? Eigene Einschätzung von Relevanz und Nutzwert, abgeglichen mit importierten Einträgen und Backlinks.">
      <p className={"mb-3 " + muted}>Neue Bewertungen unter <Link to="/research" className="underline">Content → SEO-Research</Link>, Kategorie „Verzeichnisqualität“.
        Relevanz und Nutzwert sind eigene Bewertungen von 0 bis 3, keine Google-Metrik.</p>
      {q.isLoading && <Spinner />}
      {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <EmptyState title="Noch keine Verzeichnisbewertungen" />}
      {q.data?.items.map((x) => (
        <div key={x.id} className={box}>
          <div className="flex flex-wrap items-center gap-2">
            <strong>{x.directory}</strong>
            <Badge tone="gray">{x.manual_quality_label}</Badge>
            {x.listed_in_imported_citations && <Badge tone="blue">im Verzeichnisimport</Badge>}
          </div>
          <p className={"break-all " + muted}>{x.listing_url}</p>
          <p>Relevanz {x.relevance_assessed ?? "?"}/3 · Nutzwert {x.editorial_value_assessed ?? "?"}/3</p>
          <p className={muted}>Kosten: {x.cost_eur_reported ?? "unbekannt"} € · Besuche: {x.referral_visits_reported ?? "unbekannt"} · Kosten/Besuch: {x.cost_per_visit ?? "nicht berechenbar"}
            {" · "}{x.matched_backlink_count} passende Backlink-Datensätze</p>
        </div>
      ))}
      <p className={muted}>{q.data?.method}</p>
    </Card>
  );
}

export function AiSourceStabilityPanel({ siteId }: { siteId: number }) {
  const q = useQuery<Stability>({ queryKey: ["authority-stability", siteId],
    queryFn: () => api.get("/sites/" + siteId + "/authority/ai-source-stability") });
  return (
    <Card title="Wiederkehrende KI-Quellen" description="Welche URLs werden bei derselben Frage an mehreren Tagen zitiert? Gleiche Frage an verschiedenen Tagen erneut stellen und erfassen.">
      {q.isLoading && <Spinner />}
      {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <EmptyState title="Noch keine wiederholten Testfragen" description="Sobald dieselbe Frage auf derselben Plattform an mehreren Tagen erfasst ist, erscheint sie hier." />}
      {q.data && q.data.items.length > 0 && <p className={"mb-3 " + muted}>{q.data.observations_considered} dokumentierte Stichproben, nicht repräsentativ.</p>}
      {q.data?.items.map((g, i) => (
        <div key={g.platform + g.prompt + i} className={box}>
          <strong>{g.platform} · {g.prompt}</strong>
          <p className={muted}>{g.sample_count} Stichproben an {g.sampled_days} Tagen</p>
          {g.sources.map((x) => (
            <p key={x.url} className="break-all text-xs">{x.url} · an {x.distinct_days_cited} Tagen
              {x.repeated_on_multiple_days ? <Badge tone="green">wiederholt</Badge> : <span className="text-slate-400"> · einmalig</span>}</p>
          ))}
          <p className={"mt-1 " + muted}>{g.interpretation}</p>
        </div>
      ))}
      <p className={muted}>{q.data?.method}</p>
    </Card>
  );
}
