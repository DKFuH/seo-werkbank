import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Overlap = { provider: string; result: { common_count: number; count_a: number;
  count_b: number; jaccard: number | null; overlap_of_smaller: number | null; common_urls: string[];
  interpretation: string }; method: string };
type Relaunch = { items: { old_url: string; intended_new_url: string; status: string }[];
  counts: Record<string, number>; method: string };
type Pagination = { crawl_id: number | null; items: { url: string; depth: number | null;
  inlinks: number; indexable: boolean; hints: string[] }[]; method: string };
type Schema = { crawl_id: number | null; items: { url: string; types: string[];
  potential_google_feature_types: string[]; other_schema_types: string[];
  google_eligibility_confirmed: boolean }[]; method: string };

export default function AdvancedSeo() {
  const { site } = useSite();
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [firstUrls, setFirstUrls] = useState("");
  const [secondUrls, setSecondUrls] = useState("");
  const [oldCrawl, setOldCrawl] = useState("");
  const [newCrawl, setNewCrawl] = useState("");
  const [mapping, setMapping] = useState("");
  const root = "/sites/" + site?.id + "/advanced";
  const parseLines = (s: string) => s.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  const serp = useMutation<Overlap>({ mutationFn: () => api.post(root + "/serp-overlap", {
    first_keyword: first, second_keyword: second, country: "de", language: "de",
    manual_urls_first: parseLines(firstUrls), manual_urls_second: parseLines(secondUrls),
  }) });
  const relaunch = useMutation<Relaunch>({ mutationFn: () => api.post(root + "/relaunch", {
    old_crawl_id: Number(oldCrawl), new_crawl_id: Number(newCrawl),
    mappings: parseLines(mapping).map(line => {
      const [old_url, new_url] = line.split(" => ").map(x => x.trim());
      return { old_url, new_url };
    }),
  }) });
  const pagination = useQuery<Pagination>({ queryKey: ["advanced-pagination", site?.id],
    queryFn: () => api.get(root + "/pagination"), enabled: !!site });
  const schema = useQuery<Schema>({ queryKey: ["advanced-schema", site?.id],
    queryFn: () => api.get(root + "/schema-review"), enabled: !!site });
  return <div className="space-y-4">
    <PageHeader title="Erweiterte SEO-Prüfungen" description="SERP-Overlap, Relaunch-Vergleiche, Paginierung und Schema-Potenzial aus tatsächlich vorhandenen Daten." />
    <Card title="SERP-Overlap – zwei Keywords vergleichen">
      <form className="space-y-3" onSubmit={e => { e.preventDefault(); serp.mutate(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Keyword A"><Input value={first} onChange={e => setFirst(e.target.value)} required /></Field>
          <Field label="Keyword B"><Input value={second} onChange={e => setSecond(e.target.value)} required /></Field>
          <Field label="Ergebnis-URLs A (optional, eine pro Zeile)"><Textarea rows={3} value={firstUrls} onChange={e => setFirstUrls(e.target.value)} /></Field>
          <Field label="Ergebnis-URLs B (optional, eine pro Zeile)"><Textarea rows={3} value={secondUrls} onChange={e => setSecondUrls(e.target.value)} /></Field>
        </div>
        <Button type="submit" variant="primary" loading={serp.isPending} disabled={!site}>Vergleichen</Button>
      </form>
      {serp.error && <ErrorBox error={serp.error} />}
      {serp.data && <div className="mt-3 text-sm">
        <p>{serp.data.provider}: A {serp.data.result.count_a} / B {serp.data.result.count_b}
          {" · "}Gemeinsame URLs {serp.data.result.common_count}
          {" · "}Jaccard {serp.data.result.jaccard ?? "–"}</p>
        {serp.data.result.common_urls.map(url => <p key={url} className="break-all text-xs text-slate-500">{url}</p>)}
        <p className="mt-2 text-xs text-slate-500">{serp.data.method}</p>
      </div>}
    </Card>
    <Card title="Relaunch: zwei gespeicherte Crawls vergleichen">
      <p className="mb-2 text-xs text-slate-500">Zwei abgeschlossene Crawl-IDs der gleichen Website angeben. Optional Zuordnungen im Format „alte URL => neue URL“.</p>
      <form className="space-y-3" onSubmit={e => { e.preventDefault(); relaunch.mutate(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Crawl-ID vorher"><Input type="number" min={1} required value={oldCrawl} onChange={e => setOldCrawl(e.target.value)} /></Field>
          <Field label="Crawl-ID danach"><Input type="number" min={1} required value={newCrawl} onChange={e => setNewCrawl(e.target.value)} /></Field>
        </div>
        <Field label="Explizite URL-Zuordnungen (optional)"><Textarea rows={3} value={mapping} onChange={e => setMapping(e.target.value)} /></Field>
        <Button type="submit" disabled={!site} loading={relaunch.isPending}>Relaunch prüfen</Button>
      </form>
      {relaunch.error && <ErrorBox error={relaunch.error} />}
      {relaunch.data && <div className="mt-3 text-sm">
        <p>{Object.entries(relaunch.data.counts).map(([k, n]) => k + ": " + n).join(" · ")}</p>
        {relaunch.data.items.filter(x => x.status !== "observed_ok").slice(0, 60).map((x, i) =>
          <p key={i} className="mt-1 break-all text-xs">{x.status} · {x.old_url} → {x.intended_new_url}</p>)}
        <p className="mt-2 text-xs text-slate-500">{relaunch.data.method}</p>
      </div>}
    </Card>
    <Card title="Paginierung und tiefe Archivseiten">
      {pagination.isLoading && <Spinner />}
      {pagination.error && <ErrorBox error={pagination.error} />}
      {!pagination.data?.items.length && <EmptyState title="Keine Hinweise aus dem letzten Crawl" />}
      {pagination.data?.items.slice(0, 100).map(x => <div key={x.url} className="mb-2 text-sm">
        <p className="break-all font-medium">{x.url}</p>
        <p className="text-xs text-slate-500">Tiefe {x.depth ?? "?"} · Eingehende Links {x.inlinks}
          {" · "}{x.hints.join("; ") || "Keine zusätzlichen Heuristikhinweise"}</p>
      </div>)}
      <p className="text-xs text-slate-500">{pagination.data?.method}</p>
    </Card>
    <Card title="Schema.org und Rich-Result-Potenzial">
      {schema.isLoading && <Spinner />}
      {schema.error && <ErrorBox error={schema.error} />}
      {!schema.data?.items.length && <EmptyState title="Keine JSON-LD-Daten im letzten Crawl" />}
      {schema.data?.items.slice(0, 80).map(x => <div key={x.url} className="mb-2 text-sm">
        <p className="break-all font-medium">{x.url}</p>
        <p className="text-xs text-slate-500">Typen: {x.types.join(", ")}
          {" · "}Mögliche Google-Funktionstypen: {x.potential_google_feature_types.join(", ") || "keine"}</p>
      </div>)}
      <p className="text-xs text-slate-500">{schema.data?.method}</p>
    </Card>
  </div>;
}
