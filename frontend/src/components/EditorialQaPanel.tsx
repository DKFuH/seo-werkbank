import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Button, Card, ErrorBox } from "./ui";

type Finding = { kind: string; severity: string; title: string; examples: string[]; total: number; review: string };
type Result = { findings: Finding[]; finding_count: number; needs_review: boolean; method: string };
export default function EditorialQaPanel({ siteId, itemId, original, proposed, rationale }: {
  siteId: number; itemId: number; original: string; proposed: string; rationale: string;
}) {
  const check = useMutation<Result>({
    mutationFn: () => api.post(`/sites/${siteId}/seo-work/${itemId}/editorial-qa`,
      { original_text: original, proposed_text: proposed, rationale }),
  });
  return <Card title="Redaktionelle Qualitätssicherung" description="Prüft auffällige neue Behauptungen vor einer Freigabe. Keine automatische Faktenprüfung.">
    <Button size="sm" disabled={!proposed.trim()} loading={check.isPending} onClick={() => check.mutate()}>
      Aktuellen Entwurf prüfen
    </Button>
    {check.error && <ErrorBox error={check.error} />}
    {check.data && <div className="mt-3 space-y-2 text-sm">
      <p><strong>{check.data.finding_count} Hinweiskategorien</strong> erkannt. Auch null Hinweise belegen keine inhaltliche Richtigkeit.</p>
      {check.data.findings.map(f => <div key={f.kind} className="border-b py-2 dark:border-slate-800">
        <strong>{f.title}</strong> · {f.total} neue Angaben · {f.severity}
        <p className="break-words text-xs">{f.examples.join("; ")}</p><p className="text-xs text-slate-500">{f.review}</p>
      </div>)}
      <p className="text-xs text-slate-500">{check.data.method}</p>
    </div>}
  </Card>;
}
