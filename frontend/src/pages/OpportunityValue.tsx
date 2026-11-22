import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum, shortUrl } from "../lib/format";
import { estimateBusinessValue, parsePercent, parseScenario, sortByValue, type Rates } from "../lib/valueModel";

type PageOpportunity = { url: string; title: string | null; estimated_extra_clicks: number; impressions: number; clicks: number };
type ContentRefreshResult = {
  has_data: boolean; reason?: string; pages: PageOpportunity[]; total_pages: number;
  source?: string; start_date?: string | null; end_date?: string | null; notes?: string[];
};

const initialRates: Rates = { leadPercent: "", closePercent: "", contributionEuro: "" };
const money = (v: number) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v);
const oneDigit = (v: number) => new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 }).format(v);

export default function OpportunityValue() {
  const { site } = useSite();
  const [days, setDays] = useState(28);
  const [rates, setRates] = useState<Rates>(initialRates);
  // The manual relevance assessment is scoped by site and URL and is never sent to the server.
  const [fit, setFit] = useState<Record<string, string>>({});
  const data = useQuery<ContentRefreshResult>({
    queryKey: ["content-refresh", site?.id, days],
    queryFn: () => api.get("/sites/" + site!.id + "/content-refresh", { days }),
    enabled: !!site?.id,
  });

  const scenario = useMemo(() => parseScenario(rates), [rates]);
  const pages = useMemo(() => {
    const relevant = Object.fromEntries((data.data?.pages ?? []).map((p) => [p.url, fit[String(site?.id) + ":" + p.url]]));
    return sortByValue(data.data?.pages ?? [], relevant, scenario);
  }, [data.data, fit, scenario, site?.id]);
  const assessed = pages.map((p) => ({
    ...p, result: estimateBusinessValue(p.estimated_extra_clicks, fit[String(site?.id) + ":" + p.url], scenario),
  }));
  const assessedPages = assessed.filter((p) => p.result !== null);
  const totalDb = assessedPages.reduce((sum, p) => sum + (p.result?.contributionEuro ?? 0), 0);

  const setRate = (key: keyof Rates, value: string) => setRates((previous) => ({ ...previous, [key]: value }));
  const rateInput = (key: keyof Rates, label: string, hint: string) => (
    <Field label={label} hint={hint}>
      <Input type="text" inputMode="decimal" value={rates[key]} onChange={(e) => setRate(key, e.target.value)}
        placeholder="Eigene Annahme eingeben" aria-label={label} />
    </Field>
  );
  return (
    <div className="space-y-4">
      <PageHeader title="Wirtschaftliche SEO-Chancen" description="SEO-Maßnahmen nach selbst definierten Szenarien bewerten, statt nur auf Klickpotenzial zu schauen." />
      <Card title="Szenario" description="Alle drei Eingaben stammen von dir. Es werden keine Conversion- oder Margenwerte angenommen.">
        <div className="grid gap-3 md:grid-cols-3">
          {rateInput("leadPercent", "Leadquote aus zusätzlichen Klicks (%)", "Anteil relevanter zusätzlicher Klicks, die zur Anfrage werden")}
          {rateInput("closePercent", "Abschlussquote aus Leads (%)", "Anteil der Anfragen, aus denen Aufträge entstehen")}
          {rateInput("contributionEuro", "Deckungsbeitrag je Auftrag (€)", "Deckungsbeitrag statt Umsatz, z. B. 2000,50")}
        </div>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          Formel: geschätzte Zusatzklicks × manuell geschätzter relevanter Anteil × Leadquote × Abschlussquote × DB je Auftrag.
        </p>
        {!scenario && <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
          Bitte drei gültige Werte eingeben (Quoten 0 bis 100 %, Deckungsbeitrag größer als 0).
        </p>}
        <p className="mt-2 text-xs text-slate-500">Die Angaben bleiben nur in dieser geöffneten Ansicht. Sie werden nicht gespeichert oder automatisch aus Matomo abgeleitet.</p>
      </Card>
      <Card title="Zeitraum">
        <Select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="GSC-Zeitraum">
          {[7, 14, 28, 56, 90, 180].map((n) => <option key={n} value={n}>{n} Tage</option>)}
        </Select>
      </Card>
      {!site && <Card><EmptyState title="Zuerst eine Website auswählen" /></Card>}
      {data.isLoading && <Card><Spinner label="GSC-Chancen laden…" /></Card>}
      {data.error && <ErrorBox error={data.error} onRetry={() => data.refetch()} />}
      {data.data && !data.data.has_data && <Card><EmptyState title="Keine zugeordneten GSC-Daten" description={data.data.reason ?? "Die GSC-Analyse benötigt Suchanfrage-URL-Paare."} /></Card>}
      {data.data?.has_data && <>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <Stat label="SEO-Seiten mit Chancen" value={fmtInt(data.data.total_pages)} />
          <Stat label="Manuell bewertete Seiten" value={assessedPages.length + " von " + pages.length} />
          <Stat label="Szenario-Deckungsbeitrag" value={scenario ? money(totalDb) : "–"} hint="Keine Prognose – nur für manuell bewertete Seiten" />
        </div>
        <Card>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Die Suchdaten stammen aus GSC. Die zusätzlichen Klicks aus Content-Refresh sind bereits eine hypothetische CTR-Schätzung.
            Relevanzanteil, Lead- und Abschlussquote sowie Marge sind ebenfalls Annahmen.
            Der berechnete DB ist daher <strong>keine Vorhersage und kein gemessener Ertrag</strong>.
          </p>
          {(data.data.notes ?? []).map((n) => <p className="mt-2 text-sm text-amber-700 dark:text-amber-300" key={n}>{n}</p>)}
        </Card>
        {pages.length === 0 && <Card><EmptyState title="Keine Chancen im Zeitraum" /></Card>}
        {assessed.map((page) => {
          const key = String(site?.id) + ":" + page.url;
          const currentFit = fit[key] ?? "";
          const validFit = currentFit === "" || parsePercent(currentFit) !== null;
          return (
            <Card key={key} title={page.title || shortUrl(page.url, site?.url)} description={page.url}
              actions={<Link to="/content-refresh" className="text-sm font-medium text-brand-700 underline dark:text-brand-300">Content-Refresh</Link>}>
              <div className="grid gap-3 md:grid-cols-3 md:items-end">
                <div>
                  <div className="text-xs text-slate-500">Geschätzte Zusatzklicks</div>
                  <div className="text-lg font-semibold">+{fmtInt(page.estimated_extra_clicks)}</div>
                  <div className="text-xs text-slate-500">{fmtInt(page.impressions)} GSC-Impressionen der Chancen</div>
                </div>
                <Field label="Wirtschaftlich relevanter Anteil (%)" hint="Eigene Einschätzung; leer = nicht bewertet">
                  <Input type="text" inputMode="decimal" aria-label={"Relevanter Anteil für " + page.url} value={currentFit}
                    placeholder="0 bis 100" onChange={(e) => setFit((prev) => ({ ...prev, [key]: e.target.value }))} />
                </Field>
                <div>
                  <div className="text-xs text-slate-500">DB-Szenario für diese Seite</div>
                  <div className="text-lg font-semibold">{page.result ? money(page.result.contributionEuro) : "–"}</div>
                  {page.result && <div className="text-xs text-slate-500">{oneDigit(page.result.expectedLeads)} angenommene Leads · {oneDigit(page.result.expectedOrders)} angenommene Aufträge</div>}
                </div>
              </div>
              {!validFit && <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">Nur Werte von 0 bis 100 % eingeben.</p>}
              {page.result && <div className="mt-2"><Badge tone="blue">Szenariowert, nicht gemessen</Badge></div>}
              <p className="mt-2 text-xs text-slate-500">Gemessene Impressionen: {fmtInt(page.impressions)} · angenommene zusätzliche Klicks: {fmtNum(page.estimated_extra_clicks)}</p>
            </Card>
          );
        })}
      </>}
    </div>
  );
}
