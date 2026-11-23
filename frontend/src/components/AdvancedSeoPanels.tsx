/* Checks from the former "Erweiterte SEO-Prüfungen" page. Each one now lives on the screen whose topic it belongs to:
   SERP overlap on SERP-Analyse, relaunch on Crawler, pagination on Interne Verlinkung, rich-result potential on
   Strukturierte Daten. Backend: /api/sites/{id}/advanced/... */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { CrawlSummary } from "../lib/context";
import { crawlName, fmtDateTime, fmtInt } from "../lib/format";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, Select, Spinner, Textarea } from "./ui";

type Overlap = { provider: string; result: { common_count: number; count_a: number;
  count_b: number; jaccard: number | null; overlap_of_smaller: number | null; common_urls: string[];
  interpretation: string }; method: string };
type Relaunch = { items: { old_url: string; intended_new_url: string; status: string }[];
  counts: Record<string, number>; method: string };
type Pagination = { crawl_id: number | null; items: { url: string; depth: number | null;
  inlinks: number; indexable: boolean; hints: string[] }[]; method: string };
type Schema = { crawl_id: number | null; items: { url: string; types: string[];
  potential_google_feature_types: string[]; other_schema_types: string[];
  google_eligibility_confirmed: boolean; validator_result: { errors: number; warnings: number; findings: { level: string; path: string; message: string }[] } }[]; method: string };

const root = (siteId: number) => "/sites/" + siteId + "/advanced";
const lines = (s: string) => s.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
const muted = "text-xs text-slate-500 dark:text-slate-400";

/** "alt => neu", "alt -> neu" or "alt → neu"; lines without a separator are ignored. */
export function parseMappings(text: string): { old_url: string; new_url: string }[] {
  return lines(text).flatMap((line) => {
    const parts = line.split(/\s*(?:=>|->|→)\s*/);
    return parts.length === 2 && parts[0] && parts[1] ? [{ old_url: parts[0], new_url: parts[1] }] : [];
  });
}

export function SerpOverlapCard({ siteId }: { siteId: number }) {
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [firstUrls, setFirstUrls] = useState("");
  const [secondUrls, setSecondUrls] = useState("");
  const serp = useMutation<Overlap>({ mutationFn: () => api.post(root(siteId) + "/serp-overlap", {
    first_keyword: first, second_keyword: second, country: "de", language: "de",
    manual_urls_first: lines(firstUrls), manual_urls_second: lines(secondUrls),
  }) });
  return (
    <Card title="Zwei Keywords vergleichen (SERP-Überschneidung)"
      description="Wie viele gleiche URLs ranken für beide Keywords? Viele gemeinsame URLs sprechen für eine Seite, wenige für getrennte Seiten.">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); serp.mutate(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Keyword A"><Input value={first} onChange={(e) => setFirst(e.target.value)} required /></Field>
          <Field label="Keyword B"><Input value={second} onChange={(e) => setSecond(e.target.value)} required /></Field>
          <Field label="Ergebnis-URLs A (optional, eine pro Zeile)"><Textarea rows={3} value={firstUrls} onChange={(e) => setFirstUrls(e.target.value)} /></Field>
          <Field label="Ergebnis-URLs B (optional, eine pro Zeile)"><Textarea rows={3} value={secondUrls} onChange={(e) => setSecondUrls(e.target.value)} /></Field>
        </div>
        <Button type="submit" variant="primary" loading={serp.isPending}>Vergleichen</Button>
      </form>
      {serp.error && <div className="mt-3"><ErrorBox error={serp.error} /></div>}
      {serp.data && (
        <div className="mt-3 space-y-1 text-sm">
          <p>{serp.data.provider}: A {serp.data.result.count_a} / B {serp.data.result.count_b} · Gemeinsame URLs {serp.data.result.common_count} · Jaccard {serp.data.result.jaccard ?? "–"}</p>
          <p className={muted}>{serp.data.result.interpretation}</p>
          {serp.data.result.common_urls.map((url) => <p key={url} className={"break-all " + muted}>{url}</p>)}
          <p className={"pt-1 " + muted}>{serp.data.method}</p>
        </div>
      )}
    </Card>
  );
}

const RELAUNCH_STATUS: Record<string, string> = {
  observed_ok: "in Ordnung", target_absent_in_new_crawl: "Ziel fehlt im neuen Crawl", non_200_target: "Ziel antwortet nicht mit 200",
  target_not_indexable: "Ziel nicht indexierbar", canonical_differs: "Canonical weicht ab",
  redirect_needs_verification: "Weiterleitung prüfen", title_changed_review: "Titel geändert",
};
const statusLabel = (s: string) => RELAUNCH_STATUS[s] ?? s;

const crawlLabel = (c: CrawlSummary) => `${crawlName(c)} · ${fmtDateTime(c.finished_at ?? c.started_at)} · ${fmtInt(c.pages_crawled)} URLs`;

