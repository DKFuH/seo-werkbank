import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card, EmptyState, ErrorBox, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

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

export default function AuthorityIntelligence() {
  const { site } = useSite();
  const root = "/sites/" + site?.id + "/authority";
  const dirs = useQuery<Directories>({ queryKey: ["authority-directories", site?.id],
    queryFn: () => api.get(root + "/directories"), enabled: !!site });
  const ai = useQuery<Stability>({ queryKey: ["authority-stability", site?.id],
    queryFn: () => api.get(root + "/ai-source-stability"), enabled: !!site });
  return <div className="space-y-4">
    <PageHeader title="Verzeichnisqualität & KI-Quellen" description="Nachvollziehbare Verzeichnisentscheidungen und wiederholt beobachtete KI-Quellen – ohne erfundene Linkstärke." />
    <Card title="Branchenverzeichnisse fachlich vergleichen">
      <p className="mb-3 text-sm text-slate-500">Neue Prüfungen unter <Link to="/research" className="underline">Content → SEO-Research</Link> mit der Kategorie „Verzeichnisqualität“ erfassen.
        Relevanz und redaktioneller Nutzwert sind persönliche Bewertungen von 0 bis 3, keine Google-Metrik.</p>
      {dirs.isLoading && <Spinner />}
      {dirs.error && <ErrorBox error={dirs.error} />}
      {dirs.data && dirs.data.items.length === 0 && <EmptyState title="Noch keine Verzeichnisbewertungen dokumentiert" />}
      {dirs.data?.items.map(x => <div key={x.id} className="mb-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
        <strong>{x.directory}</strong>
        <p className="break-all text-xs text-slate-500">{x.listing_url}</p>
        <p>Eigene Relevanz: {x.relevance_assessed ?? "?"}/3 · redaktioneller Nutzwert: {x.editorial_value_assessed ?? "?"}/3</p>
        <p>Einordnung: {x.manual_quality_label}</p>
        <p className="text-xs text-slate-500">Kosten: {x.cost_eur_reported ?? "unbekannt"} EUR
          {" · "}Referral-Besuche: {x.referral_visits_reported ?? "unbekannt"}
          {" · "}Kosten/Besuch: {x.cost_per_visit ?? "nicht berechenbar"}</p>
        <p className="text-xs text-slate-500">Nachweise: {x.matched_backlink_count} passende importierte Backlink-Datensätze
          {" · "}Verzeichnisimport: {x.listed_in_imported_citations ? "ja" : "nein"}</p>
      </div>)}
      <p className="text-xs text-slate-500">{dirs.data?.method}</p>
    </Card>
    <Card title="KI-Quellen: wiederholte Beobachtungen">
      {ai.isLoading && <Spinner />}
      {ai.error && <ErrorBox error={ai.error} />}
      {ai.data && ai.data.items.length === 0 && <EmptyState title="Noch keine KI-Quellenstichproben mit wiederholten Testfragen" />}
      <p className="mb-3 text-xs text-slate-500">{ai.data?.observations_considered ?? 0} dokumentierte Stichproben; keine repräsentative KI-Reichweite.</p>
      {ai.data?.items.map((group, index) => <div key={group.platform + group.prompt + index}
        className="mb-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
        <strong>{group.platform} · {group.prompt}</strong>
        <p className="text-xs text-slate-500">{group.sample_count} Stichproben an {group.sampled_days} Tagen</p>
        {group.sources.map(x => <p className="break-all text-xs" key={x.url}>
          {x.url} · {x.distinct_days_cited} unterschiedliche Tage
          {x.repeated_on_multiple_days ? " · wiederholt beobachtet" : " · einzelne Tagesbeobachtung"}
        </p>)}
        <p className="mt-1 text-xs text-slate-500">{group.interpretation}</p>
      </div>)}
      <p className="text-xs text-slate-500">{ai.data?.method}</p>
    </Card>
  </div>;
}
