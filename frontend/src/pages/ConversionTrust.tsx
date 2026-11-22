import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card, EmptyState, ErrorBox, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type FunnelStep = { id: number; stage: string; action: string; action_url: string | null;
  friction: string | null; form_fields: string | null; evidence_url: string | null };
type TrustProof = { id: number; claim: string; proof_type: string | null; proof_url: string | null;
  genuineness_verified: false };
type Review = { url: string; title: string | null; crawl_found: boolean; cta_lexical_hint: boolean | null;
  missing_stages: string[]; steps: FunnelStep[]; proofs: TrustProof[]; proofs_without_source: number;
  requires_manual_review: string[] };
type Profile = { id: number; brand_name: string; positioning: string; offer: string;
  evidence_url: string | null; source_recorded: boolean; verified: false };
type Result = { crawl_id: number | null; pages: Review[]; brand_profiles: Profile[];
  sources: { funnel_steps: number; trust_proofs: number; brand_profiles: number }; method: string };

export default function ConversionTrust() {
  const { site } = useSite();
  const q = useQuery<Result>({
    queryKey: ["conversion-trust", site?.id],
    queryFn: () => api.get("/sites/" + site!.id + "/conversion-trust"),
    enabled: !!site,
  });
  return <div className="space-y-4">
    <PageHeader title="Conversion & Trust Intelligence" description="Reale Funnel-Schritte und überprüfbare Vertrauensbelege dokumentieren – nicht nur Keywords oder technische SEO." />
    <Card>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Erfasse einen <Link className="underline" to="/research">Conversion-Funnel-Schritt, Vertrauensnachweis oder Markenpositionierung</Link> im Research-Workspace.
        Diese Ansicht gleicht Einträge mit dem letzten Crawl ab. Linkangaben und Claims werden nicht automatisch verifiziert.
        Eine Premiumwirkung oder Conversion-Steigerung lässt sich daraus nicht ableiten.
      </p>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {q.isLoading && <Card><Spinner /></Card>}
    {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
    {q.data && <>
      <Card title="Erfasste Belege">
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div>Funnel-Schritte: <strong>{q.data.sources.funnel_steps}</strong></div>
          <div>Vertrauensbelege: <strong>{q.data.sources.trust_proofs}</strong></div>
          <div>Markenprofile: <strong>{q.data.sources.brand_profiles}</strong></div>
        </div>
      </Card>
      <Card title="Positionierung & Nachweise">
        {!q.data.brand_profiles.length && <EmptyState title="Noch kein Markenprofil erfasst" />}
        {q.data.brand_profiles.map((p) => <div key={p.id} className="mb-3 text-sm">
          <strong>{p.brand_name}</strong> · {p.positioning}
          <p className="text-xs text-slate-500">Leistungsversprechen: {p.offer}</p>
          <p className="text-xs text-slate-500">{p.source_recorded ? "Quelle erfasst – nicht verifiziert" : "Quelle fehlt"}</p>
        </div>)}
      </Card>
      {!q.data.pages.length && <Card><EmptyState title="Keine Funnel- oder Vertrauenseinträge" /></Card>}
      {q.data.pages.map((p) => <Card key={p.url} title={p.title || p.url} description={p.url}>
        <p className="text-sm">Letzter Crawl: {p.crawl_found ? "Seite gefunden" : "Seite nicht gefunden"}
          {" · "}CTA-Wort im Text: {p.cta_lexical_hint === null ? "unbekannt" : p.cta_lexical_hint ? "Treffer" : "kein Treffer"}</p>
        <p className="mt-2 text-xs text-slate-500">Fehlende dokumentierte Phasen: {p.missing_stages.join(", ") || "keine"}
          {" · "}Nachweise ohne URL: {p.proofs_without_source}</p>
        <div className="mt-2 space-y-1">{p.steps.map((s) => <p key={s.id} className="text-sm">
          {s.stage}: {s.action}{s.friction ? " · Hürde: " + s.friction : ""}
        </p>)}</div>
        {p.proofs.map((e) => <p key={e.id} className="mt-1 text-xs">
          Behauptung: {e.claim} – {e.proof_url ? "Beleg angegeben, ungeprüft" : "Beleg fehlt"}
        </p>)}
        <p className="mt-2 text-xs text-slate-500">Weiter manuell prüfen: {p.requires_manual_review.join(" · ")}</p>
      </Card>)}
      <p className="text-xs text-slate-500">{q.data.method}</p>
    </>}
  </div>;
}
