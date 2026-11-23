import { ExternalLink } from "lucide-react";
import { classificationMeta, PROFILE_LABELS, PROFILE_SHORT_LABELS } from "../lib/auditProfiles";
import { Badge, Card } from "./ui";

type EngineEvidence = {
  status: "related_guidance" | "not_evaluated" | string;
  documentation: string | null;
  evidence?: "quoted" | "topic" | null;
  section?: string | null;
  quote?: string | null;
  source_status?: string | null;
};

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
  const engines: ({ id: "google" | "bing" | "brave" } & EngineEvidence)[] = [
    { id: "google", status: google ? "related_guidance" : "not_evaluated", documentation: google ? rule.google_documentation ?? null : null },
    ...(["bing", "brave"] as const).map((id) => ({
      id, status: rule.search_engines?.[id]?.status ?? "not_evaluated", documentation: rule.search_engines?.[id]?.documentation ?? null,
      evidence: rule.search_engines?.[id]?.evidence, section: rule.search_engines?.[id]?.section,
      quote: rule.search_engines?.[id]?.quote, source_status: rule.search_engines?.[id]?.source_status,
    })),
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
            <li key={e.id} className="py-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-800 dark:text-slate-200">{PROFILE_LABELS[e.id]}</span>
                <span className="inline-flex items-center gap-2">
                  {e.status === "related_guidance"
                    ? <Badge tone={e.evidence === "topic" ? "amber" : "green"}
                        title={e.evidence === "topic" ? "Die Leitlinie behandelt das Themenfeld, enthält aber keinen Satz zu genau dieser Prüfung." : "Ein Satz der Leitlinie beschreibt genau diese Prüfung."}>
                        {e.evidence === "topic" ? "Themenbezug" : "Zitat"} · im {PROFILE_SHORT_LABELS[e.id]}-Score
                      </Badge>
                    : <Badge>nicht bewertet</Badge>}
                  {e.documentation && <DocLink href={e.documentation} />}
                </span>
              </div>
              {e.section && (
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Fundstelle: {e.section}
                  {e.quote && <blockquote className="mt-0.5 border-l-2 border-slate-300 pl-2 italic dark:border-slate-700">„{e.quote}“</blockquote>}
                  {e.source_status && <span className="block">Quelle: {e.source_status}</span>}
                </p>
              )}
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
