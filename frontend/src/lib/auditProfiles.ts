export type AuditProfile = "all" | "google" | "bing" | "brave" | "geo";

export function matchesAuditProfile(group: { profiles?: readonly string[] }, profile: AuditProfile): boolean {
  return profile === "all" || (group.profiles ?? []).includes(profile);
}
