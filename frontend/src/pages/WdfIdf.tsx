import { useMutation } from "@tanstack/react-query";
import { Sigma } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, Checkbox, type Column, DataTable, EmptyState, ErrorBox, Field, Input, Notice, PageHeader, Select, Spinner, Stat, Textarea, Url, chartColors,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtInt, fmtPct } from "../lib/format";

const STATUS_TONE: Record<string, string> = {
  "fehlt": "red", "deutlich unter Schnitt": "amber", "über Maximum": "purple", "im Rahmen": "green", "selten": "gray",
};

function parseLines(text: string): string[] {
  return Array.from(new Set(text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)));
}

const num = (v: number | undefined | null) => (v === null || v === undefined ? "–" : v.toFixed(3));

export default function WdfIdf() {
  const [keyword, setKeyword] = useState("");
  const [myUrl, setMyUrl] = useState("");
  const [myText, setMyText] = useState("");
  const [urlText, setUrlText] = useState("");
  const [bigrams, setBigrams] = useState(false);
  const [useSerp, setUseSerp] = useState(false);
  const [limit, setLimit] = useState("50");
  const urls = parseLines(urlText);

  const run = useMutation({
    mutationFn: () => api.post("/content/wdf-idf", {
      keyword: keyword.trim(), my_url: myUrl.trim() || null, my_content: myText.trim() || null,
      competitor_urls: urls, use_serp: useSerp && urls.length === 0, ngram: bigrams ? 2 : 1, limit: Number(limit), lang: "de", country: "de",
    }),
  });
  const r = run.data;
  const canSubmit = urls.length <= 10 && (urls.length > 0 || (useSerp && !!keyword.trim()));
  const submit = (e: FormEvent) => { e.preventDefault(); if (canSubmit) run.mutate(); };
  const hasOwn = !!r?.summary;
  const docs: any[] = r?.documents ?? [];
  const compDocs = docs.filter((d) => !d.is_own);

  const columns: Column<any>[] = [
    { key: "term", header: "Begriff", render: (t) => (
      <span className="font-medium text-slate-900 dark:text-slate-100">{t.term}{t.is_keyword && <Badge tone="blue">Keyword</Badge>}</span>
    ) },
    ...(hasOwn ? [
      { key: "own", header: "Eigene Seite", align: "right" as const, tooltip: "WDF*IDF der eigenen Seite (Anzahl in Klammern)", render: (t: any) => <span className="tabular-nums">{num(t.own)} <span className="text-slate-400">({t.own_count})</span></span> },
    ] : []),
    { key: "mean", header: "Ø Wettbewerb", align: "right", render: (t) => <span className="tabular-nums">{num(t.competitor_mean)}</span> },
    { key: "max", header: "Max", align: "right", render: (t) => <span className="tabular-nums">{num(t.competitor_max)}</span> },
    { key: "share", header: "Seiten", align: "right", tooltip: "Anteil der Wettbewerberseiten, die den Begriff verwenden", render: (t) => `${t.competitors_using} (${fmtPct(t.competitor_share, 0)})` },
    ...(hasOwn ? [{ key: "status", header: "Bewertung", render: (t: any) => <Badge tone={STATUS_TONE[t.status] ?? "gray"}>{t.status}</Badge> }] : []),
  ];

  const chartData = (r?.terms ?? []).slice(0, 25).map((t: any) => ({ term: t.term, "Ø Wettbewerb": t.competitor_mean, Max: t.competitor_max, ...(hasOwn ? { "Eigene Seite": t.own } : {}) }));
  const dist: Record<string, number[]> = r?.distribution ?? {};

  return (
    <div>
      <PageHeader title="WDF*IDF-Analyse"
        description="Vergleicht die Termgewichtung deiner Seite mit den Seiten, die für ein Keyword ranken. Deutsche Stoppwörter, echte WDF*IDF-Formel, Drittelverteilung und Überschriften im Vergleich." />
      <div className="space-y-4">
        <Card title="Eingabe">
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-3 lg:grid-cols-12">
              <Field label="Fokus-Keyword" className="lg:col-span-4">
                <Input maxLength={200} value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="z. B. schwarze spüle" />
              </Field>
              <Field label="Eigene URL" hint="optional; alternativ Text einfügen" className="lg:col-span-6">
                <Input type="url" maxLength={2048} value={myUrl} onChange={(e) => setMyUrl(e.target.value)} placeholder="https://example.de/ratgeber/…" />
              </Field>
              <Field label="Begriffe" className="lg:col-span-2">
                <Select value={limit} onChange={(e) => setLimit(e.target.value)}>
                  {["30", "50", "100"].map((v) => <option key={v} value={v}>Top {v}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Eigener Text (optional)" hint="HTML, Markdown oder Klartext – z. B. ein Entwurf vor der Veröffentlichung. Hat Vorrang vor der eigenen URL.">
              <Textarea rows={4} value={myText} onChange={(e) => setMyText(e.target.value)} />
            </Field>
            <Field label="Wettbewerber-URLs, eine pro Zeile" hint={`${urls.length} / 10 – am besten die Top 5–10 aus Google für das Keyword.`}>
              <Textarea rows={5} value={urlText} onChange={(e) => setUrlText(e.target.value)} className="font-mono text-xs" placeholder={"https://wettbewerber-1.de/seite\nhttps://wettbewerber-2.de/ratgeber"} />
            </Field>
            <div className="flex flex-wrap items-center gap-4">
              <Checkbox label="Zweiwort-Begriffe einbeziehen" checked={bigrams} onChange={setBigrams} />
              <Checkbox label="Ohne URLs: SERP-Anbieter fragen" checked={useSerp} onChange={setUseSerp} hint="nur wenn in den Einstellungen ein Anbieter hinterlegt ist" />
              <Button type="submit" variant="primary" icon={<Sigma className="h-4 w-4" />} loading={run.isPending} disabled={!canSubmit}>Analysieren</Button>
            </div>
          </form>
        </Card>

        {run.isPending && <Card><Spinner label="Seiten werden geladen und ausgewertet…" /></Card>}
        {run.error && <ErrorBox error={run.error} onRetry={() => run.mutate()} />}
        {!r && !run.isPending && !run.error && (
          <Card><EmptyState icon={<Sigma className="h-6 w-6" />} title="Noch keine Analyse" description="Wettbewerber-URLs eintragen und optional die eigene Seite oder einen Entwurf." /></Card>
        )}

        {r && !run.isPending && (
          <>
            {(r.notes ?? []).map((n: string) => <Notice key={n} tone={n.startsWith("Nur ") || n.startsWith("Eigene URL") ? "warn" : "info"}>{n}</Notice>)}
            {(r.failed ?? []).length > 0 && (
              <Notice tone="warn">Nicht ladbar: {r.failed.map((f: any) => <span key={f.url} className="mr-2"><Url href={f.url} /> ({f.error})</span>)}</Notice>
            )}

            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Wettbewerberseiten" value={fmtInt(compDocs.length)} />
              <Stat label="Ø Wörter Wettbewerb" value={fmtInt(compDocs.length ? compDocs.reduce((s, d) => s + d.words, 0) / compDocs.length : null)} />
              {hasOwn ? <Stat label="Wörter eigene Seite" value={fmtInt(docs[0]?.words)} /> : <Stat label="Eigene Seite" value="–" />}
              {hasOwn ? <Stat label="Fehlende Begriffe" value={fmtInt(r.summary.missing.length)} tone={r.summary.missing.length > 5 ? "warn" : "good"} hint="von ≥ 50 % der Wettbewerber genutzt" /> : <Stat label="Begriffe" value={fmtInt(r.terms.length)} />}
            </div>

            {hasOwn && (r.summary.missing.length > 0 || r.summary.over_max.length > 0) && (
              <Card title="Auf einen Blick">
                <div className="grid gap-4 md:grid-cols-2 text-sm">
                  <div>
                    <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Fehlen, obwohl die meisten Wettbewerber sie nutzen</div>
                    <div className="flex flex-wrap gap-1">{r.summary.missing.map((t: string) => <Badge key={t} tone="red">{t}</Badge>)}</div>
                  </div>
                  <div>
                    <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Über dem Maximum der Wettbewerber</div>
                    {r.summary.over_max.length ? <div className="flex flex-wrap gap-1">{r.summary.over_max.map((t: string) => <Badge key={t} tone="purple">{t}</Badge>)}</div> : <span className="text-slate-500">keine</span>}
                  </div>
                </div>
              </Card>
            )}

            <Card title="WDF*IDF-Kurve (Top 25)" description={r.method}>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="term" angle={-45} textAnchor="end" interval={0} tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <ChartTooltip formatter={(v: any) => (typeof v === "number" ? v.toFixed(3) : v)} />
                    <Legend verticalAlign="top" />
                    <Bar dataKey="Ø Wettbewerb" fill="#cbd5e1" />
                    <Line dataKey="Max" stroke={chartColors[2]} dot={false} strokeDasharray="4 3" />
                    {hasOwn && <Line dataKey="Eigene Seite" stroke={chartColors[0]} strokeWidth={2} />}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card padded={false} title={`Begriffe (${r.terms.length})`}>
              <div className="max-h-[36rem] overflow-y-auto">
                <DataTable dense columns={columns} rows={r.terms} rowKey={(t: any) => t.term} empty={<EmptyState title="Keine gemeinsamen Begriffe" />} />
              </div>
            </Card>

            {hasOwn && Object.keys(dist).length > 0 && (
              <Card padded={false} title="Drittelverteilung der eigenen Seite" description="Wo im Text die wichtigsten Begriffe vorkommen">
                <DataTable dense rows={Object.entries(dist).map(([term, v]) => ({ term, v }))} rowKey={(x: any) => x.term} columns={[
                  { key: "t", header: "Begriff", render: (x: any) => x.term },
                  ...["Anfang", "Mitte", "Ende"].map((label, i) => ({ key: label, header: label, align: "right" as const, render: (x: any) => {
                    const max = Math.max(...x.v);
                    return <span className={x.v[i] && x.v[i] === max ? "font-semibold text-brand-700 dark:text-brand-300" : "text-slate-500"}>{x.v[i]}</span>;
                  } })),
                ]} />
              </Card>
            )}

            <Card title="Überschriften im Vergleich">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {docs.map((d) => (
                  <div key={d.url} className="min-w-0">
                    <div className="mb-1 flex items-center gap-2 text-xs">{d.is_own && <Badge tone="blue">eigene Seite</Badge>}<span className="truncate"><Url href={d.url} /></span></div>
                    <div className="text-xs text-slate-500">{fmtInt(d.words)} Wörter</div>
                    <ul className="mt-1 space-y-0.5 text-xs text-slate-700 dark:text-slate-300">
                      {(d.headings ?? []).map((h: any, i: number) => (
                        <li key={i} style={{ paddingLeft: `${(h.level - 1) * 10}px` }}><span className="text-slate-400">H{h.level}</span> {h.text}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
