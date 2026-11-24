import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, EmptyState, ErrorBox, Input, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum, shortUrl } from "../lib/format";

type GapCategory = "new_candidate" | "expand" | "review" | "no_action";
type QueryEvidence = {
  query: string; category: GapCategory; reason: string; impressions: number; clicks: number;
  position: number | null; ranked_url: string; ranked_crawl_found: boolean;
  ranked_title_coverage: number | null; ranked_body_coverage: number | null;
  best_existing_url: string | null; best_existing_coverage: number;
  multiple_landing_urls: boolean; landing_urls: { url: string; impressions: number; clicks: number }[];
};
type GapCluster = {
  id: number; query: string; category: GapCategory; queries: QueryEvidence[];
  impressions: number; clicks: number; ranked_url: string;
  best_existing_url: string | null; multiple_landing_urls: boolean;
};
type GapResult = {
  has_data: boolean; reason?: string; source?: "api" | "csv"; crawl_id?: number;
  start_date?: string | null; end_date?: string | null; total_clusters?: number;
  queries_considered?: number; truncated?: boolean; truncated_pairs?: boolean;
  truncated_pages?: boolean; crawl_pages_compared?: number; clusters: GapCluster[];
  notes?: string[]; method?: string;
};
const CAT: Record<GapCategory, { label: string; tone: string }> = {
  new_candidate: { label: "Neuen Inhalt prüfen", tone: "blue" },
  expand: { label: "Bestehenden Inhalt erweitern", tone: "amber" },
  review: { label: "Zuordnung / Suchintention prüfen", tone: "purple" },
  no_action: { label: "Vorerst keine Maßnahme", tone: "gray" },
};

