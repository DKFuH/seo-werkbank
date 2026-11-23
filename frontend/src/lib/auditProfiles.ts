export type AuditProfile = "all" | "google" | "bing" | "brave" | "geo";

export const PROFILE_LABELS: Record<Exclude<AuditProfile, "all">, string> = {
  google: "Google",
  bing: "Microsoft Bing",
  brave: "Brave Search",
  geo: "GEO",
};

export const PROFILE_SHORT_LABELS: Record<Exclude<AuditProfile, "all">, string> = {
  google: "Google",
  bing: "Bing",
  brave: "Brave",
  geo: "GEO",
};

export type RuleClassification = "technical_requirement" | "google_recommendation" | "seo_heuristic" | "geo_experiment";

/** Short label + badge tone per provenance class. The long label comes from the API. */
export const CLASSIFICATION_META: Record<RuleClassification, { short: string; tone: string }> = {
  technical_requirement: { short: "Technisch", tone: "red" },
  google_recommendation: { short: "Google-Empfehlung", tone: "blue" },
  seo_heuristic: { short: "Heuristik", tone: "gray" },
  geo_experiment: { short: "GEO-Hypothese", tone: "purple" },
};

export function classificationMeta(classification: string | undefined) {
  return CLASSIFICATION_META[classification as RuleClassification] ?? CLASSIFICATION_META.seo_heuristic;
}

export function matchesAuditProfile(group: { profiles?: readonly string[] }, profile: AuditProfile): boolean {
  return profile === "all" || (group.profiles ?? []).includes(profile);
}
