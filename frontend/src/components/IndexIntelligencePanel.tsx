import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, EmptyState, ErrorBox, Select, Spinner } from "./ui";

type Smap = { crawl_id: number; date: string | null; sitemap_url_count: number; with_lastmod: number; added_count?: number; removed_count?: number; added: string[]; removed: string[]; compare_available: boolean; truncated: boolean };
type Inspect = { url: string; checked_at: string; verdict: string | null; coverage: string | null; previous_verdict: string | null; index_loss_alert: boolean };
export default function IndexIntelligencePanel() {
  const { site } = useSite();
  const [limit, setLimit] = useState(5);
  const [message, setMessage] = useState("");
  const prefix = `/sites/${site?.id}/index-intelligence`;
  const sitemap = useQuery<{ items: Smap[]; note: string }>({
    queryKey: ["sitemap-history", site?.id], enabled: !!site,
    queryFn: () => api.get(`${prefix}/sitemap-history`),
  });
  const candidates = useQuery<{ items: { url: string; reason: string }[] }>({
    queryKey: ["index-candidates", site?.id], enabled: !!site,
    queryFn: () => api.get(`${prefix}/candidates`),
  });
  const history = useQuery<{ items: Inspect[]; note: string }>({
    queryKey: ["inspection-history", site?.id], enabled: !!site,
    queryFn: () => api.get(`${prefix}/history`),
  });
  const start = useMutation({
    mutationFn: () => api.post(`${prefix}/inspect`, { limit }),
    onSuccess: result => setMessage(`Google-Inspection-Job #${result.job_id} gestartet. Verlauf nach Abschluss neu laden.`),
    onError: e => setMessage(errorMessage(e)),
  });
  if (!site) return null;
  return <div className="mt-5 space-y-4">
    <Card title="Sitemap-Historie über abgeschlossene Crawls" description="Es werden nur URLs verglichen, die der jeweilige Crawl tatsächlich erfasst hat.">
      {sitemap.isLoading ? <Spinner /> : sitemap.error ? <ErrorBox error={sitemap.error} /> :
        !sitemap.data?.items?.length ? <EmptyState title="Noch keine Crawl-Historie" /> :
        <div className="space-y-2">{sitemap.data.items.map(item => <div key={item.crawl_id} className="border-b py-2 text-sm dark:border-slate-800">
          <strong>Crawl #{item.crawl_id}</strong> · {item.date?.slice(0, 10) ?? "unbekannt"} · {item.sitemap_url_count} gelistete URLs, {item.with_lastmod} mit lastmod
          {item.compare_available && <p className="text-xs">Neu beobachtet: {item.added_count ?? 0} · Nicht mehr beobachtet: {item.removed_count ?? 0}</p>}
          {item.truncated && <p className="text-xs text-amber-600">Sitemap-URL-Vergleich gekürzt.</p>}
        </div>)}</div>}
      <p className="mt-2 text-xs text-slate-500">{sitemap.data?.note}</p>
    </Card>
    <Card title="Google URL Inspection – begrenzter Batch">
      <p className="mb-3 text-sm">Priorisiert neue oder geänderte, indexierbare Crawl-Seiten. Google liefert einen gespeicherten Indexstatus, keinen Live-URL-Test. Voraussetzung: verbundene Search Console und passende Property.</p>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <label className="text-sm">URLs je Durchlauf{" "}
          <Select value={limit} onChange={e => setLimit(Number(e.target.value))} className="w-20">
            {[1, 3, 5, 10].map(n => <option key={n} value={n}>{n}</option>)}
          </Select>
        </label>
        <Button loading={start.isPending} disabled={!(candidates.data?.items.length)} onClick={() => start.mutate()}>Prüfung starten</Button>
        <Button variant="secondary" onClick={() => void history.refetch()}>Verlauf aktualisieren</Button>
      </div>
      {message && <p role="status" className="mb-2 text-sm">{message}</p>}
      {candidates.isLoading && <Spinner />}
      <p className="text-xs text-slate-500">Prüfkandidaten: {candidates.data?.items.length ?? 0}. Bei fehlendem Crawl oder fehlender Property werden keine externen API-Anfragen erzeugt.</p>
      {history.error && <ErrorBox error={history.error} />}
      {!history.data?.items.length && <EmptyState title="Keine gespeicherten Google-Indexprüfungen" />}
      {history.data?.items.slice(0, 35).map((item, i) => <div key={i} className="border-b py-2 text-xs dark:border-slate-800">
        <div className="flex items-center gap-2"><strong>{item.verdict ?? "Unbekannt"}</strong>{item.index_loss_alert && <strong className="text-red-600">Indexstatus von PASS abgewichen</strong>}</div>
        <a href={item.url} className="break-all underline" target="_blank" rel="noreferrer">{item.url}</a>
        <p>{item.coverage ?? "Kein Coverage-State"} · {item.checked_at?.slice(0, 16)} {item.previous_verdict ? `(zuvor: ${item.previous_verdict})` : ""}</p>
      </div>)}
      <p className="mt-2 text-xs text-slate-500">{history.data?.note}</p>
    </Card>
  </div>;
}
