import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge, Card, EmptyState, ErrorBox, PageHeader, Spinner, Stat, Url } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { DirectoryQualityPanel } from "../components/AuthorityPanels";
import { fmtInt } from "../lib/format";

type Action = { priority: string; title: string; basis: string; type: string };
type LocalPlan = {
  citations: { count: number; missing: Record<string, number>; inconsistent: string[]; duplicates: number };
  review_requests: { total: number; by_status: Record<string, number>; source: string };
  actions: Action[]; limitations: string[];
};
type Publication = {
  id: number; title: string; status: string; source_url: string | null; target_url: string | null;
  evidence_url: string | null; backlink_record: {
    status: string; nofollow: boolean | null; last_checked: string | null; origin: string;
  } | null; interpretation: string;
};
type Publications = { items: Publication[]; method: string };

export default function SeoEvidence() {
  const { site } = useSite();
  const plan = useQuery<LocalPlan>({ queryKey: ["local-action-plan", site?.id],
    queryFn: () => api.get("/sites/" + site!.id + "/local-action-plan"), enabled: !!site });
  const publication = useQuery<Publications>({ queryKey: ["publication-evidence", site?.id],
    queryFn: () => api.get("/sites/" + site!.id + "/publication-evidence"), enabled: !!site });
  return <div className="space-y-4">
    <PageHeader title="Lokales SEO, Bewertungen & Veröffentlichungen" description="Nachvollziehbare Aktionsliste aus eigenen Importdaten und manuellen Vorgängen, nicht aus behaupteten Google- oder Branchenwerten." />
    <Card>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Hier werden ausschließlich <strong>importierte Branchenprofile</strong>, <strong>manuell protokollierte Vorgänge</strong>
        und <strong>vorhandene Backlink-Datensätze</strong> verglichen. Es besteht keine Verbindung zur Google Business Profile API
        und es werden keine externen Profile live geprüft.
      </p>
      <div className="mt-3 flex flex-wrap gap-3 text-sm">
        <Link className="font-medium text-brand-700 underline dark:text-brand-300" to="/local">Branchenprofile importieren</Link>
        <Link className="font-medium text-brand-700 underline dark:text-brand-300" to="/seo-work">Vorgänge erfassen</Link>
        <Link className="font-medium text-brand-700 underline dark:text-brand-300" to="/backlinks">Backlinks prüfen</Link>
      </div>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {plan.isLoading && <Card><Spinner /></Card>}
    {plan.error && <ErrorBox error={plan.error} onRetry={() => plan.refetch()} />}
    {plan.data && <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <Stat label="Importierte Verzeichniseinträge" value={fmtInt(plan.data.citations.count)} />
        <Stat label="NAP-Felder mit Abweichungen" value={fmtInt(plan.data.citations.inconsistent.length)} />
        <Stat label="Dokumentierte Bewertungsanfragen" value={fmtInt(plan.data.review_requests.total)} />
      </div>
      <Card title="Prüfbare Maßnahmen">
        <ul className="space-y-3">
          {plan.data.actions.map((item) => <li key={item.type} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <Badge tone={item.priority === "high" ? "red" : item.priority === "medium" ? "amber" : "gray"}>
                {item.priority === "manual" ? "manuell" : item.priority === "high" ? "hoch" : "mittel"}
              </Badge>
              <span className="text-sm font-medium">{item.title}</span>
            </div>
            <p className="mt-1 text-xs text-slate-500">{item.basis}</p>
          </li>)}
        </ul>
      </Card>
      <Card title="Bewertungsprozess">
        <p className="text-sm">Erfasste Vorgänge: {fmtInt(plan.data.review_requests.total)}.
          {" "}Statusverteilung: {Object.entries(plan.data.review_requests.by_status).map(([status, n]) => status + ": " + fmtInt(n)).join("; ") || "keine"}.
        </p>
        <p className="mt-2 text-sm text-slate-500">Einladungen sind nur dokumentiert, nicht automatisch versandt.
          Alle Kunden gleich behandeln, keine bezahlten oder selektiv angefragten positiven Bewertungen.</p>
      </Card>
      <Card title="Datenlücken">
        <ul className="list-disc space-y-1 pl-4 text-sm text-slate-500">
          {plan.data.limitations.map((reason) => <li key={reason}>{reason}</li>)}
        </ul>
      </Card>
    </>}
    {publication.isLoading && <Card><Spinner label="Publikationsnachweise werden abgeglichen…" /></Card>}
    {publication.error && <ErrorBox error={publication.error} onRetry={() => publication.refetch()} />}
    {publication.data && <Card title="Publikationen und Backlink-Nachweise">
      <p className="mb-3 text-xs text-slate-500">{publication.data.method}</p>
      {!publication.data.items.length && <EmptyState title="Keine Publikationsvorgänge dokumentiert" description="Im Bereich SEO-Maßnahmen eine Veröffentlichung anlegen und die Quell-URL eintragen." />}
      <ul className="space-y-3">
        {publication.data.items.map((item) => <li key={item.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="text-sm">{item.title}</strong>
            <Badge>{item.status}</Badge>
            {item.backlink_record && <Badge tone={item.backlink_record.status === "live" ? "green" : "amber"}>
              Backlink-Datensatz: {item.backlink_record.status}
            </Badge>}
          </div>
          {item.source_url && <div className="mt-2 text-xs">Quelle: <Url href={item.source_url} /></div>}
          {item.target_url && <div className="mt-1 text-xs">Ziel: <Url href={item.target_url} /></div>}
          {item.evidence_url && <div className="mt-1 text-xs">Nachweis: <Url href={item.evidence_url} /></div>}
          <p className="mt-2 text-xs text-slate-500">{item.interpretation}</p>
          {item.backlink_record && <p className="mt-1 text-xs text-slate-500">
            Nofollow: {item.backlink_record.nofollow === null ? "unbekannt" : item.backlink_record.nofollow ? "ja" : "nein"}
            {" · "}Zuletzt geprüft: {item.backlink_record.last_checked ?? "nie"}
          </p>}
        </li>)}
      </ul>
    </Card>}
    {site && <DirectoryQualityPanel siteId={site.id} />}
  </div>;
}