export function RelaunchPanel({ siteId, crawls, newestId }: { siteId: number; crawls: CrawlSummary[]; newestId: number | null }) {
  const done = crawls.filter((c) => c.status === "completed");
  const [newId, setNewId] = useState<number | null>(newestId);
  const [oldId, setOldId] = useState<number | null>(null);
  const [mapping, setMapping] = useState("");
  useEffect(() => {
    const n = newestId ?? done[0]?.id ?? null;
    setNewId(n);
    setOldId(done.find((c) => n !== null && c.id < n)?.id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, newestId, done.length]);
  const relaunch = useMutation<Relaunch>({ mutationFn: () => api.post(root(siteId) + "/relaunch", {
    old_crawl_id: oldId, new_crawl_id: newId, mappings: parseMappings(mapping),
  }) });
  if (done.length < 2) {
    return <Card><EmptyState title="Zwei abgeschlossene Crawls nötig" description="Vor dem Relaunch einmal crawlen, danach noch einmal. Dann lassen sich alte und neue URLs vergleichen." /></Card>;
  }
  const problems = relaunch.data?.items.filter((x) => x.status !== "observed_ok") ?? [];
  return (
    <Card title="Relaunch-Vergleich" description="Welche URLs aus dem Crawl vor dem Relaunch sind danach noch erreichbar oder weitergeleitet? Es werden keine Weiterleitungen geändert.">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); relaunch.mutate(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Crawl vor dem Relaunch">
            <Select value={oldId ?? ""} onChange={(e) => setOldId(Number(e.target.value))} required>
              <option value="" disabled>Crawl wählen</option>
              {done.map((c) => <option key={c.id} value={c.id}>{crawlLabel(c)}</option>)}
            </Select>
          </Field>
          <Field label="Crawl nach dem Relaunch">
            <Select value={newId ?? ""} onChange={(e) => setNewId(Number(e.target.value))} required>
              {done.map((c) => <option key={c.id} value={c.id}>{crawlLabel(c)}</option>)}
            </Select>
          </Field>
        </div>
        <Field label="Geplante URL-Zuordnungen (optional)" hint="Eine pro Zeile: alte URL => neue URL (auch -> oder →)">
          <Textarea rows={3} value={mapping} onChange={(e) => setMapping(e.target.value)} />
        </Field>
        <Button type="submit" variant="primary" loading={relaunch.isPending} disabled={!oldId || !newId || oldId === newId}>Relaunch prüfen</Button>
      </form>
      {relaunch.error && <div className="mt-3"><ErrorBox error={relaunch.error} /></div>}
      {relaunch.data && (
        <div className="mt-3 space-y-1 text-sm">
          <div className="flex flex-wrap gap-1">
            {Object.entries(relaunch.data.counts).map(([k, n]) => <Badge key={k} tone={k === "observed_ok" ? "green" : "amber"}>{statusLabel(k)}: {n}</Badge>)}
          </div>
          {problems.slice(0, 60).map((x, i) => <p key={i} className="break-all text-xs">{statusLabel(x.status)} ·{x.old_url} → {x.intended_new_url}</p>)}
          {problems.length > 60 && <p className={muted}>… und {problems.length - 60} weitere</p>}
          <p className={"pt-1 " + muted}>{relaunch.data.method}</p>
        </div>
      )}
    </Card>
  );
}

export function PaginationPanel({ siteId }: { siteId: number }) {
  const q = useQuery<Pagination>({ queryKey: ["advanced-pagination", siteId], queryFn: () => api.get(root(siteId) + "/pagination") });
  if (q.isLoading) return <Card><Spinner /></Card>;
  if (q.error) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const items = q.data?.items ?? [];
  return (
    <Card title="Paginierung und tiefe Archivseiten" description="Blätterseiten aus dem letzten Crawl mit Klicktiefe und eingehenden Links">
      {!items.length ? <EmptyState title="Keine Paginierungsseiten im letzten Crawl" /> : items.slice(0, 100).map((x) => (
        <div key={x.url} className="mb-2 text-sm">
          <p className="break-all font-medium">{x.url}</p>
          <p className={muted}>Tiefe {x.depth ?? "?"} · Eingehende Links {x.inlinks}{x.indexable ? "" : " · nicht indexierbar"} · {x.hints.join("; ") || "keine weiteren Hinweise"}</p>
        </div>
      ))}
      <p className={muted}>{q.data?.method}</p>
    </Card>
  );
}

export function SchemaPotentialPanel({ siteId }: { siteId: number }) {
  const q = useQuery<Schema>({ queryKey: ["advanced-schema", siteId], queryFn: () => api.get(root(siteId) + "/schema-review") });
  if (q.isLoading) return <Card><Spinner /></Card>;
  if (q.error) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const items = q.data?.items ?? [];
  return (
    <Card title="Rich-Result-Potenzial" description="JSON-LD-Typen je Seite und welche davon Google für Suchfunktionen nutzen kann. Keine Garantie, dass Google sie anzeigt.">
      {!items.length ? <EmptyState title="Keine JSON-LD-Daten im letzten Crawl" /> : items.slice(0, 80).map((x) => (
        <div key={x.url} className="mb-2 text-sm">
          <p className="break-all font-medium">{x.url}</p>
          <p className={muted}>Typen: {x.types.join(", ")} · Mögliche Google-Funktionen: {x.potential_google_feature_types.join(", ") || "keine"} · Validator: {x.validator_result.errors} Fehler, {x.validator_result.warnings} Hinweise</p>
          {x.validator_result.findings.slice(0, 5).map((f, i) => <p key={i} className={muted}>{f.level}: {f.path} – {f.message}</p>)}
        </div>
      ))}
      <p className={muted}>{q.data?.method}</p>
    </Card>
  );
}
