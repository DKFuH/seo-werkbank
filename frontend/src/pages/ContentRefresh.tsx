import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, EmptyState, ErrorBox, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum, fmtPct, shortUrl } from "../lib/format";

type QueryOpportunity = {
  query: string; clicks: number; impressions: number; position: number; ctr: number;
  type: "striking_distance" | "low_ctr"; estimated_extra_clicks: number;
  review_terms: string[]; mentioned_in_body: boolean | null; editorial_action: string;
};
type RefreshPage = {
  url: string; title: string | null; crawl_found: boolean; impressions: number; clicks: number;
  estimated_extra_clicks: number; queries: QueryOpportunity[];
};
type RefreshResult = {
  has_data: boolean; reason?: string; source?: "api" | "csv"; pages: RefreshPage[];
  start_date?: string | null; end_date?: string | null; unpaired_rows?: number;
  truncated?: boolean; total_pages: number; notes?: string[]; method?: string;
};

export default function ContentRefresh() {
  const { site } = useSite();
  const [days, setDays] = useState(28);
  const [copied, setCopied] = useState("");
  const result = useQuery<RefreshResult>({
    queryKey: ["content-refresh", site?.id, days],
    queryFn: () => api.get(`/sites/${site!.id}/content-refresh`, { days }),
    enabled: !!site?.id,
  });
  const d = result.data;
  const copyBrief = async (page: RefreshPage) => {
    const brief = ["Content-Refresh-Briefing (manuell prüfen)", `URL: ${page.url}`,
      ...page.queries.map((q) => ["", `GSC-Suchanfrage: ${q.query}`,
        `Impressionen: ${q.impressions}; Klicks: ${q.clicks}; Ø Position: ${q.position}`,
        `Hinweis: ${q.editorial_action}`,
        q.review_terms.length ? `Begriffe für Überschriftenprüfung: ${q.review_terms.join(", ")}` : ""].filter(Boolean).join("\n")),
      "", "Keine automatisch erstellten Artikeltexte. Prüfe Suchintention, Fakten und bestehende Abschnitte vor Änderungen."].join("\n");
    try {
      await navigator.clipboard.writeText(brief);
      setCopied(page.url);
    } catch {
      setCopied("");
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader title="Content-Refresh" description="Konkrete Seiten aus gemessenen GSC-Suchanfrage-URL-Paaren auswählen und redaktionelle Optimierungen prüfen." />
      <Card title="Auswertungszeitraum">
        <div className="flex flex-wrap items-center gap-3">
          <Select aria-label="GSC-Zeitraum" value={days} onChange={(e) => setDays(Number(e.target.value))} className="max-w-48">
            {[7, 14, 28, 56, 90, 180].map((n) => <option key={n} value={n}>{n} Tage</option>)}
          </Select>
          <span className="text-sm text-slate-500 dark:text-slate-400">{d?.end_date ? `Bis ${d.end_date}` : "Ohne Datumsbezug oder keine Daten"}</span>
        </div>
      </Card>
      {!site && <Card><EmptyState title="Website auswählen" description="Für Content-Refresh ist eine Website mit GSC-Daten erforderlich." /></Card>}
      {result.isLoading && <Card><Spinner label="GSC-Query-URL-Paare werden ausgewertet…" /></Card>}
      {result.error && <ErrorBox error={result.error} onRetry={() => result.refetch()} />}
      {d && !d.has_data && <Card><EmptyState title="Keine zugeordneten GSC-Daten" description={d.reason ?? "GSC-Daten mit Suchanfrage UND URL importieren oder synchronisieren."} />
        <p className="mt-3 text-sm"><Link to="/search-console" className="font-medium text-brand-700 underline dark:text-brand-300">Zur Search Console</Link></p>
      </Card>}
      {d?.has_data && <>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <Stat label="Seiten mit Chancen" value={fmtInt(d.total_pages)} />
          <Stat label="GSC-Quelle" value={d.source === "api" ? "API" : "CSV"} />
          <Stat label="Query-Zeilen ohne URL-Bezug" value={fmtInt(d.unpaired_rows)} />
        </div>
        <Card>
          <p className="text-sm text-slate-600 dark:text-slate-300">Zusatzklicks sind hypothetische CTR-Szenarien, keine Prognosen. Worttreffer im Crawl sind keine semantische Prüfung. Vorschläge ändern keine Inhalte und veröffentlichen nichts.</p>
          {d.notes?.map((note) => <p key={note} className="mt-2 text-sm text-amber-700 dark:text-amber-300">{note}</p>)}
          {d.truncated && <p className="mt-2 text-sm font-medium">Die Analyse ist auf die 10.000 meistgesehenen Query-URL-Paare begrenzt.</p>}
        </Card>
        {d.pages.length === 0 && <Card><EmptyState title="Keine passende Chance gefunden" description="In diesem Zeitraum liegen keine Query-URL-Paare mit mindestens 20 Impressionen und auffälliger Rankingposition oder CTR vor." /></Card>}
        {d.pages.map((page) => <Card key={page.url} title={page.title || shortUrl(page.url, site?.url)}
          description={page.url} actions={<Button onClick={() => void copyBrief(page)}>{copied === page.url ? "Briefing kopiert" : "Briefing kopieren"}</Button>}>
          <div className="mb-3 flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-300">
            <span>{fmtInt(page.impressions)} Impr. (aus Chancen)</span>
            <span>{fmtInt(page.clicks)} Klicks</span>
            <span>+{fmtInt(page.estimated_extra_clicks)} Klicks (Schätzung)</span>
            {!page.crawl_found && <Badge tone="amber">Nicht im letzten Crawl gefunden</Badge>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700"><tr>
                <th className="py-2 pr-3">Suchanfrage</th><th className="py-2 pr-3">GSC-Daten</th><th className="py-2">Redaktionelle Prüfung</th>
              </tr></thead>
              <tbody>{page.queries.map((q) => <tr key={q.query} className="border-b border-slate-100 align-top dark:border-slate-800">
                <td className="py-2 pr-3 font-medium">{q.query}<div className="mt-1"><Badge tone={q.type === "low_ctr" ? "purple" : "blue"}>{q.type === "low_ctr" ? "CTR prüfen" : "Position 4–20"}</Badge></div></td>
                <td className="py-2 pr-3 whitespace-nowrap">{fmtInt(q.impressions)} Impr. · {fmtInt(q.clicks)} Klicks<div className="text-xs text-slate-500">Pos. {fmtNum(q.position)} · CTR {fmtPct(q.ctr)}</div></td>
                <td className="py-2">{q.editorial_action}
                  {q.review_terms.length > 0 && <div className="mt-1 text-xs text-slate-500">Überschriften-Wortabgleich: {q.review_terms.join(", ")}</div>}
                </td>
              </tr>)}</tbody>
            </table>
          </div>
        </Card>)}
        <p className="text-xs text-slate-500">{d.method}</p>
      </>}
    </div>
  );
}
