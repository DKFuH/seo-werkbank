/** Transparent, explicitly user-supplied business scenario — never actual conversions. */
export type Rates = { leadPercent: string; closePercent: string; contributionEuro: string };
export type BusinessScenario = { leadRate: number; closeRate: number; contribution: number };
export type ValueEstimate = {
  qualifiedClicks: number; expectedLeads: number; expectedOrders: number; contributionEuro: number;
};

function decimal(input: string): number | null {
  const trimmed = input.trim();
  const groupedGerman = /^\d{1,3}(?:\.\d{3})+(?:,\d+)?$/.test(trimmed);
  if (!groupedGerman && !/^\d+(?:[.,]\d+)?$/.test(trimmed)) return null;
  const normalized = groupedGerman ? trimmed.replace(/\./g, "").replace(",", ".") : trimmed.replace(",", ".");
  const num = Number(normalized);
  return Number.isFinite(num) ? num : null;
}

export function parsePercent(input: string): number | null {
  const number = decimal(input);
  return number !== null && number >= 0 && number <= 100 ? number : null;
}

export function parseScenario(rates: Rates): BusinessScenario | null {
  const leadPercent = parsePercent(rates.leadPercent);
  const closePercent = parsePercent(rates.closePercent);
  const contribution = decimal(rates.contributionEuro);
  if (leadPercent === null || closePercent === null || contribution === null || contribution <= 0) return null;
  return { leadRate: leadPercent / 100, closeRate: closePercent / 100, contribution };
}

export function estimateBusinessValue(
  extraClicks: number, relevantShareInput: string | undefined, scenario: BusinessScenario | null,
): ValueEstimate | null {
  if (!scenario || relevantShareInput === undefined || !Number.isFinite(extraClicks) || extraClicks < 0) return null;
  const relevantShare = parsePercent(relevantShareInput);
  if (relevantShare === null) return null;
  const qualifiedClicks = extraClicks * relevantShare / 100;
  const expectedLeads = qualifiedClicks * scenario.leadRate;
  const expectedOrders = expectedLeads * scenario.closeRate;
  return { qualifiedClicks, expectedLeads, expectedOrders, contributionEuro: expectedOrders * scenario.contribution };
}

/** A diagnostic, not a ranking factor. Entries without assumptions remain unscored. */
export function sortByValue<T extends { url: string; estimated_extra_clicks: number }>(
  pages: T[], fitPercentByUrl: Record<string, string>, scenario: BusinessScenario | null,
): T[] {
  return [...pages].sort((a, b) => {
    const av = estimateBusinessValue(a.estimated_extra_clicks, fitPercentByUrl[a.url], scenario)?.contributionEuro;
    const bv = estimateBusinessValue(b.estimated_extra_clicks, fitPercentByUrl[b.url], scenario)?.contributionEuro;
    if (av === null || av === undefined) return bv === null || bv === undefined ? 0 : 1;
    if (bv === null || bv === undefined) return -1;
    return bv - av;
  });
}
