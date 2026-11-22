import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Button, Card, EmptyState, ErrorBox, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type CaseStudy = { id: number; title: string; target_url: string; has_evidence: boolean;
  verified: false; draft_preview: string };
type QuestionGroup = { audience: string; questions: { id: number; question: string; context: string;
  suggested_url: string | null }[] };
type Claim = { id: number; subject: string; claim: string; source_url: string;
  expected_statement: string | null; lexically_matching: boolean | null; source_verified: false };
type Experiment = { id: number; title: string; hypothesis: string; metric: string; unit: string;
  start_date: string; end_date: string | null; baseline: number | null; followup: number | null;
  observed_difference: number | null; causal_effect_established: false };
type Result = { cases: CaseStudy[]; buyer_questions: QuestionGroup[]; brand_claims: Claim[];
  experiments: Experiment[]; method: string };

export default function ContentStudio() {
  const { site } = useSite();
  const qc = useQueryClient();
  const root = "/sites/" + site?.id;
  const q = useQuery<Result>({ queryKey: ["content-studio", site?.id],
    queryFn: () => api.get(root + "/content-studio"), enabled: !!site });
  const draft = useMutation({ mutationFn: (id: number) => api.post(root + "/content-studio/case-studies/" + id + "/draft", {}),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["content-studio", site?.id] }) });
  return <div className="space-y-4">
    <PageHeader title="Evidence-led Content Studio" description="Fallstudien aus realen Projektdaten, Käuferfragen, Markenabgleich und Marketing-Experimente – ohne erfundene Erfolgsgeschichten." />
    <Card>
      <p className="text-sm text-slate-600 dark:text-slate-300">Erfasse die Originalinformationen im <Link to="/research" className="underline">SEO-Research-Workspace</Link>.
        Eine Fallstudie wird nur als redaktioneller Entwurf mit den eingegebenen Fakten erzeugt.
        Veröffentlichung und Freigabe bleiben im <Link to="/content-proposals" className="underline">Content-Entwurfsworkflow</Link> getrennt.</p>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {q.isLoading && <Card><Spinner /></Card>}
    {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
    <Card title="Fallstudien und prüfbare Projektgeschichten">
      {!q.data?.cases.length && <EmptyState title="Keine dokumentierten Projektfallstudien" />}
      {q.data?.cases.map((c) => <div key={c.id} className="mb-4 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <strong className="text-sm">{c.title}</strong>
        <p className="mt-1 break-all text-xs text-slate-500">Ziel: {c.target_url} · {c.has_evidence ? "Nachweis angegeben, ungeprüft" : "Nachweis fehlt"}</p>
        <pre className="my-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-slate-700 dark:text-slate-300">{c.draft_preview}</pre>
        <Button size="sm" disabled={draft.isPending}
          onClick={() => { if (window.confirm("Aus den erfassten Aussagen einen rein internen Content-Entwurf erzeugen?")) draft.mutate(c.id); }}>
          Entwurf zur Freigabe erstellen
        </Button>
      </div>)}
      {draft.error && <ErrorBox error={draft.error} />}
      {draft.isSuccess && <p className="text-xs text-slate-500">Ein Entwurf wurde angelegt. Die Veröffentlichung erfolgt nicht automatisch.</p>}
    </Card>
    <Card title="Echte Käuferfragen für Content-Briefings">
      {!q.data?.buyer_questions.length && <EmptyState title="Noch keine Käuferfragen dokumentiert" />}
      {q.data?.buyer_questions.map((group) => <div className="mb-3 text-sm" key={group.audience}>
        <strong>{group.audience}</strong>
        {group.questions.map((question) => <p key={question.id} className="mt-1 text-xs">
          {question.question} · {question.context}{question.suggested_url ? " · " + question.suggested_url : ""}
        </p>)}
      </div>)}
      <p className="text-xs text-slate-500">Keine personenbezogenen Kundendaten eingeben. Eine Kundenfrage ist kein Suchvolumenbeleg.</p>
    </Card>
    <Card title="Brand-Consistency-Check">
      {!q.data?.brand_claims.length && <EmptyState title="Noch keine Markenaussagen zum Abgleich" />}
      {q.data?.brand_claims.map((b) => <div key={b.id} className="mb-2 text-sm">
        <strong>{b.subject}</strong> · {b.claim}
        <p className="break-all text-xs text-slate-500">Quelle (nicht verifiziert): {b.source_url}</p>
        <p className="text-xs text-slate-500">{b.lexically_matching === null ? "Kein erwarteter Wortlaut erfasst" :
          b.lexically_matching ? "Wortlaut stimmt überein" : "Wortlaut weicht ab"} · keine Wahrheitsprüfung</p>
      </div>)}
    </Card>
    <Card title="Marketing-Experiment-Journal">
      {!q.data?.experiments.length && <EmptyState title="Noch keine Experimente dokumentiert" />}
      {q.data?.experiments.map((e) => <div key={e.id} className="mb-3 text-sm">
        <strong>{e.title}</strong> · {e.start_date}
        <p className="text-xs">{e.hypothesis}</p>
        <p className="text-xs text-slate-500">{e.metric} ({e.unit}): {e.baseline ?? "?"} → {e.followup ?? "?"}
          {" · "}beobachtete Differenz: {e.observed_difference ?? "nicht messbar"}</p>
        <p className="text-xs text-slate-500">Keine nachgewiesene Kausalwirkung; Testdesign und Vergleichbarkeit separat prüfen.</p>
      </div>)}
    </Card>
    <p className="text-xs text-slate-500">{q.data?.method}</p>
  </div>;
}
