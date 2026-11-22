import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, CircleX, FileText, Gauge } from "lucide-react";
import { type ReactNode, useMemo, useState } from "react";
import {
  Badge, Button, Card, Checkbox, type Column, DataBadge, DataTable, EmptyState, ErrorBox, Field, Input, KeyValue, Notice, PageHeader, ScoreRing, Spinner, Textarea, Url,
} from "../components/ui";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtPct, shortUrl } from "../lib/format";

const INTENT_TONE: Record<string, string> = { transactional: "green", commercial: "purple", navigational: "blue", local: "orange", informational: "gray" };

function parseLines(text: string): string[] {
  return Array.from(new Set(text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)));
}

function countWords(text: string): number {
  const plain = text.replace(/<[^>]*>/g, " ");
  return (plain.match(/[\p{L}\p{N}][\p{L}\p{N}'’-]*/gu) ?? []).length;
}

function Chip({ children, tone, title }: { children: ReactNode; tone?: "good" | "bad"; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs ${
      tone === "good" ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
      : tone === "bad" ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
      : "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"}`}>{children}</span>
  );
}

const STATUS_META: Record<string, { label: string; icon: ReactNode }> = {
  fail: { label: "Nicht erfüllt", icon: <CircleX className="h-4 w-4 text-red-600 dark:text-red-400" /> },
  warn: { label: "Prüfen", icon: <CircleAlert className="h-4 w-4 text-amber-600 dark:text-amber-400" /> },
  pass: { label: "Erfüllt", icon: <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> },
};

function CheckGroup({ status, checks }: { status: string; checks: any[] }) {
  const [open, setOpen] = useState(status !== "pass");
  if (!checks.length) return null;
  const meta = STATUS_META[status];
  return (
    <div>
      <button className="flex w-full items-center justify-between gap-2 py-1.5 text-left" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">{meta.icon}{meta.label}
          <span className="rounded-full bg-slate-100 px-1.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">{checks.length}</span></span>
        <span className="text-xs text-slate-500 dark:text-slate-400">{open ? "Ausblenden" : "Anzeigen"}</span>
      </button>
      {open && (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {checks.map((c) => (
            <li key={c.id} className="py-2 pl-6">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{c.label}</span>
                <span className="text-xs text-slate-400" title="Gewicht dieser Prüfung im Score">Gewicht {c.weight}</span>
              </div>
              <div className="break-words text-xs text-slate-500 dark:text-slate-400">{c.detail}</div>
              {c.recommendation && <div className="mt-1 text-xs text-slate-700 dark:text-slate-300"><span className="font-medium">Lösung:</span> {c.recommendation}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Content() {
  const { site } = useSite();
  const [keyword, setKeyword] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [secondary, setSecondary] = useState("");
  const [content, setContent] = useState("");
  const [loadUrl, setLoadUrl] = useState("");
  const [competitorText, setCompetitorText] = useState("");
  const [useSerp, setUseSerp] = useState(false);
  const [suggestQuestions, setSuggestQuestions] = useState(false);
  const [useSitePages, setUseSitePages] = useState(true);
  const [termFilter, setTermFilter] = useState<"all" | "missing">("missing");

  const words = useMemo(() => countWords(content), [content]);
  const competitorUrls = parseLines(competitorText);
  const secondaryList = secondary.split(",").map((s) => s.trim()).filter(Boolean);

  const fetchPage = useMutation({
    mutationFn: () => api.post("/content/fetch", { url: loadUrl.trim() }),
    onSuccess: (d) => {
      setTitle(d.title ?? "");
      setDescription(d.meta_description ?? "");
      setContent(d.content ?? "");
      setUrl(d.url ?? loadUrl.trim());
    },
  });
  const analyze = useMutation({
    mutationFn: () => api.post("/content/analyze", {
      content, keyword: keyword.trim(), title: title.trim() || null, meta_description: description.trim() || null, url: url.trim() || null,
      secondary_keywords: secondaryList, competitor_urls: competitorUrls, use_serp: useSerp, suggest_questions: suggestQuestions,
      site_id: site && useSitePages ? site.id : null,
    }),
  });

  const r = analyze.data;
  const checks: any[] = r?.checks ?? [];
  const read = r?.readability;
  const terms: any[] = r?.semantic_terms ?? [];
  const shownTerms = termFilter === "missing" ? terms.filter((t) => t.status === "missing") : terms;
  const topics: any[] = r?.topic_coverage?.topics ?? [];
  const tooMany = secondaryList.length > 30 || competitorUrls.length > 10;
  const canAnalyze = !!keyword.trim() && !!content.trim() && !tooMany;

  const termColumns: Column<any>[] = [
    { key: "term", header: "Begriff", render: (t) => <span className="font-medium text-slate-900 dark:text-slate-100">{t.term}</span> },
    { key: "share", header: "Bei Wettbewerbern", align: "right", render: (t) => `${fmtPct(t.share, 0)} (${t.documents})` },
    { key: "avg", header: "Ø Nennungen", align: "right", render: (t) => t.avg_count },
    { key: "used", header: "In deinem Entwurf", align: "right", render: (t) => (t.used ? <Badge tone="green">{t.used}× genutzt</Badge> : <Badge tone="amber">fehlt</Badge>) },
  ];

  return (
    <div>
      <PageHeader title="Content-Optimierung"
        description="Bewertet einen Entwurf nach Onpage-Regeln und optional gegen die Seiten, die bereits ranken. Die Scores sind Heuristiken und sagen keine Rankings voraus." />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* ------------------------------------------------------ editor */}
        <div className="min-w-0 space-y-4">
          <Card title="Entwurf">
            <div className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <Field label="Bestehende Seite laden (optional)" className="flex-1">
                  <Input type="url" value={loadUrl} onChange={(e) => setLoadUrl(e.target.value)} placeholder="https://example.de/ratgeber/…" />
                </Field>
                <Button loading={fetchPage.isPending} disabled={!loadUrl.trim()} onClick={() => fetchPage.mutate()}>Von URL laden</Button>
              </div>
              {fetchPage.error && <ErrorBox error={fetchPage.error} />}
              {fetchPage.data && !fetchPage.isPending && <Notice tone="success">{fmtInt(fetchPage.data.word_count)} Wörter geladen von <span className="break-all">{fetchPage.data.url}</span>. Title, Description und Inhalt wurden übernommen.</Notice>}

              <Field label="Ziel-Keyword">
                <Input required maxLength={200} value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="z. B. küche planen" />
              </Field>
              <Field label="Title" hint={`${title.length} Zeichen (Ziel 30–60)`}>
                <Input maxLength={500} value={title} onChange={(e) => setTitle(e.target.value)} />
              </Field>
              <Field label="Meta-Description" hint={`${description.length} Zeichen (Ziel 70–160)`}>
                <Textarea rows={2} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} />
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="URL (optional)">
                  <Input maxLength={2048} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.de/ratgeber/kueche-planen/" />
                </Field>
                <Field label="Neben-Keywords" hint={`Kommagetrennt${secondaryList.length ? ` · ${secondaryList.length} / 30` : ""}`}>
                  <Input value={secondary} onChange={(e) => setSecondary(e.target.value)} placeholder="küchenplanung, küchenmaße" />
                </Field>
              </div>
              <Field label="Inhalt (Markdown, HTML oder Klartext)">
                <Textarea rows={18} maxLength={400000} value={content} onChange={(e) => setContent(e.target.value)} className="font-mono text-xs"
                  placeholder={"# Überschrift\n\nEntwurf hier schreiben oder einfügen…"} />
              </Field>
              <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span><span className="font-semibold tabular-nums text-slate-700 dark:text-slate-200">{fmtInt(words)}</span> words · {fmtInt(content.length)} characters</span>
                {r?.target_word_count ? <span>Competitor median: {fmtInt(r.target_word_count)} words</span> : null}
              </div>
            </div>
          </Card>

          <Card title="Mit rankenden Seiten vergleichen" description="Optional. Aktiviert Vorschläge zu verwandten Begriffen, Themenabdeckung und FAQ.">
            <div className="space-y-3">
              <Field label="Wettbewerber-URLs, eine pro Zeile" hint={`${competitorUrls.length} / 10 URLs. Die Seiten werden von diesem Tool abgerufen und gemessen.`}>
                <Textarea rows={4} value={competitorText} onChange={(e) => setCompetitorText(e.target.value)} className="font-mono text-xs" placeholder="https://wettbewerber.de/ratgeber" />
              </Field>
              <Checkbox label="SERP-Anbieter für Wettbewerber nutzen" checked={useSerp} onChange={setUseSerp} hint="Nur ohne eingefügte URLs. Braucht einen SERP-Anbieter in den Einstellungen." />
              <Checkbox label="Fragen aus Autocomplete vorschlagen" checked={suggestQuestions} onChange={setSuggestQuestions} hint="Ergänzt echte Frage-Vervollständigungen als FAQ-Ideen." />
              <Checkbox label="Eigene Seiten für interne Linkideen nutzen" checked={!!site && useSitePages} onChange={setUseSitePages}
                hint={site ? `Nutzt den letzten Crawl von ${site.name}.` : "Website anlegen und crawlen, um das zu aktivieren."} />
            </div>
          </Card>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary" icon={<Gauge className="h-4 w-4" />} loading={analyze.isPending} disabled={!canAnalyze} onClick={() => analyze.mutate()}>Inhalt analysieren</Button>
            {!canAnalyze && !tooMany && <span className="text-xs text-slate-500 dark:text-slate-400">Ziel-Keyword und Inhalt eingeben.</span>}
            {tooMany && <span className="text-xs text-red-600 dark:text-red-400">Höchstens 30 Neben-Keywords und 10 Wettbewerber-URLs.</span>}
          </div>
        </div>

        {/* ------------------------------------------------------ results */}
        <div className="min-w-0 space-y-4">
          {analyze.isPending ? <Card><Spinner label={competitorUrls.length || useSerp ? "Wettbewerberseiten werden geladen und analysiert…" : "Wird analysiert…"} /></Card>
            : analyze.error ? <ErrorBox error={analyze.error} onRetry={() => analyze.mutate()} />
            : !r ? <Card><EmptyState icon={<FileText className="h-6 w-6" />} title="Noch keine Analyse" description="Keyword und Inhalt eintragen und auf Inhalt analysieren klicken. Nach jeder Änderung erneut ausführen." /></Card>
            : (
              <>
                <Card>
                  <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
                    <ScoreRing score={r.score} size={112} />
                    <div className="min-w-0 flex-1 space-y-2 text-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-slate-900 dark:text-slate-100">Content-Score</span>
                        <DataBadge kind="estimated" />
                        <Badge>{r.format}</Badge>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-slate-600 dark:text-slate-300">
                        Intent: <Badge tone={INTENT_TONE[r.intent?.intent] ?? "gray"}>{r.intent?.intent}</Badge>
                        <span className="text-xs text-slate-500 dark:text-slate-400">estimate, confidence {fmtPct(r.intent?.confidence, 0)}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600 sm:grid-cols-3 dark:text-slate-300">
                        <span>Wörter: <b className="tabular-nums">{fmtInt(r.word_count)}</b></span>
                        <span>Ziel: <b className="tabular-nums">{r.target_word_count ? fmtInt(r.target_word_count) : "n/a"}</b></span>
                        <span>Exakte Phrase: <b className="tabular-nums">{r.keyword_occurrences}×</b></span>
                        <span>Dichte: <b className="tabular-nums">{r.keyword_density}%</b></span>
                        <span>Wettbewerber: <b className="tabular-nums">{r.competitors_used}</b></span>
                        <span>Prüfungen: <b className="tabular-nums">{checks.filter((c) => c.status === "pass").length}/{checks.length}</b> erfüllt</span>
                      </div>
                    </div>
                  </div>
                </Card>

                {(r.notes ?? []).length > 0 && (
                  <Notice><ul className="list-disc space-y-0.5 pl-5">{r.notes.map((n: string) => <li key={n}>{n}</li>)}</ul></Notice>
                )}

                <Card title="Prüfungen">
                  <div className="space-y-2">
                    {["fail", "warn", "pass"].map((s) => <CheckGroup key={`${s}-${analyze.submittedAt}`} status={s} checks={checks.filter((c) => c.status === s)} />)}
                  </div>
                </Card>

                <Card title="Lesbarkeit" description="Flesch-Formeln, auf englische Texte geeicht – für deutsche Texte nur grob">
                  {read?.flesch_reading_ease === null || read?.flesch_reading_ease === undefined ? (
                    <p className="text-sm text-slate-500 dark:text-slate-400">Zu wenig Text, um die Lesbarkeit zu messen.</p>
                  ) : (
                    <KeyValue items={[
                      ["Lesbarkeitsindex", <span key="e">{read.flesch_reading_ease} <Badge tone={read.flesch_reading_ease >= 50 ? "green" : read.flesch_reading_ease >= 30 ? "amber" : "red"}>{read.label}</Badge></span>],
                      ["Klassenstufe", read.flesch_kincaid_grade],
                      ["Sätze", fmtInt(read.sentences)],
                      ["Ø Satzlänge", `${read.avg_sentence_length} Wörter`],
                      ["Sätze über 25 Wörter", fmtPct(read.long_sentence_share, 0)],
                    ]} />
                  )}
                </Card>

                <Card padded={false} title="Verwandte Begriffe der rankenden Seiten"
                  actions={terms.length ? (
                    <span className="inline-flex gap-1">
                      {(["missing", "all"] as const).map((f) => (
                        <button key={f} onClick={() => setTermFilter(f)} aria-pressed={termFilter === f}
                          className={`rounded-md px-2 py-1 text-xs font-medium ${termFilter === f ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}>
                          {f === "missing" ? `Fehlend (${terms.filter((t) => t.status === "missing").length})` : `Alle (${terms.length})`}
                        </button>
                      ))}
                    </span>
                  ) : undefined}>
                  {terms.length ? (
                    <div className="max-h-96 overflow-y-auto">
                      <DataTable dense columns={termColumns} rows={shownTerms} rowKey={(t) => t.term}
                        empty={<EmptyState title="Nichts fehlt" description="Dein Entwurf nutzt alle wiederkehrenden Begriffe der Wettbewerberseiten." />} />
                    </div>
                  ) : <EmptyState title="Keine Wettbewerberdaten" description="Wettbewerber-URLs einfügen oder den SERP-Anbieter aktivieren, um die Begriffe rankender Seiten zu sehen." />}
                </Card>

                {r.wdf_idf?.terms?.length > 0 && (
                  <Card padded={false} title="WDF*IDF des Entwurfs"
                    description="Termgewichtung deines Entwurfs gegen dieselben Wettbewerberseiten. Vergleichswerte, keine Zielvorgaben."
                    actions={<Link to="/wdf-idf" className="text-xs font-medium text-brand-700 hover:underline dark:text-brand-300">Vollansicht mit Kurve</Link>}>
                    <div className="max-h-96 overflow-y-auto">
                      <DataTable dense rows={r.wdf_idf.terms} rowKey={(t: any) => t.term} columns={[
                        { key: "term", header: "Begriff", render: (t: any) => <span className="font-medium">{t.term}{t.is_keyword && <> <Badge tone="blue">Keyword</Badge></>}</span> },
                        { key: "own", header: "Entwurf", align: "right", render: (t: any) => <span className="tabular-nums">{t.own?.toFixed(3)} <span className="text-slate-400">({t.own_count})</span></span> },
                        { key: "mean", header: "Ø Wettbewerb", align: "right", render: (t: any) => <span className="tabular-nums">{t.competitor_mean.toFixed(3)}</span> },
                        { key: "max", header: "Max", align: "right", render: (t: any) => <span className="tabular-nums">{t.competitor_max.toFixed(3)}</span> },
                        { key: "status", header: "Bewertung", render: (t: any) => <Badge tone={({ "fehlt": "red", "deutlich unter Schnitt": "amber", "über Maximum": "purple", "im Rahmen": "green" } as Record<string, string>)[t.status] ?? "gray"}>{t.status}</Badge> },
                      ]} />
                    </div>
                  </Card>
                )}

                <Card title="Themenabdeckung" description={r.topic_coverage?.covered_share !== null && r.topic_coverage?.covered_share !== undefined
                  ? `Deckt ${fmtPct(r.topic_coverage.covered_share, 0)} der Zwischenüberschrift-Themen der Wettbewerber ab` : "Themen aus Zwischenüberschriften der Wettbewerber"}>
                  {topics.length ? (
                    <div className="flex flex-wrap gap-1.5">
                      {topics.map((t) => <Chip key={t.term} tone={t.covered ? "good" : "bad"} title={`${t.documents} Wettbewerberseite(n), ${t.covered ? "abgedeckt" : "nicht abgedeckt"}`}>{t.term} <span className="opacity-70">{fmtPct(t.share, 0)}</span></Chip>)}
                    </div>
                  ) : <p className="text-sm text-slate-500 dark:text-slate-400">{r.competitors_used ? "Auf den Wettbewerberseiten wurden keine wiederkehrenden Themen gefunden." : "Braucht Wettbewerberseiten."}</p>}
                  {topics.length > 0 && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Grün: im Entwurf abgedeckt. Gelb: nicht abgedeckt.</p>}
                </Card>

                <Card title="FAQ-Vorschläge" description="Fragen aus Autocomplete und Wettbewerber-Überschriften, die dein Entwurf noch nicht beantwortet">
                  {(r.faq_suggestions ?? []).length ? (
                    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">{r.faq_suggestions.map((q: string) => <li key={q}>{q}</li>)}</ul>
                  ) : <p className="text-sm text-slate-500 dark:text-slate-400">Keine Vorschläge. Autocomplete-Fragen aktivieren oder Wettbewerber-URLs ergänzen.</p>}
                </Card>

                <div className="grid gap-4 xl:grid-cols-2">
                  <Card title="Schema-Empfehlungen">
                    {(r.schema_recommendations ?? []).length ? (
                      <ul className="space-y-2 text-sm">
                        {r.schema_recommendations.map((s: any) => (
                          <li key={s.type}><Badge tone="purple">{s.type}</Badge> <span className="text-slate-600 dark:text-slate-300">{s.reason}</span></li>
                        ))}
                      </ul>
                    ) : <p className="text-sm text-slate-500 dark:text-slate-400">Für diesen Entwurf drängt sich kein Schema-Typ auf.</p>}
                  </Card>
                  <Card title="Vorschläge für interne Links">
                    {(r.internal_link_suggestions ?? []).length ? (
                      <ul className="space-y-2 text-sm">
                        {r.internal_link_suggestions.map((l: any) => (
                          <li key={l.url}>
                            <Url href={l.url} label={shortUrl(l.url, site?.url)} />
                            <div className="text-xs text-slate-500 dark:text-slate-400">{l.title ? `${l.title} · ` : ""}{l.reason}</div>
                          </li>
                        ))}
                      </ul>
                    ) : <p className="text-sm text-slate-500 dark:text-slate-400">{site && useSitePages ? "Keine gecrawlte Seite passt zu Themen des Entwurfs (oder es gibt noch keinen abgeschlossenen Crawl)." : "Website wählen und die Option für interne Links aktivieren, um Ideen aus deinen gecrawlten Seiten zu bekommen."}</p>}
                  </Card>
                </div>

                <Card title={`Genutzte Wettbewerber (${(r.competitors ?? []).length})`}>
                  {(r.competitors ?? []).length ? (
                    <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
                      {r.competitors.map((c: any) => (
                        <li key={c.url} className="flex flex-wrap items-baseline justify-between gap-x-3 py-1.5">
                          <span className="min-w-0"><span className="text-slate-800 dark:text-slate-200">{c.title || "Ohne Titel"}</span><br /><Url href={c.url} className="text-xs" /></span>
                          <span className="text-xs tabular-nums text-slate-500 dark:text-slate-400">{fmtInt(c.word_count)} words</span>
                        </li>
                      ))}
                    </ul>
                  ) : <p className="text-sm text-slate-500 dark:text-slate-400">Es wurden keine Wettbewerberseiten analysiert.</p>}
                </Card>
              </>
            )}
        </div>
      </div>
    </div>
  );
}
