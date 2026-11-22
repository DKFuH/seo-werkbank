import { describe, expect, it } from "vitest";
import { relativeChange, summarizeAi, summarizeWork } from "../lib/dashboardSummary";

describe("summarizeWork", () => {
  it("counts open items per kind and keeps the API order for next steps", () => {
    const s = summarizeWork([
      { id: 1, kind: "content", status: "draft", title: "A", updated_at: "2026-11-22" },
      { id: 2, kind: "content", status: "published", title: "B", updated_at: "2026-11-21" },
      { id: 3, kind: "review", status: "requested", title: "C", updated_at: "2026-11-20" },
      { id: 4, kind: "competitor", status: "dismissed", title: "D", updated_at: "2026-11-19" },
    ]);
    expect(s).toMatchObject({ total: 4, open: 2, done: 2, byKind: { content: 1, review: 1 } });
    expect(s.next.map((x) => x.id)).toEqual([1, 3]);
  });
});

describe("summarizeAi", () => {
  it("treats www and subdomains as the own site and ignores other hosts", () => {
    const s = summarizeAi([
      { brand_mentioned: true, cited_url: "https://example.de/a", observed_at: "2026-11-01T10:00:00" },
      { brand_mentioned: false, cited_url: "https://blog.example.de/b", observed_at: "2026-11-05T10:00:00" },
      { brand_mentioned: true, cited_url: "https://other.de/", observed_at: "2026-10-01T10:00:00" },
      { brand_mentioned: false, cited_url: "kein link", observed_at: "2026-09-01T10:00:00" },
    ], "https://www.example.de/");
    expect(s).toMatchObject({ samples: 4, mentioned: 2, ownCitations: 2, latest: "2026-11-05T10:00:00", mentionShare: 0.5 });
  });

  it("has no share without samples", () => {
    expect(summarizeAi([], "https://example.de").mentionShare).toBeNull();
  });
});

describe("relativeChange", () => {
  it("returns null when there is nothing to compare with", () => {
    expect(relativeChange(10, 0)).toBeNull();
    expect(relativeChange(10, null)).toBeNull();
    expect(relativeChange(15, 10)).toBeCloseTo(0.5);
  });
});
