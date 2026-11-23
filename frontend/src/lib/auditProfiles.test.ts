import { describe, expect, it } from "vitest";
import { classificationMeta, matchesAuditProfile } from "./auditProfiles";

describe("classification meta", () => {
  it("maps known classes and falls back to heuristic for unknown values", () => {
    expect(classificationMeta("technical_requirement").short).toBe("Technisch");
    expect(classificationMeta("geo_experiment").tone).toBe("purple");
    expect(classificationMeta(undefined).short).toBe("Heuristik");
    expect(classificationMeta("something_new").short).toBe("Heuristik");
  });
});

describe("audit profile filter", () => {
  it("keeps all findings in the default view and only mapped findings in a profile", () => {
    const groups = [
      { id: "noindex", profiles: ["bing", "brave"] },
      { id: "geo_llms_missing", profiles: ["geo"] },
      { id: "thin_content", profiles: [] },
    ];

    expect(groups.filter((group) => matchesAuditProfile(group, "all")).map((group) => group.id))
      .toEqual(["noindex", "geo_llms_missing", "thin_content"]);
    expect(groups.filter((group) => matchesAuditProfile(group, "brave")).map((group) => group.id))
      .toEqual(["noindex"]);
    expect(groups.filter((group) => matchesAuditProfile(group, "geo")).map((group) => group.id))
      .toEqual(["geo_llms_missing"]);
  });
});
