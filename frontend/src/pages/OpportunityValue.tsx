import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum, shortUrl } from "../lib/format";
import { estimateBusinessValue, parsePercent, parseScenario, sortByValue, type Rates } from "../lib/valueModel";

type PageOpportunity = { url: string; title: string | null; estimated_extra_clicks: number; impressions: number; clicks: number };
type ContentRefreshResult = {
  has_data: boolean;
  reason?: string;
  pages: PageOpportunity[];
  total_pages: number;
  source?: string;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string[];
};

type DependencyAuditResult = {
  has_data: boolean;
  reason?: string;
  site_id: number;
  site_name: string;
  start_date: string;
  end_date: string;
  days_evaluated: number;
  gsc_source: string;
  total_clicks: number;
  total_impressions: number;
  landingpage_concentration: {
    total_landing_pages: number;
    top_1_share: number;
    top_3_share: number;
    top_5_share: number;
    top_10_share: number;
    pareto: {
      pages_for_80_pct_clicks: number;
      percentage_of_all_pages: number;
      summary: string;
    };
    risk_level: "kritisch" | "moderat" | "ausgewogen";
    risk_assessment: string;
    top_pages: {
      url: string;
      clicks: number;
      impressions: number;
      click_share: number;
      single_point_of_failure: boolean;
    }[];
  };
  search_term_concentration: {
    total_queries: number;
    top_1_query_share: number;
    top_3_query_share: number;
    brand_tokens_used: string[];
    brand_clicks: number;
    brand_share: number;
    non_brand_clicks: number;
    non_brand_share: number;
    brand_risk_level: string;
    brand_risk_assessment: string;
    top_queries: {
      query: string;
      clicks: number;
      impressions: number;
      click_share: number;
      is_brand: boolean;
    }[];
  };
  channel_resilience: {
    google_gsc_active: boolean;
    bing_webmaster_active: boolean;
    channel_assessment: string;
  };
  method: string;
};

const initialRates: Rates = { leadPercent: "", closePercent: "", contributionEuro: "" };
const money = (v: number) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v);
const oneDigit = (v: number) => new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 }).format(v);
const pctFmt = (v: number | null | undefined) => (v == null ? "–" : (v * 100).toLocaleString("de-DE", { maximumFractionDigits: 1 }) + " %");

