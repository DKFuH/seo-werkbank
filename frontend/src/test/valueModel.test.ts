import { describe, expect, it } from "vitest";
import { estimateBusinessValue, parsePercent, parseScenario, sortByValue } from "../lib/valueModel";

describe("Business-Opportunity-Szenario", () => {
  it("keine Fantasiewerte ohne alle Nutzereingaben", () => {
    expect(parseScenario({ leadPercent: "", closePercent: "40", contributionEuro: "1000" })).toBeNull();
    expect(parseScenario({ leadPercent: "5", closePercent: "40", contributionEuro: "" })).toBeNull();
    expect(estimateBusinessValue(200, "50", null)).toBeNull();
  });

  it("akzeptiert deutsche Dezimalzahlen, verhindert ungültige Eingaben", () => {
    expect(parsePercent("2,5")).toBe(2.5);
    expect(parsePercent("-1")).toBeNull();
    expect(parsePercent("105")).toBeNull();
    expect(parsePercent("nicht bekannt")).toBeNull();
    expect(parseScenario({ leadPercent: "2,5", closePercent: "50", contributionEuro: "2.000" })).toEqual({
      leadRate: 0.025, closeRate: 0.5, contribution: 2000,
    });
  });

  it("rechnet Leads, Aufträge und Deckungsbeitrag als Szenario", () => {
    const scenario = parseScenario({ leadPercent: "5", closePercent: "40", contributionEuro: "2.000,50" });
    expect(scenario?.contribution).toBe(2000.5);
    const result = estimateBusinessValue(200, "50", scenario);
    expect(result?.qualifiedClicks).toBe(100);
    expect(result?.expectedLeads).toBe(5);
    expect(result?.expectedOrders).toBe(2);
    expect(result?.contributionEuro).toBe(4001);
  });

  it("behandelt 0% Fit als gültiges Null-Szenario und ungeprüfte Seiten separat", () => {
    const s = parseScenario({ leadPercent: "2", closePercent: "30", contributionEuro: "1000" });
    expect(estimateBusinessValue(100, "0", s)?.contributionEuro).toBe(0);
    expect(estimateBusinessValue(100, undefined, s)).toBeNull();
    const pages = [
      { url: "a", estimated_extra_clicks: 100 },
      { url: "b", estimated_extra_clicks: 20 },
      { url: "c", estimated_extra_clicks: 1000 },
    ];
    expect(sortByValue(pages, { a: "10", b: "100" }, s).map((p) => p.url)).toEqual(["b", "a", "c"]);
    expect(pages[0].url).toBe("a");
  });
});