export default function ContentGap() {
  const { site } = useSite();
  const [days, setDays] = useState(90);
  const [minImpressions, setMinImpressions] = useState(10);
  const [filter, setFilter] = useState("all");
  const [message, setMessage] = useState("");
  const [targets, setTargets] = useState<Record<number, string>>({});
  const result = useQuery<GapResult>({
    queryKey: ["content-gap", site?.id, days, minImpressions],
    queryFn: () => api.get(`/sites/${site!.id}/content-gap`, { days, min_impressions: minImpressions }),
    enabled: !!site?.id,
  });
  const save = useMutation({
    mutationFn: (data: { query: string; target_url: string; action: GapCategory }) =>
      api.post(`/sites/${site!.id}/content-gap/work`, data),
    onSuccess: x => setMessage(`Redaktionelle Maßnahme #${x.id} erstellt (nicht veröffentlicht).`),
    onError: e => setMessage(errorMessage(e)),
  });
  const d = result.data;
  const shown = useMemo(() => (d?.clusters ?? []).filter(c => filter === "all" || c.category === filter), [d, filter]);
  const makeBrief = async (cluster: GapCluster) => {
    const rows = [
      "Content-Gap-Briefing – vor einer Umsetzung manuell prüfen",
      `Website: ${site?.url ?? ""}`,
      `Keywordgruppe: ${cluster.query}`,
      `Empfehlung: ${CAT[cluster.category].label}`,
      `Rankende GSC-URL: ${cluster.ranked_url}`,
      `Mögliche bestehende Zielseite: ${cluster.best_existing_url ?? "nicht eindeutig"}`,
      `Impressionen der einzelnen Suchanfragen addiert: ${cluster.impressions} (kein Suchvolumen)`,
      ...cluster.queries.map(q => [
        `Suchanfrage: ${q.query}`,
        `GSC: ${q.impressions} Impressionen, ${q.clicks} Klicks, Ø Position ${q.position ?? "unbekannt"}`,
        `Rankende URL: ${q.ranked_url}`,
        q.reason,
      ].join("\n")),
      "Prüfen: bestehende Seiten, tatsächliche Suchintention, SERP, Kannibalisierungsrisiken und redaktionellen Mehrwert.",
      "Die Werkbank erstellt und veröffentlicht keine Artikel automatisch.",
    ];
    try {
      await navigator.clipboard.writeText(rows.join("\n\n"));
      setMessage("Briefing in die Zwischenablage kopiert.");
    } catch {
      setMessage("Kopieren nicht möglich; Browserberechtigung prüfen.");
    }
  };

  return <div className="space-y-4">
    <PageHeader title="Content-Gap-Analyse" description="GSC-Suchanfragen samt rankenden URLs mit Titeln, Überschriften und Text aus dem letzten Website-Crawl vergleichen." />
    {!site && <Card><EmptyState title="Website auswählen" description="Wähle eine Website mit GSC-Daten und abgeschlossenem Crawl." /></Card>}
    <Card title="Untersuchung konfigurieren">
      <div className="flex flex-wrap items-end gap-3">
        <label className="space-y-1 text-xs">Zeitraum (Tage)
          <Select value={days} onChange={e => setDays(Number(e.target.value))} className="w-40">
            {[28, 56, 90, 180, 365].map(n => <option key={n} value={n}>{n} Tage</option>)}
          </Select>
        </label>
        <label className="space-y-1 text-xs">Mindestimpressionen je Suchanfrage
          <Input type="number" min={1} max={100000} value={minImpressions}
            onChange={e => setMinImpressions(Math.max(1, Number(e.target.value) || 1))} className="w-40" />
        </label>
        <label className="space-y-1 text-xs">Empfehlung
          <Select value={filter} onChange={e => setFilter(e.target.value)} className="w-60">
            <option value="all">Alle Kategorien</option>
            {Object.entries(CAT).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}
          </Select>
        </label>
      </div>
    </Card>
    {result.isLoading && <Card><Spinner label="Content-Abdeckung wird geprüft…" /></Card>}
    {result.error && <ErrorBox error={result.error} onRetry={() => result.refetch()} />}
    {d && !d.has_data && <Card><EmptyState title="Noch keine auswertbaren Daten" description={d.reason} />
      <p className="mt-3 text-sm"><Link to="/search-console" className="underline">GSC-Daten laden</Link> · <Link to="/crawler" className="underline">Website crawlen</Link></p>
    </Card>}
    {d?.has_data && <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Keywordgruppen" value={fmtInt(d.total_clusters ?? 0)} />
        <Stat label="Suchanfragen geprüft" value={fmtInt(d.queries_considered ?? 0)} />
        <Stat label="Crawl-Seiten verglichen" value={fmtInt(d.crawl_pages_compared ?? 0)} />
        <Stat label="GSC-Datenquelle" value={d.source === "api" ? "API" : "CSV"} />
      </div>
      <Card title="Datenqualität und Grenzen">
        <p className="text-sm">Vergleich mit Crawl #{d.crawl_id}. GSC-Zeitraum: {d.start_date ?? "ohne Datum"} bis {d.end_date ?? "ohne Datum"}. Diese Einordnung ist eine lexikalische Heuristik, keine automatische Suchintent- oder Kannibalisierungsbestätigung.</p>
        {(d.notes ?? []).map((n, i) => <p key={i} className="mt-2 text-xs text-amber-700 dark:text-amber-300">{n}</p>)}
        {(d.truncated || d.truncated_pairs || d.truncated_pages) && <p className="mt-2 text-xs font-medium">Auswertung wurde zur Laufzeitbegrenzung gekürzt; fehlende Treffer sind kein Beleg für fehlende Inhalte.</p>}
      </Card>
      {shown.length === 0 && <Card><EmptyState title="Keine passenden Keywordgruppen" description="Mindestimpressionen, Zeitraum oder Kategorie anpassen." /></Card>}
      {shown.map(cluster => <Card key={cluster.id} title={cluster.query}
        actions={<Button size="sm" onClick={() => void makeBrief(cluster)}>Briefing kopieren</Button>}>
        <div className="mb-3 flex flex-wrap gap-2">
          <Badge tone={CAT[cluster.category].tone}>{CAT[cluster.category].label}</Badge>
          {cluster.multiple_landing_urls && <Badge tone="amber">Mehrere relevante Landingpages – prüfen</Badge>}
          <span className="text-xs text-slate-500">{fmtInt(cluster.impressions)} GSC-Impressionen · {fmtInt(cluster.clicks)} Klicks · {cluster.queries.length} Suchanfragen</span>
        </div>
        <p className="break-all text-xs">Aktuell rankend: <a href={cluster.ranked_url} target="_blank" rel="noreferrer" className="underline">{shortUrl(cluster.ranked_url)}</a></p>
        {cluster.best_existing_url && <p className="break-all text-xs">Weitere vorhandene Seite: <a href={cluster.best_existing_url} target="_blank" rel="noreferrer" className="underline">{shortUrl(cluster.best_existing_url)}</a></p>}
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[580px] text-left text-xs">
            <thead><tr className="border-b dark:border-slate-800"><th className="pb-2">GSC-Suchanfrage</th><th className="pb-2">Messwerte</th><th className="pb-2">Begründung</th></tr></thead>
            <tbody>{cluster.queries.map(q => <tr key={q.query} className="border-b align-top dark:border-slate-800">
              <td className="py-2 pr-3 font-medium">{q.query}</td>
              <td className="py-2 pr-3 whitespace-nowrap">{fmtInt(q.impressions)} Impr. · {fmtInt(q.clicks)} Klicks<br/>Ø Pos. {q.position == null ? "–" : fmtNum(q.position)}</td>
              <td className="py-2">{q.reason}<div className="mt-1 text-slate-500">Title/H1-Abdeckung {q.ranked_title_coverage == null ? "nicht geprüft" : Math.round(q.ranked_title_coverage * 100) + "%"} · Text {q.ranked_body_coverage == null ? "nicht geprüft" : Math.round(q.ranked_body_coverage * 100) + "%"}</div></td>
            </tr>)}</tbody>
          </table>
        </div>
        {cluster.category !== "no_action" && site && <div className="mt-4 flex flex-wrap items-center gap-2">
          <Input aria-label={`Ziel-URL für ${cluster.query}`} className="min-w-64 flex-1"
            placeholder="Ziel-URL der Website für manuelle Maßnahme"
            value={targets[cluster.id] ?? cluster.best_existing_url ?? cluster.ranked_url}
            onChange={e => setTargets(p => ({ ...p, [cluster.id]: e.target.value }))} />
          <Button size="sm" loading={save.isPending} onClick={() => {
            const url = targets[cluster.id] ?? cluster.best_existing_url ?? cluster.ranked_url;
            save.mutate({ query: cluster.query, target_url: url, action: cluster.category === "no_action" ? "review" : cluster.category });
          }}>Als Maßnahme erfassen</Button>
        </div>}
      </Card>)}
      <p className="text-xs text-slate-500">{d.method}</p>
    </>}
    {message && <p role="status" className="text-sm">{message} <Link to="/seo-work" className="underline">Maßnahmen ansehen</Link></p>}
  </div>;
}
