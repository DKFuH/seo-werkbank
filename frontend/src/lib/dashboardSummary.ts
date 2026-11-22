/**
 * Pure summaries for the dashboard area cards. They only count what the APIs return;
 * nothing here estimates, extrapolates or fills gaps.
 */

/** Work-item states after which nothing is left to do. Everything else counts as open. */
export const DONE_STATES = new Set(["published", "measured", "received", "verified", "lost", "completed", "actioned", "dismissed"]);

export const WORK_KIND_LABEL: Record<string, string> = {
  content: "Content", review: "Bewertungen", publication: "Veröffentlichungen", local: "Lokal", competitor: "Wettbewerb",
};

export interface WorkItem { id: number; kind: string; status: string; title: string; updated_at: string }

export function summarizeWork(items: WorkItem[]) {
  const open = items.filter((x) => !DONE_STATES.has(x.status));
  const byKind: Record<string, number> = {};
  for (const x of open) byKind[x.kind] = (byKind[x.kind] ?? 0) + 1;
  // The API already sorts by last update, newest first.
  return { total: items.length, open: open.length, done: items.length - open.length, byKind, next: open.slice(0, 3) };
}

export interface AiObservation { brand_mentioned: boolean; cited_url: string | null; observed_at: string }

function bareHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return null;
  }
}

/** Counts manual samples. "Own citation" means the cited URL is on the site's host (www ignored). */
export function summarizeAi(items: AiObservation[], siteUrl: string) {
  const own = bareHost(siteUrl);
  const mentioned = items.filter((x) => x.brand_mentioned).length;
  const ownCitations = items.filter((x) => {
    const h = bareHost(x.cited_url);
    return !!own && !!h && (h === own || h.endsWith("." + own));
  }).length;
  const latest = items.reduce<string | null>((max, x) => (!max || x.observed_at > max ? x.observed_at : max), null);
  return { samples: items.length, mentioned, ownCitations, latest, mentionShare: items.length ? mentioned / items.length : null };
}

/** Relative change, or null when there is no comparable previous value. */
export function relativeChange(now: number | null | undefined, before: number | null | undefined): number | null {
  if (now === null || now === undefined || before === null || before === undefined || before === 0) return null;
  return (now - before) / before;
}
