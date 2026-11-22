import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Card, EmptyState, ErrorBox, PageHeader, Select, Spinner, Url } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt } from "../lib/format";

type Topic = { term: string; competitor_count: number; observed_page_count: number;
  examples: { competitor: string; url: string; title: string | null }[] };
type Result = { has_data: boolean; reason?: string; topics: Topic[]; total_topics?: number;
  competitors_with_crawl?: number; method?: string };

export default function CompetitorRadar() {
  const { site } = useSite();
  const [minimum, setMinimum] = useState(1);
  const q = useQuery<Result>({
    queryKey: ["competitor-topic-radar", site?.id],
    queryFn: () => api.get("/sites/" + site!.id + "/competitor-topic-radar", { limit: 300 }),
    enabled: !!site,
  });
  const topics = (q.data?.topics ?? []).filter((t) => t.competitor_count >= minimum);
  return <div className="space-y-4">
    <PageHeader title="Wettbewerber-Themenradar" description="Themenindikatoren aus echten Wettbewerber-Crawls: Wortpaare in Titeln und H1s, die im eigenen Crawl nicht auftauchen." />
    <Card title="Datenqualität und Interpretation">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Die Liste basiert ausschließlich auf gecrawlten Seitentiteln und H1s. Eine fehlende Wortkombination ist
        <strong> kein Nachweis</strong>, dass du das Thema nicht behandelst. Auch Suchvolumen, Traffic,
        Nachfrage, Konkurrenzrankings und Kaufabsicht werden nicht behauptet.
      </p>
      <p className="mt-2 text-sm"><Link to="/competitors" className="font-medium text-brand-700 underline dark:text-brand-300">Wettbewerber und Crawls verwalten</Link></p>
    </Card>
    <Card title="Filter">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">Mindestens so viele Wettbewerber
          <Select value={minimum} onChange={(e) => setMinimum(Number(e.target.value))} className="mt-1 max-w-40">
            {[1, 2, 3, 4, 5].map((v) => <option key={v} value={v}>{v}</option>)}
          </Select>
        </label>
        {q.data?.has_data && <span className="text-sm text-slate-500">
          {fmtInt(q.data.competitors_with_crawl)} Wettbewerber mit Crawl · {fmtInt(q.data.total_topics)} Termkandidaten
        </span>}
      </div>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {q.isLoading && <Card><Spinner /></Card>}
    {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
    {q.data && !q.data.has_data && <Card><EmptyState title="Keine auswertbaren Wettbewerber-Crawls" description={q.data.reason ?? "Eigenen Crawl und mindestens einen Wettbewerber-Crawl abschließen."} /></Card>}
    {q.data?.has_data && !topics.length && <Card><EmptyState title="Keine Themen mit diesem Filter" /></Card>}
    {topics.map((t) => <Card key={t.term} title={t.term}>
      <div className="mb-2 flex flex-wrap gap-2">
        <Badge tone="blue">{t.competitor_count} Wettbewerber</Badge>
        <Badge>{t.observed_page_count} gecrawlte Seiten</Badge>
      </div>
      <ul className="space-y-2">{t.examples.map((ex) => <li key={ex.url} className="text-sm">
        <strong>{ex.competitor}:</strong> <Url href={ex.url} label={ex.title || ex.url} />
      </li>)}</ul>
    </Card>)}
  </div>;
}
