import { useQuery } from "@tanstack/react-query";
import { Card, EmptyState, ErrorBox, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Evidence = { items: { page_url: string; source_links_missing: number;
  claims: { id: number; claim: string; evidence_url: string | null; verified: boolean }[] }[]; method: string };
type Cro = { crawl_id: number | null; items: { url: string; title: string | null; h1_present: boolean;
  meta_description_present: boolean; text_contains_possible_cta: boolean; not_examined: string[];
  manual_reviews: { criterion: string; result: string }[] }[]; method: string };
type Comparison = { items: { id: number; subject_a: string; subject_b: string; criterion: string;
  source_url: string | null; needs_source: boolean; verified: boolean }[]; method: string };
type Asset = { items: { id: number; title: string; purpose: string; audience: string; format: string;
  missing_specifications: string[]; review_checklist: string[] }[]; method: string };

export default function ResearchQuality() {
  const { site } = useSite();
  const root = "/sites/" + site?.id + "/research";
  const evidence = useQuery<Evidence>({ queryKey: ["quality-evidence", site?.id],
    queryFn: () => api.get(root + "/content-evidence"), enabled: !!site });
  const cro = useQuery<Cro>({ queryKey: ["quality-cro", site?.id],
    queryFn: () => api.get(root + "/cro-audit"), enabled: !!site });
  const comparisons = useQuery<Comparison>({ queryKey: ["quality-comparison", site?.id],
    queryFn: () => api.get(root + "/comparison-review"), enabled: !!site });
  const assets = useQuery<Asset>({ queryKey: ["quality-assets", site?.id],
    queryFn: () => api.get(root + "/asset-briefs"), enabled: !!site });
  const queries: { isLoading: boolean; error: Error | null }[] = [evidence, cro, comparisons, assets];
  return <div className="space-y-4">
    <PageHeader title="Content-Qualität & Conversion-Checks" description="Nachweise, Textsignale, Vergleiche und Nutzwert-Assets prüfen – ohne unbestätigte Google-Scores oder CRO-Erfolgsgarantien." />
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {queries.some((q) => q.isLoading) && <Card><Spinner /></Card>}
    {queries.map((q, i) => q.error ? <ErrorBox key={i} error={q.error} /> : null)}
    <Card title="Eigene Aussagen und ihre Nachweise">
      {evidence.data?.items.length === 0 && <EmptyState title="Keine Inhaltsnachweise erfasst" />}
      {evidence.data?.items.map((item) => <div className="mb-3 text-sm" key={item.page_url}>
        <strong className="break-all">{item.page_url}</strong>
        <p className="text-xs text-slate-500">{item.source_links_missing} Aussagen ohne Quellenlink</p>
        {item.claims.map((c) => <p key={c.id}>„{c.claim}“ – {c.evidence_url ? "Quelle angegeben, ungeprüft" : "Quelle fehlt"}</p>)}
      </div>)}
      <p className="text-xs text-slate-500">{evidence.data?.method}</p>
    </Card>
    <Card title="Landingpage-Signale (Crawler)">
      {cro.data?.items.length === 0 && <EmptyState title="Keine gecrawlten HTML-Seiten" />}
      <p className="mb-3 text-xs text-slate-500">Technische Worttreffer sind keine visuelle UX-Prüfung oder Conversion-Messung.</p>
      {cro.data?.items.slice(0, 50).map((p) => <div key={p.url} className="mb-3 border-b border-slate-100 pb-2 text-sm dark:border-slate-800">
        <strong className="break-all">{p.title ?? p.url}</strong>
        <p className="text-xs">H1: {p.h1_present ? "vorhanden" : "fehlt"} · Meta: {p.meta_description_present ? "vorhanden" : "fehlt"}
          {" · "}CTA-Wort im Text: {p.text_contains_possible_cta ? "gefunden" : "nicht gefunden"}</p>
        {p.manual_reviews.map((x, i) => <p className="text-xs text-slate-500" key={i}>{x.criterion}: {x.result}</p>)}
      </div>)}
      <p className="text-xs text-slate-500">Nicht automatisch geprüft: visueller Einstieg, Mobilansicht, echte Conversion, Vertrauenswürdigkeit und Formulare.</p>
    </Card>
    <Card title="Vergleichsdaten">
      {comparisons.data?.items.length === 0 && <EmptyState title="Keine Produkt- oder Alternativenvergleiche erfasst" />}
      {comparisons.data?.items.map((c) => <p className="mb-2 text-sm" key={c.id}>
        {c.subject_a} / {c.subject_b} – {c.criterion}: {c.needs_source ? "Beleg fehlt" : "Quelle erfasst (nicht verifiziert)"}
      </p>)}
    </Card>
    <Card title="Linkable-Assets: Briefing und Qualitätssicherung">
      {assets.data?.items.length === 0 && <EmptyState title="Noch keine Asset-Briefings" />}
      {assets.data?.items.map((a) => <div className="mb-3 text-sm" key={a.id}>
        <strong>{a.title}</strong> · {a.format}
        <p className="text-xs text-slate-500">Ziel: {a.purpose} · Zielgruppe: {a.audience}</p>
        <p className="text-xs">{a.missing_specifications.length ? "Offene Angaben: " + a.missing_specifications.join(", ")
          : "Pflichtangaben für die Planung vorhanden"}</p>
        <p className="text-xs text-slate-500">QA: {a.review_checklist.join(" · ")}</p>
      </div>)}
      <p className="text-xs text-slate-500">{assets.data?.method}</p>
    </Card>
    <p className="text-xs text-slate-500">Einträge werden im SEO-Research-Workspace angelegt. Diese Ansicht prüft nur, was aus vorhandenen Daten ableitbar ist.</p>
  </div>;
}
