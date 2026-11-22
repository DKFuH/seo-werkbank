import { useMutation, useQuery } from "@tanstack/react-query";
import { Search, Sparkles } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge, Button, Card, type Column, DataBadge, DataTable, EmptyState, ErrorBox, Field, Input, Notice, PageHeader, ScoreRing, Spinner, Stat, Textarea, Url,
} from "../components/ui";
import { api, ApiError } from "../lib/api";
import { fmtInt, fmtPct, titleCase } from "../lib/format";

const INTENT_TONE: Record<string, string> = { transactional: "green", commercial: "purple", navigational: "blue", local: "orange", informational: "gray" };
const COMPONENT_MAX: Record<string, number> = { authority_domains: 40, homepage_results: 15, optimised_titles: 25, content_depth: 20 };
const COMPONENT_HELP: Record<string, string> = {
  authority_domains: "Anteil der Top-Ergebnisse auf sehr großen oder .gov/.edu-Domains",
  homepage_results: "Anteil der Top-Ergebnisse, die Startseiten sind",
  optimised_titles: "Anteil der Ergebnis-Titles mit allen Keyword-Wörtern",
  content_depth: "Durchschnittliche Wortzahl der geladenen Seiten (Deckel bei 2.500 Wörtern)",
};

function Chip({ children, title }: { children: ReactNode; title?: string }) {
  return <span title={title} className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">{children}</span>;
}

function parseLines(text: string): string[] {
  return Array.from(new Set(text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)));
}

const termColumns: Column<any>[] = [
  { key: "term", header: "Begriff", render: (t) => <span className="font-medium text-slate-900 dark:text-slate-100">{t.term}</span> },
  { key: "documents", header: "Seiten", align: "right", tooltip: "Anzahl der analysierten Seiten, die den Begriff nutzen", render: (t) => t.documents },
  { key: "share", header: "Anteil", align: "right", render: (t) => fmtPct(t.share, 0) },
  { key: "avg", header: "Ø Nennungen", align: "right", tooltip: "Durchschnittliche Häufigkeit auf den Seiten, die ihn nutzen", render: (t) => t.avg_count },
];

function AiBrief({ keyword, serp }: { keyword: string; serp: any }) {
  const run = useMutation({ mutationFn: () => api.post("/ai/run", { task: "content_brief", keyword, serp }) });
  return (
    <Card title="KI-Content-Briefing" description="Vom eingerichteten KI-Anbieter ausschließlich aus der Analyse dieser Seite erstellt."
      actions={<Button size="sm" variant="primary" icon={<Sparkles className="h-3.5 w-3.5" />} loading={run.isPending} onClick={() => run.mutate()}>Briefing mit KI erstellen</Button>}>
      {run.isPending ? <Spinner label="Briefing wird geschrieben…" /> : run.error ? (
        <div className="space-y-2">
          <ErrorBox error={run.error} onRetry={() => run.mutate()} />
          {run.error instanceof ApiError && run.error.status === 400 && (
            <p className="text-xs text-slate-500 dark:text-slate-400">KI-Funktionen sind optional und brauchen einen Anbieter (Ollama oder einen OpenAI-kompatiblen Endpunkt). <Link to="/settings" className="font-medium text-brand-700 hover:underline dark:text-brand-300">In den Einstellungen einrichten</Link>.</p>
          )}
        </div>
      ) : run.data ? (
        <div className="space-y-3">
          <div className="prose-ai whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{run.data.output}</div>
          <p className="border-t border-slate-100 pt-2 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
            {run.data.provider}{run.data.model ? ` · ${run.data.model}` : ""}. {run.data.grounding}
          </p>
        </div>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">Macht aus Überschriften-Themen, häufigen Begriffen, Fragen und Seitenstatistik oben eine Gliederung für eine neue Seite.</p>
      )}
    </Card>
  );
}

