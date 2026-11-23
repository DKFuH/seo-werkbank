import { ExternalLink } from "lucide-react";
import { classificationMeta, PROFILE_LABELS, PROFILE_SHORT_LABELS } from "../lib/auditProfiles";
import { Badge, Card } from "./ui";

type EngineEvidence = { status: "related_guidance" | "not_evaluated" | string; documentation: string | null };

export type RuleProvenance = {
  classification?: string;
  classification_label?: string;
  google_documentation?: string | null;
  search_engines?: Record<string, EngineEvidence>;
  profiles?: string[];
};

/** Compact provenance badge: technical issue, Google recommendation, heuristic or GEO hypothesis. */
export function ClassificationBadge({ rule }: { rule: RuleProvenance }) {
  if (!rule.classification) return null;
  const meta = classificationMeta(rule.classification);
  return <Badge tone={meta.tone} title={rule.classification_label}>{meta.short}</Badge>;
}

/** Profile chips (Google/Bing/Brave/GEO) a rule counts towards. */
export function ProfileChips({ profiles }: { profiles?: string[] }) {
  if (!profiles?.length) return <span className="text-xs text-slate-400" title="Fließt in keinen Suchmaschinen-Score ein">–</span>;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {profiles.map((p) => <Badge key={p}>{PROFILE_SHORT_LABELS[p as keyof typeof PROFILE_SHORT_LABELS] ?? p}</Badge>)}
    </span>
  );
}

function DocLink({ href }: { href: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline dark:text-brand-300">
      Dokumentation <ExternalLink className="h-3 w-3" />
    </a>
  );
}

/** Detail card for the issue page: where the rule comes from and how each engine is covered. */
export function ProvenanceCard({ rule }: { rule: RuleProvenance }) {
  if (!rule.classification) return null;
  const profiles = new Set(rule.profiles ?? []);
  const google = profiles.has("google");
  const engines: { id: "google" | "bing" | "brave"; status: string; documentation: string | null }[] = [
    { id: "google", status: google ? "related_guidance" : "not_evaluated", documentation: google ? rule.google_documentation ?? null : null },
    ...(["bing", "brave"] as const).map((id) => ({ id, status: rule.search_engines?.[id]?.status ?? "not_evaluated", documentation: rule.search_engines?.[id]?.documentation ?? null })),
  ];
  return (
    <Card title="Einordnung" description="Woher die Regel stammt und für welche Suchmaschine sie dokumentiert ist. Ändert den Schweregrad nicht.">
      <div className="space-y-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <ClassificationBadge rule={rule} />
          <span className="text-slate-700 dark:text-slate-300">{rule.classification_label}</span>
        </div>
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {engines.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <span className="font-medium text-slate-800 dark:text-slate-200">{PROFILE_LABELS[e.id]}</span>
              <span className="inline-flex items-center gap-2">
                {e.status === "related_guidance"
                  ? <Badge tone="green">dokumentiert · im {PROFILE_SHORT_LABELS[e.id]}-Score</Badge>
                  : <Badge>nicht bewertet</Badge>}
                {e.documentation && <DocLink href={e.documentation} />}
              </span>
            </li>
          ))}
          {profiles.has("geo") && (
            <li className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <span className="font-medium text-slate-800 dark:text-slate-200">GEO</span>
              <Badge tone="purple">Hypothese · im GEO-Score</Badge>
            </li>
          )}
        </ul>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          „Nicht bewertet“ heißt: keine suchmaschinenspezifische Quelle hinterlegt, nicht dass die Regel dort irrelevant ist.
          Dokumentationslinks sind Einstiegspunkte, kein Beleg für konkrete Grenzwerte.
        </p>
      </div>
    </Card>
  );
}
