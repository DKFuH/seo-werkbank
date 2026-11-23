import { useMutation } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { type FormEvent, useState } from "react";
import {
  Badge, Button, Card, type Column, DataTable, EmptyState, ErrorBox, Field, Input, Notice, PageHeader, ScoreRing, Spinner, Stat, Textarea,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt } from "../lib/format";

const TONE: Record<string, string> = { pass: "green", warn: "amber", fail: "red", info: "gray" };
const LABEL: Record<string, string> = { pass: "ok", warn: "prüfen", fail: "Problem", info: "Info" };
const GROUPS = ["Zugang", "Integrität", "Entität", "Struktur", "Belege"];

const VERDICT: Record<string, [string, string]> = {
  ok: ["green", "kommt durch"], blocked: ["red", "gesperrt"], challenge: ["red", "Prüfseite"],
  different: ["amber", "abweichend"], error: ["gray", "Fehler"],
};

/** Requests the own site with a browser and with each AI crawler's user agent: does a CDN/WAF block the bots? */
function BotAccessCard() {
  const { site } = useSite();
  const [url, setUrl] = useState("");
  const run = useMutation({ mutationFn: () => api.post(`/sites/${site!.id}/geo/bot-access`, url.trim() ? { url: url.trim() } : {}) });
  const d = run.data;
  const columns: Column<any>[] = [
    { key: "agent", header: "Crawler", render: (b) => <span className="font-medium">{b.agent}</span> },
    { key: "op", header: "Anbieter", render: (b) => b.operator },
    { key: "verdict", header: "Ergebnis", render: (b) => <Badge tone={VERDICT[b.verdict]?.[0] ?? "gray"}>{VERDICT[b.verdict]?.[1] ?? b.verdict}</Badge> },
    { key: "reason", header: "Details", render: (b) => <span className="text-xs text-slate-500 dark:text-slate-400">{b.reason}</span> },
  ];
  if (!site) return null;
  return (
    <Card title="Sperrt das CDN KI-Crawler?" padded={false}
      description="robots.txt kann alles erlauben, während Cloudflare oder eine Firewall die Bots trotzdem abweist. Ruft eine Seite der ausgewählten Website mit Browser- und mit Bot-Kennung ab (12 Anfragen).">
      <div className="space-y-3 p-4">
        <form onSubmit={(e) => { e.preventDefault(); run.mutate(); }} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field label={`URL auf ${site.domain} (leer = Startseite)`} className="flex-1">
            <Input type="url" maxLength={2048} value={url} onChange={(e) => setUrl(e.target.value)} placeholder={site.url} />
          </Field>
          <Button type="submit" loading={run.isPending}>Bot-Zugang prüfen</Button>
        </form>
        {run.error && <ErrorBox error={run.error} />}
        {d && (
          d.blocked.length
            ? <Notice tone="warn">Abgewiesen: {d.blocked.join(", ")}. Browser bekommt HTTP {d.browser.status ?? "–"}.</Notice>
            : <Notice tone="success">Kein KI-Crawler abgewiesen. Browser bekommt HTTP {d.browser.status ?? "–"}.</Notice>
        )}
      </div>
      {d && <DataTable dense columns={columns} rows={d.items} rowKey={(b: any) => b.agent} />}
      {d && <p className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">{d.method}</p>}
    </Card>
  );
}

/** llms.txt draft from the last crawl of the selected site: shown for review, copied or downloaded. */
function LlmsDraftCard() {
  const { site } = useSite();
  const [copied, setCopied] = useState(false);
  const draft = useMutation({ mutationFn: () => api.get(`/sites/${site!.id}/geo/llms-txt-draft`) });
  const d = draft.data;
  if (!site) return null;
  const copy = async () => {
    try { await navigator.clipboard.writeText(d.text); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* clipboard blocked */ }
  };
  return (
    <Card title="llms.txt-Entwurf" description="Erzeugt aus den indexierbaren Seiten des letzten Crawls eine llms.txt nach llmstxt.org: Abschnitte nach Pfad, am besten verlinkte Seiten zuerst. Vor dem Hochladen prüfen und kürzen.">
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => draft.mutate()} loading={draft.isPending}>Entwurf erzeugen</Button>
          {d && <Button variant="ghost" onClick={copy}>{copied ? "Kopiert" : "Kopieren"}</Button>}
          {d && <Button variant="ghost" onClick={() => api.download(`/sites/${site.id}/geo/llms-txt-draft`, { download: true }, "llms.txt")}>Als Datei laden</Button>}
        </div>
        {draft.error && <ErrorBox error={draft.error} />}
        {d && (
          <>
            <p className="text-xs text-slate-500 dark:text-slate-400">{d.pages} Seiten in {d.sections.length} Abschnitten · Crawl #{d.crawl_id}</p>
            {d.summary_missing && <Notice tone="warn">Die Startseite hat keine Meta-Description. Die Zeile „&gt; Kurzbeschreibung“ fehlt deshalb und muss ergänzt werden.</Notice>}
            <Textarea readOnly rows={14} value={d.text} className="font-mono text-xs" aria-label="llms.txt-Entwurf" />
            <p className="text-xs text-slate-500 dark:text-slate-400">{d.method}</p>
          </>
        )}
      </div>
    </Card>
  );
}

