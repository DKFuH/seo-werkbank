import { useMutation } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { type FormEvent, useState } from "react";
import {
  Badge, Button, Card, type Column, DataTable, EmptyState, ErrorBox, Field, Input, Notice, PageHeader, ScoreRing, Spinner, Stat,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtInt } from "../lib/format";

const TONE: Record<string, string> = { pass: "green", warn: "amber", fail: "red", info: "gray" };
const LABEL: Record<string, string> = { pass: "ok", warn: "prüfen", fail: "Problem", info: "Info" };
const GROUPS = ["Zugang", "Entität", "Struktur", "Belege"];

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
        description="Prüft, ob eine Seite von KI-Suchsystemen (ChatGPT, Claude, Perplexity, Gemini, Copilot) abgerufen, verstanden und zitiert werden kann: Crawler-Zugang, llms.txt, Entität, Antwortstruktur und Belege." />
      <div className="space-y-4">
        <Card title="Seite prüfen">
          <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Field label="URL" className="flex-1">
              <Input type="url" required maxLength={2048} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.de/ratgeber/…" />
            </Field>
            <Button type="submit" variant="primary" icon={<Bot className="h-4 w-4" />} loading={run.isPending}>Prüfen</Button>
          </form>
        </Card>

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