export default function OpportunityValue() {
  const { site } = useSite();
  const [mainTab, setMainTab] = useState<"chancen" | "klumpenrisiko">("chancen");
  const [days, setDays] = useState(28);
  const [rates, setRates] = useState<Rates>(initialRates);
  const [fit, setFit] = useState<Record<string, string>>({});
  const [customBrand, setCustomBrand] = useState("");
  const [activeBrandFilter, setActiveBrandFilter] = useState("");

  const refreshData = useQuery<ContentRefreshResult>({
    queryKey: ["content-refresh", site?.id, days],
    queryFn: () => api.get("/sites/" + site!.id + "/content-refresh", { days }),
    enabled: !!site?.id && mainTab === "chancen",
  });

  const dependencyData = useQuery<DependencyAuditResult>({
    queryKey: ["dependency-audit", site?.id, days, activeBrandFilter],
    queryFn: () =>
      api.get("/sites/" + site!.id + "/dependency-audit", {
        days,
        brand_term: activeBrandFilter.trim() || undefined,
      }),
    enabled: !!site?.id && mainTab === "klumpenrisiko",
  });

  const scenario = useMemo(() => parseScenario(rates), [rates]);
  const pages = useMemo(() => {
    const relevant = Object.fromEntries((refreshData.data?.pages ?? []).map((p) => [p.url, fit[String(site?.id) + ":" + p.url]]));
    return sortByValue(refreshData.data?.pages ?? [], relevant, scenario);
  }, [refreshData.data, fit, scenario, site?.id]);

  const assessed = pages.map((p) => ({
    ...p,
    result: estimateBusinessValue(p.estimated_extra_clicks, fit[String(site?.id) + ":" + p.url], scenario),
  }));
  const assessedPages = assessed.filter((p) => p.result !== null);
  const totalDb = assessedPages.reduce((sum, p) => sum + (p.result?.contributionEuro ?? 0), 0);

  const setRate = (key: keyof Rates, value: string) => setRates((previous) => ({ ...previous, [key]: value }));
  const rateInput = (key: keyof Rates, label: string, hint: string) => (
    <Field label={label} hint={hint}>
      <Input
        type="text"
        inputMode="decimal"
        value={rates[key]}
        onChange={(e) => setRate(key, e.target.value)}
        placeholder="Eigene Annahme eingeben"
        aria-label={label}
      />
    </Field>
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Wirtschaftliche Chancen & Klumpenrisiko"
        description="Wirtschaftliche SEO-Szenarien und Abhängigkeits-Audits (Landingpage-, Keyword- und Suchmaschinen-Klumpenrisiken)."
      />

      <div role="tablist" aria-label="Wirtschaftliche Analyse" className="flex flex-wrap gap-2">
        <button
          role="tab"
          aria-selected={mainTab === "chancen"}
          onClick={() => setMainTab("chancen")}
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
            mainTab === "chancen"
              ? "bg-brand-600 text-white"
              : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          }`}
        >
          Wirtschaftliche Chancen (Szenario)
        </button>
        <button
          role="tab"
          aria-selected={mainTab === "klumpenrisiko"}
          onClick={() => setMainTab("klumpenrisiko")}
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
            mainTab === "klumpenrisiko"
              ? "bg-brand-600 text-white"
              : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          }`}
        >
          Klumpenrisiko & Abhängigkeiten
        </button>
      </div>

      <Card title="GSC-Beobachtungszeitraum">
        <Select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="GSC-Zeitraum" className="w-48">
          {[7, 14, 28, 56, 90, 180].map((n) => (
            <option key={n} value={n}>
              {n} Tage
            </option>
          ))}
        </Select>
      </Card>

      {!site && (
        <Card>
          <EmptyState title="Zuerst eine Website auswählen" />
        </Card>
      )}

      {mainTab === "klumpenrisiko" && site && (
        <div className="space-y-4">
          {dependencyData.isLoading && (
            <Card>
              <Spinner label="Berechne Klumpenrisiko aus GSC-Daten…" />
            </Card>
          )}
          {dependencyData.error && <ErrorBox error={dependencyData.error} onRetry={() => dependencyData.refetch()} />}
          {dependencyData.data && !dependencyData.data.has_data && (
            <Card>
              <EmptyState title="Keine GSC-Daten vorhanden" description={dependencyData.data.reason} />
            </Card>
          )}
          {dependencyData.data?.has_data && (
            <>
              {/* Landingpage Concentration Section */}
              <Card
                title="1. Landingpage-Klumpenrisiko (URL-Konzentration)"
                description="Wie stark hängt der organische Gesamterfolg von nur wenigen Seiten ab?"
              >
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <Badge
                    tone={
                      dependencyData.data.landingpage_concentration.risk_level === "kritisch"
                        ? "red"
                        : dependencyData.data.landingpage_concentration.risk_level === "moderat"
                        ? "amber"
                        : "green"
                    }
                  >
                    Risikostufe: {dependencyData.data.landingpage_concentration.risk_level.toUpperCase()}
                  </Badge>
                  <span className="text-sm text-slate-600 dark:text-slate-300">
                    {dependencyData.data.landingpage_concentration.risk_assessment}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Stat
                    label="Top-1 URL Anteil"
                    value={pctFmt(dependencyData.data.landingpage_concentration.top_1_share)}
                    tone={dependencyData.data.landingpage_concentration.top_1_share >= 0.4 ? "bad" : undefined}
                  />
                  <Stat
                    label="Top-3 URLs Anteil"
                    value={pctFmt(dependencyData.data.landingpage_concentration.top_3_share)}
                    tone={dependencyData.data.landingpage_concentration.top_3_share >= 0.65 ? "bad" : undefined}
                  />
                  <Stat
                    label="Top-5 URLs Anteil"
                    value={pctFmt(dependencyData.data.landingpage_concentration.top_5_share)}
                  />
                  <Stat
                    label="Pareto-Fokus"
                    value={`${dependencyData.data.landingpage_concentration.pareto.percentage_of_all_pages} %`}
                    hint={`${dependencyData.data.landingpage_concentration.pareto.pages_for_80_pct_clicks} URLs für 80 % Klicks`}
                  />
                </div>

                {/* Top pages table */}
                <div className="mt-4">
                  <h4 className="mb-2 text-xs font-semibold uppercase text-slate-500">Top-Traffic-Landingpages</h4>
                  <div className="overflow-x-auto rounded-lg border border-slate-200 text-xs dark:border-slate-800">
                    <table className="w-full text-left">
                      <thead className="bg-slate-50 dark:bg-slate-900">
                        <tr>
                          <th className="p-2.5">URL</th>
                          <th className="p-2.5 text-right">Klicks</th>
                          <th className="p-2.5 text-right">Impressionen</th>
                          <th className="p-2.5 text-right">Anteil Gesamtklicks</th>
                          <th className="p-2.5">Risiko-Einstufung</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dependencyData.data.landingpage_concentration.top_pages.map((p) => (
                          <tr key={p.url} className="border-t dark:border-slate-800">
                            <td className="p-2.5 max-w-md truncate">
                              <a href={p.url} target="_blank" rel="noreferrer" className="font-medium underline break-all">
                                {p.url}
                              </a>
                            </td>
                            <td className="p-2.5 text-right font-semibold">{fmtInt(p.clicks)}</td>
                            <td className="p-2.5 text-right text-slate-500">{fmtInt(p.impressions)}</td>
                            <td className="p-2.5 text-right font-medium">{pctFmt(p.click_share)}</td>
                            <td className="p-2.5">
                              {p.single_point_of_failure ? (
                                <Badge tone="red">Single Point of Failure (≥25 %)</Badge>
                              ) : (
                                <span className="text-slate-500">Verteilt</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </Card>

              {/* Brand vs Non-Brand Section */}
              <Card
                title="2. Suchbegriff- & Marken-Klumpenrisiko"
                description="Wie stark basiert dein Search-Traffic auf dem Firmennamen vs. generischen Suchbegriffen?"
              >
                <div className="mb-4 flex flex-wrap items-end gap-3">
                  <Field label="Verwendeter Markenbegriff" hint="Standardmäßig aus Site-Name und Domain abgeleitet">
                    <Input
                      placeholder={dependencyData.data.search_term_concentration.brand_tokens_used.join(", ")}
                      value={customBrand}
                      onChange={(e) => setCustomBrand(e.target.value)}
                      className="w-64"
                    />
                  </Field>
                  <Button variant="secondary" size="md" onClick={() => setActiveBrandFilter(customBrand)}>
                    Filter anwenden
                  </Button>
                  {activeBrandFilter && (
                    <Button variant="ghost" size="md" onClick={() => { setCustomBrand(""); setActiveBrandFilter(""); }}>
                      Zurücksetzen
                    </Button>
                  )}
                </div>

                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <Badge tone={dependencyData.data.search_term_concentration.brand_risk_level === "hohe_markenabhaengigkeit" ? "amber" : "blue"}>
                    {dependencyData.data.search_term_concentration.brand_risk_level}
                  </Badge>
                  <span className="text-sm text-slate-600 dark:text-slate-300">
                    {dependencyData.data.search_term_concentration.brand_risk_assessment}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Stat
                    label="Brand-Traffic Anteil"
                    value={pctFmt(dependencyData.data.search_term_concentration.brand_share)}
                    hint={`${fmtInt(dependencyData.data.search_term_concentration.brand_clicks)} Klicks`}
                  />
                  <Stat
                    label="Non-Brand Traffic Anteil"
                    value={pctFmt(dependencyData.data.search_term_concentration.non_brand_share)}
                    hint={`${fmtInt(dependencyData.data.search_term_concentration.non_brand_clicks)} Klicks`}
                    tone={dependencyData.data.search_term_concentration.non_brand_share >= 0.5 ? "good" : undefined}
                  />
                  <Stat
                    label="Top-1 Keyword Anteil"
                    value={pctFmt(dependencyData.data.search_term_concentration.top_1_query_share)}
                  />
                  <Stat
                    label="Top-3 Keywords Anteil"
                    value={pctFmt(dependencyData.data.search_term_concentration.top_3_query_share)}
                  />
                </div>

                {/* Top queries table */}
                <div className="mt-4">
                  <h4 className="mb-2 text-xs font-semibold uppercase text-slate-500">Top-Suchanfragen</h4>
                  <div className="overflow-x-auto rounded-lg border border-slate-200 text-xs dark:border-slate-800">
                    <table className="w-full text-left">
                      <thead className="bg-slate-50 dark:bg-slate-900">
                        <tr>
                          <th className="p-2.5">Suchanfrage</th>
                          <th className="p-2.5 text-right">Klicks</th>
                          <th className="p-2.5 text-right">Impressionen</th>
                          <th className="p-2.5 text-right">Anteil</th>
                          <th className="p-2.5">Typ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dependencyData.data.search_term_concentration.top_queries.map((q) => (
                          <tr key={q.query} className="border-t dark:border-slate-800">
                            <td className="p-2.5 font-medium">{q.query}</td>
                            <td className="p-2.5 text-right font-semibold">{fmtInt(q.clicks)}</td>
                            <td className="p-2.5 text-right text-slate-500">{fmtInt(q.impressions)}</td>
                            <td className="p-2.5 text-right font-medium">{pctFmt(q.click_share)}</td>
                            <td className="p-2.5">
                              {q.is_brand ? <Badge tone="blue">Brand</Badge> : <Badge tone="green">Non-Brand</Badge>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </Card>

              {/* Search Engine Resilience */}
              <Card title="3. Suchmaschinen-Resilienz">
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  {dependencyData.data.channel_resilience.channel_assessment}
                </p>
                <p className="mt-2 text-xs text-slate-500">{dependencyData.data.method}</p>
              </Card>
            </>
          )}
        </div>
      )}

      {mainTab === "chancen" && site && (
        <>
          <Card title="Szenario" description="Alle drei Eingaben stammen von dir. Es werden keine Conversion- oder Margenwerte angenommen.">
            <div className="grid gap-3 md:grid-cols-3">
              {rateInput("leadPercent", "Leadquote aus zusätzlichen Klicks (%)", "Anteil relevanter zusätzlicher Klicks, die zur Anfrage werden")}
              {rateInput("closePercent", "Abschlussquote aus Leads (%)", "Anteil der Anfragen, aus denen Aufträge entstehen")}
              {rateInput("contributionEuro", "Deckungsbeitrag je Auftrag (€)", "Deckungsbeitrag statt Umsatz, z. B. 2000,50")}
            </div>
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
              Formel: geschätzte Zusatzklicks × manuell geschätzter relevanter Anteil × Leadquote × Abschlussquote × DB je Auftrag.
            </p>
            {!scenario && (
              <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
                Bitte drei gültige Werte eingeben (Quoten 0 bis 100 %, Deckungsbeitrag größer als 0).
              </p>
            )}
            <p className="mt-2 text-xs text-slate-500">
              Die Angaben bleiben nur in dieser geöffneten Ansicht. Sie werden nicht gespeichert oder automatisch aus Matomo abgeleitet.
            </p>
          </Card>

          {refreshData.isLoading && <Card><Spinner label="GSC-Chancen laden…" /></Card>}
          {refreshData.error && <ErrorBox error={refreshData.error} onRetry={() => refreshData.refetch()} />}
          {refreshData.data && !refreshData.data.has_data && (
            <Card>
              <EmptyState title="Keine zugeordneten GSC-Daten" description={refreshData.data.reason ?? "Die GSC-Analyse benötigt Suchanfrage-URL-Paare."} />
            </Card>
          )}
          {refreshData.data?.has_data && (
            <>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Stat label="SEO-Seiten mit Chancen" value={fmtInt(refreshData.data.total_pages)} />
                <Stat label="Manuell bewertete Seiten" value={assessedPages.length + " von " + pages.length} />
                <Stat label="Szenario-Deckungsbeitrag" value={scenario ? money(totalDb) : "–"} hint="Keine Prognose – nur für manuell bewertete Seiten" />
              </div>
              <Card>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  Die Suchdaten stammen aus GSC. Die zusätzlichen Klicks aus Content-Refresh sind bereits eine hypothetische CTR-Schätzung.
                  Relevanzanteil, Lead- und Abschlussquote sowie Marge sind ebenfalls Annahmen.
                  Der berechnete DB ist daher <strong>keine Vorhersage und kein gemessener Ertrag</strong>.
                </p>
                {(refreshData.data.notes ?? []).map((n) => (
                  <p className="mt-2 text-sm text-amber-700 dark:text-amber-300" key={n}>
                    {n}
                  </p>
                ))}
              </Card>
              {pages.length === 0 && <Card><EmptyState title="Keine Chancen im Zeitraum" /></Card>}
              {assessed.map((page) => {
                const key = String(site?.id) + ":" + page.url;
                const currentFit = fit[key] ?? "";
                const validFit = currentFit === "" || parsePercent(currentFit) !== null;
                return (
                  <Card
                    key={key}
                    title={page.title || shortUrl(page.url, site?.url)}
                    description={page.url}
                    actions={
                      <Link to="/content-refresh" className="text-sm font-medium text-brand-700 underline dark:text-brand-300">
                        Content-Refresh
                      </Link>
                    }
                  >
                    <div className="grid gap-3 md:grid-cols-3 md:items-end">
                      <div>
                        <div className="text-xs text-slate-500">Geschätzte Zusatzklicks</div>
                        <div className="text-lg font-semibold">+{fmtInt(page.estimated_extra_clicks)}</div>
                        <div className="text-xs text-slate-500">{fmtInt(page.impressions)} GSC-Impressionen der Chancen</div>
                      </div>
                      <Field label="Wirtschaftlich relevanter Anteil (%)" hint="Eigene Einschätzung; leer = nicht bewertet">
                        <Input
                          type="text"
                          inputMode="decimal"
                          aria-label={"Relevanter Anteil für " + page.url}
                          value={currentFit}
                          placeholder="0 bis 100"
                          onChange={(e) => setFit((prev) => ({ ...prev, [key]: e.target.value }))}
                        />
                      </Field>
                      <div>
                        <div className="text-xs text-slate-500">DB-Szenario für diese Seite</div>
                        <div className="text-lg font-semibold">{page.result ? money(page.result.contributionEuro) : "–"}</div>
                        {page.result && (
                          <div className="text-xs text-slate-500">
                            {oneDigit(page.result.expectedLeads)} angenommene Leads · {oneDigit(page.result.expectedOrders)} angenommene Aufträge
                          </div>
                        )}
                      </div>
                    </div>
                    {!validFit && <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">Nur Werte von 0 bis 100 % eingeben.</p>}
                    {page.result && (
                      <div className="mt-2">
                        <Badge tone="blue">Szenariowert, nicht gemessen</Badge>
                      </div>
                    )}
                    <p className="mt-2 text-xs text-slate-500">
                      Gemessene Impressionen: {fmtInt(page.impressions)} · angenommene zusätzliche Klicks: {fmtNum(page.estimated_extra_clicks)}
                    </p>
                  </Card>
                );
              })}
            </>
          )}
        </>
      )}
    </div>
  );
}