export default function Geo() {
  const [url, setUrl] = useState("");
  const run = useMutation({ mutationFn: () => api.post("/geo/check", { url: url.trim() }) });
  const r = run.data;
  const submit = (e: FormEvent) => { e.preventDefault(); if (url.trim()) run.mutate(); };

  const crawlerColumns: Column<any>[] = [
    { key: "agent", header: "Crawler", render: (b) => <span className="font-medium">{b.agent}{b.search_critical && <Badge tone="blue">Suche</Badge>}</span> },
    { key: "op", header: "Anbieter", render: (b) => b.operator },
    { key: "purpose", header: "Zweck", render: (b) => b.purpose },
    { key: "allowed", header: "robots.txt", render: (b) => <Badge tone={b.allowed ? "green" : b.search_critical ? "red" : "amber"}>{b.allowed ? "erlaubt" : "gesperrt"}</Badge> },
  ];

  return (
    <div>
      <PageHeader title="GEO-Check"
        description="Prüft, ob eine Seite von KI-Suchsystemen (ChatGPT, Claude, Perplexity, Gemini, Copilot) abgerufen, verstanden und zitiert werden kann: Crawler-Zugang, Integrität, Entität, Antwortstruktur und Belege." />
      <div className="space-y-4">
        <Card title="Seite prüfen">
          <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Field label="URL" className="flex-1">
              <Input type="url" required maxLength={2048} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.de/ratgeber/…" />
            </Field>
            <Button type="submit" variant="primary" icon={<Bot className="h-4 w-4" />} loading={run.isPending}>Prüfen</Button>
          </form>
        </Card>

        <BotAccessCard />
        <LlmsDraftCard />

        {run.isPending && <Card><Spinner label="Seite, robots.txt und llms.txt werden geladen…" /></Card>}
        {run.error && <ErrorBox error={run.error} onRetry={() => run.mutate()} />}
        {!r && !run.isPending && !run.error && <Card><EmptyState icon={<Bot className="h-6 w-6" />} title="Noch keine Prüfung" description="URL eingeben und prüfen." /></Card>}

        {r && !run.isPending && (
          <>
            <div className="grid gap-4 lg:grid-cols-4">
              <Card className="flex flex-col items-center justify-center">
                <ScoreRing score={r.score} label="GEO" />
                <p className="mt-2 text-center text-xs text-slate-500">Checkliste, keine Prognose</p>
              </Card>
              <div className="grid grid-cols-2 gap-3 lg:col-span-3 lg:grid-cols-3">
                <Stat label="Wörter ohne JS" value={fmtInt(r.stats.words)} />
                <Stat label="Frage-Überschriften" value={fmtInt(r.stats.question_headings)} />
                <Stat label="Listen / Tabellen" value={`${r.stats.lists} / ${r.stats.tables}`} />
                <Stat label="Externe Quellen" value={fmtInt(r.stats.external_domains.length)} />
                <Stat label="sameAs-Profile" value={fmtInt(r.stats.same_as.length)} />
                <Stat label="Letzte Änderung" value={r.stats.newest_date ? r.stats.newest_date.slice(0, 10) : "–"} />
              </div>
            </div>

            {GROUPS.map((g) => {
              const items = (r.checks ?? []).filter((c: any) => c.group === g);
              if (!items.length) return null;
              return (
                <Card key={g} title={g}>
                  <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                    {items.map((c: any) => (
                      <li key={c.id} className="flex flex-col gap-1 py-2 sm:flex-row sm:items-start sm:gap-3">
                        <Badge tone={TONE[c.status]}>{LABEL[c.status] ?? c.status}</Badge>
                        <div className="min-w-0 flex-1 text-sm">
                          <div className="font-medium text-slate-900 dark:text-slate-100">{c.label}</div>
                          <div className="text-slate-600 dark:text-slate-300">{c.detail}</div>
                          {c.recommendation && <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{c.recommendation}</div>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card>
              );
            })}

            <Card padded={false} title="KI-Crawler laut robots.txt">
              <DataTable dense columns={crawlerColumns} rows={r.crawlers ?? []} rowKey={(b: any) => b.agent} />
            </Card>

            {(r.stats.schema_types ?? []).length > 0 && (
              <Card title="Gefundene Schema-Typen">
                <div className="flex flex-wrap gap-1">{r.stats.schema_types.map((t: string) => <Badge key={t}>{t}</Badge>)}</div>
              </Card>
            )}
            {(r.notes ?? []).map((n: string) => <Notice key={n}>{n}</Notice>)}
          </>
        )}
      </div>
    </div>
  );
}