function Difficulty({ d }: { d: any }) {
  if (!d || d.score === null || d.score === undefined) {
    return (
      <Card title={<span className="inline-flex items-center gap-2">Schwierigkeit <DataBadge kind="unavailable" /></span>}>
        <p className="text-sm text-slate-500 dark:text-slate-400">{d?.reason ?? "Keine SERP-Daten"}. Lieber kein Wert als ein geratener.</p>
      </Card>
    );
  }
  const inputs = d.inputs ?? {};
  return (
    <Card title={<span className="inline-flex items-center gap-2">Geschätzte Schwierigkeit <DataBadge kind="estimated" /></span>}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex shrink-0 flex-col items-center gap-1.5">
          <ScoreRing score={d.score} label="of 100" />
          <Badge tone={d.label === "hard" ? "red" : d.label === "medium" ? "amber" : "green"}>{d.label}</Badge>
        </div>
        <div className="min-w-0 flex-1 space-y-2.5">
          {Object.entries((d.components ?? {}) as Record<string, number>).map(([k, v]) => {
            const max = COMPONENT_MAX[k] ?? 100;
            return (
              <div key={k} title={COMPONENT_HELP[k]}>
                <div className="mb-1 flex justify-between text-xs text-slate-600 dark:text-slate-300">
                  <span>{titleCase(k)}</span><span className="tabular-nums">{v} / {max}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                  <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.min(100, (v / max) * 100)}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        {d.method} Not comparable to link-based difficulty scores from other tools. Inputs: {inputs.results_considered} results considered, {inputs.authority_domains} on authority domains, {inputs.homepage_results} homepages, {inputs.titles_matching_keyword} titles matching the keyword, average word count {inputs.avg_word_count ?? "n/a"}.
      </p>
    </Card>
  );
}

export default function Serp() {
  const providers = useQuery({ queryKey: ["serp-providers"], queryFn: () => api.get("/serp/providers") });
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("us");
  const [lang, setLang] = useState("en");
  const [myUrl, setMyUrl] = useState("");
  const [urlText, setUrlText] = useState("");

  const urls = parseLines(urlText);
  const configured: string | undefined = providers.data?.configured;
  const hasProvider = !!configured && configured !== "none";
  const analyze = useMutation({
    mutationFn: () => api.post("/serp/analyze", { keyword: keyword.trim(), country: country.trim().toLowerCase(), lang: lang.trim().toLowerCase(), urls, my_url: myUrl.trim() || null }),
  });
  const r = analyze.data;
  const canSubmit = !!keyword.trim() && urls.length <= 20 && (hasProvider || urls.length > 0);
  const submit = (e: FormEvent) => { e.preventDefault(); if (canSubmit) analyze.mutate(); };

  const resultColumns: Column<any>[] = [
    { key: "pos", header: "#", align: "right", width: "40px", render: (x) => x.position },
    { key: "page", header: "Ergebnis", render: (x) => (
      <div className="max-w-md">
        <div className="font-medium text-slate-900 dark:text-slate-100">{x.title || <span className="font-normal text-slate-400">Kein Title vorhanden</span>}</div>
        <Url href={x.url} className="text-xs" />
        <div className="mt-1 flex flex-wrap gap-1">
          {x.is_homepage && <Badge tone="blue">Startseite</Badge>}
          {x.error && <Badge tone="red" title={x.error}>fetch failed: {x.error}</Badge>}
        </div>
      </div>
    ) },
    { key: "words", header: "Wörter", align: "right", render: (x) => fmtInt(x.word_count) },
    { key: "tl", header: "Title-Länge", align: "right", render: (x) => (x.title ? x.title_length : "–") },
    { key: "h2", header: "H2s", align: "right", render: (x) => (x.fetched ? x.h2_count : "–") },
    { key: "schema", header: "Schema-Typen", render: (x) => (x.schema_types ?? []).length
      ? <span className="flex max-w-xs flex-wrap gap-1">{x.schema_types.map((t: string) => <Chip key={t}>{t}</Chip>)}</span> : <span className="text-slate-400">–</span> },
  ];

  const summary = r?.summary ?? {};
  const gaps = r?.content_gaps;
  const schemaCounts = Object.entries((summary.schema_types ?? {}) as Record<string, number>);
  const resultTypes = Object.entries((r?.result_types ?? {}) as Record<string, number>);

  return (
    <div>
      <PageHeader title="SERP-Analyse"
        description="Was die rankenden Seiten eines Keywords gemeinsam haben: Länge, Überschriften, Begriffe, Fragen und strukturierte Daten. Die Seiten werden von diesem Tool geladen und gemessen; Suchmaschinen werden nie gescrapt." />

      <div className="space-y-4">
        {providers.isLoading ? <Card><Spinner label="SERP-Anbieter wird geprüft…" /></Card> : providers.error ? <ErrorBox error={providers.error} onRetry={() => providers.refetch()} /> : hasProvider ? (
          <Notice tone="success">SERP-Anbieter: <span className="font-medium">{providers.data.providers?.[configured!] ?? configured}</span>. URL-Feld leer lassen, um ihn abzufragen, oder URLs einfügen, um ihn zu übergehen.</Notice>
        ) : (
          <Notice tone="warn">
            Kein SERP-Anbieter eingerichtet, daher die rankenden URLs unten von Hand einfügen. Für automatische Ergebnisse SearXNG, Google Programmable Search oder Brave Search in den <Link to="/settings" className="font-medium underline">Einstellungen</Link> ergänzen.
          </Notice>
        )}

        <Card title="Keyword analysieren">
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-12">
              <Field label="Keyword" className="sm:col-span-2 lg:col-span-5">
                <Input required maxLength={200} value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="z. B. küche planen" />
              </Field>
              <Field label="Land" hint="2-stelliger Code" className="lg:col-span-2">
                <Input required pattern="[A-Za-z]{2}" maxLength={2} value={country} onChange={(e) => setCountry(e.target.value)} />
              </Field>
              <Field label="Sprache" hint="2-stelliger Code" className="lg:col-span-2">
                <Input required pattern="[A-Za-z]{2}" maxLength={2} value={lang} onChange={(e) => setLang(e.target.value)} />
              </Field>
              <Field label="Meine URL (optional)" hint="Ergänzt einen Inhaltslücken-Vergleich" className="sm:col-span-2 lg:col-span-3">
                <Input type="url" maxLength={2048} value={myUrl} onChange={(e) => setMyUrl(e.target.value)} placeholder="https://example.de/…" />
              </Field>
            </div>
            <Field label={hasProvider ? "Ergebnis-URLs (optional, übergeht den Anbieter)" : "Ergebnis-URLs, eine pro Zeile, in Ranking-Reihenfolge"}
              hint={`${urls.length} / 20 URLs. Die Positionen folgen deiner Reihenfolge.`}>
              <Textarea rows={5} value={urlText} onChange={(e) => setUrlText(e.target.value)} placeholder={"https://erstes-ergebnis.de/seite\nhttps://zweites-ergebnis.de/ratgeber"} className="font-mono text-xs" />
            </Field>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" variant="primary" icon={<Search className="h-4 w-4" />} loading={analyze.isPending} disabled={!canSubmit}>SERP analysieren</Button>
              {urls.length > 20 && <span className="text-xs text-red-600 dark:text-red-400">Höchstens 20 URLs.</span>}
              {!hasProvider && !urls.length && !providers.isLoading && <span className="text-xs text-slate-500 dark:text-slate-400">Mindestens eine Ergebnis-URL einfügen.</span>}
            </div>
          </form>
        </Card>

        {analyze.isPending && <Card><Spinner label="Rankende Seiten werden geladen und analysiert…" /></Card>}
        {analyze.error && <ErrorBox error={analyze.error} onRetry={() => analyze.mutate()} />}
        {!r && !analyze.isPending && !analyze.error && (
          <Card><EmptyState icon={<Search className="h-6 w-6" />} title="Noch keine Analyse" description="Keyword eingeben, um die rankenden Seiten zu analysieren." /></Card>
        )}

        {r && !analyze.isPending && (
          <>
            {r.source && <Notice><span className="font-medium">Source: {r.source.provider}.</span> {r.source.note}</Notice>}

            <div className="grid gap-4 lg:grid-cols-2">
              <Card title="Suchintention & SERP-Features">
                <div className="space-y-4 text-sm">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={INTENT_TONE[r.intent?.intent] ?? "gray"}>{r.intent?.intent}</Badge>
                      <DataBadge kind="estimated" />
                      <span className="text-xs text-slate-500 dark:text-slate-400">confidence {fmtPct(r.intent?.confidence, 0)} · {r.intent?.method}</span>
                    </div>
                    {(r.intent?.signals ?? []).length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-1 text-xs text-slate-500 dark:text-slate-400">Signals: {r.intent.signals.map((s: string) => <Chip key={s}>{s}</Chip>)}</div>
                    )}
                  </div>
                  <div>
                    <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Gemeldete SERP-Features</div>
                    {(r.features ?? []).length ? <div className="flex flex-wrap gap-1">{r.features.map((f: string) => <Badge key={f} tone="purple">{f}</Badge>)}</div>
                      : <span className="text-slate-500 dark:text-slate-400">Keine gemeldet</span>}
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{r.feature_note}</p>
                  </div>
                  <div>
                    <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Ergebnistypen</div>
                    {resultTypes.length ? <div className="flex flex-wrap gap-1">{resultTypes.map(([k, v]) => <Chip key={k} title="Aus URL-Pfaden abgeleitet">{k} <span className="font-semibold tabular-nums">{v}</span></Chip>)}</div>
                      : <span className="text-slate-500 dark:text-slate-400">Keine Ergebnisse</span>}
                  </div>
                </div>
              </Card>
              <Difficulty d={r.difficulty} />
            </div>

            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Analysierte Seiten" value={fmtInt(summary.pages_analysed)} hint={<span className="inline-flex items-center gap-1">von diesem Tool geladen <DataBadge kind="measured" /></span>} />
              <Stat label="Ø Wortzahl" value={fmtInt(summary.avg_word_count)} />
              <Stat label="Median Wortzahl" value={fmtInt(summary.median_word_count)} />
              <Stat label="Ø Title-Länge" value={summary.avg_title_length ? `${summary.avg_title_length} Zeichen` : "–"} />
            </div>

            {gaps ? (
              <Card title="Inhaltslücken deiner Seite" description={<Url href={myUrl.trim()} />}>
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Wortzahl im Vergleich</div>
                    <div className="text-sm text-slate-700 dark:text-slate-300">
                      Deine Seite: <span className="font-semibold tabular-nums">{fmtInt(gaps.word_count)}</span> Wörter · Median Wettbewerb: <span className="font-semibold tabular-nums">{fmtInt(gaps.median_competitor_words)}</span>
                      {gaps.word_count !== null && gaps.median_competitor_words ? (
                        <Badge tone={gaps.word_count >= gaps.median_competitor_words * 0.8 ? "green" : "amber"}>
                          {Math.round((gaps.word_count / gaps.median_competitor_words) * 100)}% des Medians
                        </Badge>
                      ) : null}
                    </div>
                    <div className="mb-1 mt-4 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Schema-Typen, die 2+ Wettbewerber nutzen und dir fehlen</div>
                    {(gaps.missing_schema_types ?? []).length ? <div className="flex flex-wrap gap-1">{gaps.missing_schema_types.map((t: string) => <Badge key={t} tone="amber">{t}</Badge>)}</div>
                      : <span className="text-sm text-slate-500 dark:text-slate-400">Keine</span>}
                  </div>
                  <div>
                    <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Begriffe bei 40 %+ der Wettbewerber, die deiner Seite fehlen</div>
                    {(gaps.missing_terms ?? []).length ? <div className="flex flex-wrap gap-1">{gaps.missing_terms.map((t: any) => <Chip key={t.term} title={`${t.documents} pages`}>{t.term} <span className="text-slate-400">{fmtPct(t.share, 0)}</span></Chip>)}</div>
                      : <span className="text-sm text-slate-500 dark:text-slate-400">Keine</span>}
                    <div className="mb-1 mt-4 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Überschriften-Themen, die bei dir fehlen</div>
                    {(gaps.missing_heading_topics ?? []).length ? <div className="flex flex-wrap gap-1">{gaps.missing_heading_topics.map((t: any) => <Chip key={t.term} title={`${t.documents} pages`}>{t.term} <span className="text-slate-400">{fmtPct(t.share, 0)}</span></Chip>)}</div>
                      : <span className="text-sm text-slate-500 dark:text-slate-400">Keine</span>}
                  </div>
                </div>
              </Card>
            ) : myUrl.trim() ? (
              <Notice tone="warn">Deine URL ließ sich nicht als HTML-Seite laden, daher kein Lückenvergleich.</Notice>
            ) : null}

            <Card padded={false} title={`Ergebnisse (${(r.results ?? []).length})`} description="Wortzahl, Überschriften und Schema werden je geladener Seite gemessen.">
              <DataTable columns={resultColumns} rows={r.results ?? []} rowKey={(x) => `${x.position}-${x.url}`}
                empty={<EmptyState title="Keine Ergebnisse" description="Der Anbieter lieferte für dieses Keyword nichts." />} />
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card padded={false} title="Überschriften-Themen" description="Begriffe, die in den H2/H3 rankender Seiten wiederkehren">
                <DataTable dense columns={termColumns} rows={r.heading_topics ?? []} rowKey={(t) => t.term}
                  empty={<EmptyState title="Keine wiederkehrenden Themen" description="Zu wenige Seiten geladen, um gemeinsame Themen zu finden." />} />
              </Card>
              <Card padded={false} title="Häufige Begriffe" description="Begriffe, die im Text rankender Seiten wiederkehren">
                <div className="max-h-[28rem] overflow-y-auto">
                  <DataTable dense columns={termColumns} rows={r.common_terms ?? []} rowKey={(t) => t.term}
                    empty={<EmptyState title="Keine wiederkehrenden Begriffe" description="Zu wenige Seiten geladen, um gemeinsame Begriffe zu finden." />} />
                </div>
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card title="Fragen der rankenden Seiten" description="Überschriften in Frageform">
                {(r.questions ?? []).length ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">{r.questions.map((q: string) => <li key={q}>{q}</li>)}</ul>
                ) : <p className="text-sm text-slate-500 dark:text-slate-400">Auf den analysierten Seiten gibt es keine Frage-Überschriften.</p>}
              </Card>
              <Card title="Titles & strukturierte Daten">
                <div className="space-y-4">
                  <div>
                    <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Gemeinsame Begriffe in den Titles</div>
                    {(summary.common_title_terms ?? []).length ? <div className="flex flex-wrap gap-1">{summary.common_title_terms.map((t: any) => <Chip key={t.term}>{t.term} <span className="font-semibold tabular-nums">{t.results}</span></Chip>)}</div>
                      : <span className="text-sm text-slate-500 dark:text-slate-400">Keine gemeinsamen Begriffe</span>}
                  </div>
                  <div>
                    <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Schema-Typen der rankenden Seiten</div>
                    {schemaCounts.length ? <div className="flex flex-wrap gap-1">{schemaCounts.map(([t, c]) => <Chip key={t}>{t} <span className="font-semibold tabular-nums">{c}</span></Chip>)}</div>
                      : <span className="text-sm text-slate-500 dark:text-slate-400">Keine strukturierten Daten gefunden</span>}
                  </div>
                </div>
              </Card>
            </div>

            <AiBrief key={r.keyword} keyword={r.keyword} serp={r} />
          </>
        )}
      </div>
    </div>
  );
}
