import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, EmptyState, ErrorBox, Notice, PageHeader, Spinner } from "../components/ui";

type ImportRow = {
  id: number; filename: string; state: string; format: string;
  lines_total: number; lines_parsed: number; lines_skipped: number;
  period_start: string | null; period_end: string | null;
};
type Summary = {
  imports: ImportRow[]; import_id?: number; status_counts: Record<string, number>;
  agent_counts: Record<string, number>; googlebot_days: { day: string; count: number }[];
  top_404: { path: string; count: number; referrer_host: string; agent_class: string }[];
  crawl_comparison?: { crawl_id: number | null; indexable_without_googlebot: number; examples: string[] };
  privacy?: string; note?: string;
};

export default function Logs() {
  const { site } = useSite();
  const siteId = site?.id;
  const base = `/sites/${siteId}/logs`;
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [fmt, setFmt] = useState("auto");
  const [importId, setImportId] = useState<number | undefined>(undefined);
  const [redirectFor, setRedirectFor] = useState("");
  const [target, setTarget] = useState("");
  const [message, setMessage] = useState("");
  const imports = useQuery<ImportRow[]>({ queryKey: ["log-imports", siteId], enabled: !!siteId,
    queryFn: () => api.get(base), refetchInterval: (query) => query.state.data?.some((x: ImportRow) => x.state === "processing") ? 3000 : false });
  const stats = useQuery<Summary>({ queryKey: ["log-stats", siteId, importId], enabled: !!siteId,
    queryFn: () => api.get(`${base}/summary`, { import_id: importId }), refetchInterval: 10000 });
  const upload = useMutation({ mutationFn: (f: File) => api.upload(`${base}/import`, f, undefined, { fmt }),
    onSuccess: (data) => { setMessage(`Import #${data.import_id} gestartet – Job #${data.job_id}`); qc.invalidateQueries({ queryKey: ["log-imports", siteId] }); },
    onError: (e) => setMessage(errorMessage(e)) });
  const remove = useMutation({ mutationFn: (id: number) => api.del(`${base}/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["log-imports", siteId] }); qc.invalidateQueries({ queryKey: ["log-stats", siteId] }); },
    onError: (e) => setMessage(errorMessage(e)) });
  const redirect = useMutation({ mutationFn: (path: string) => api.post(`${base}/404/redirect`, { path, target_url: target }),
    onSuccess: () => { setMessage("Redirect-Entwurf erstellt. Bitte unter Weiterleitungen prüfen und freigeben."); setRedirectFor(""); setTarget(""); },
    onError: (e) => setMessage(errorMessage(e)) });
  if (!siteId) return <EmptyState title="Website auswählen" />;
  return <div className="space-y-5">
    <PageHeader title="Logfile-Analyse & 404-Monitor" description="Apache-/Nginx-Zugriffe, Crawl-Budget-Hinweise und 404-Ziele – nur aggregierte Daten." />
    <Notice tone="warn">Bot-Erkennung erfolgt ausschließlich anhand des User-Agents und ist nicht verifiziert. Keine Rohzeilen oder IP-Adressen werden dauerhaft gespeichert. URLs mit sensiblen Pfadsegmenten werden teilweise maskiert; weitere personenbezogene Pfade müssen vor dem Upload geprüft werden.</Notice>
    <Card title="Serverlog importieren">
      <input type="file" accept=".log,.txt,.gz" onChange={e => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm" aria-label="Access-Log auswählen" />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select value={fmt} onChange={e => setFmt(e.target.value)} aria-label="Logformat" className="rounded border p-2 dark:bg-slate-900">
          <option value="auto">Format automatisch erkennen</option><option value="combined">Combined</option><option value="common">Common</option>
        </select>
        <Button disabled={!file || upload.isPending} onClick={() => { if (file) upload.mutate(file); }}>Import starten</Button>
      </div>
    </Card>
    {message && <p role="status" className="text-sm">{message}</p>}
    <Card title="Importverlauf">
      {imports.isLoading ? <Spinner /> : imports.error ? <ErrorBox error={imports.error} onRetry={() => imports.refetch()} /> :
        <div className="space-y-2">{(imports.data ?? []).length === 0 && <p className="text-sm text-slate-500">Noch kein Import vorhanden.</p>}
          {(imports.data ?? []).map(row => <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-2 text-sm dark:border-slate-800">
            <div><strong>#{row.id} {row.filename}</strong> · {row.state} · {row.lines_parsed}/{row.lines_total} Zeilen
              <p className="text-xs text-slate-500">{row.period_start ?? "–"} bis {row.period_end ?? "–"}, {row.lines_skipped} übersprungen</p>
            </div><div className="flex gap-2">
              {row.state === "completed" && <Button size="sm" variant="secondary" onClick={() => setImportId(row.id)}>Auswerten</Button>}
              <Button size="sm" variant="danger" disabled={row.state === "processing" || remove.isPending} onClick={() => remove.mutate(row.id)}>Löschen</Button>
            </div>
          </div>)}</div>}
    </Card>
    <Card title="Zusammenfassung">
      {stats.isLoading ? <Spinner /> : stats.error ? <ErrorBox error={stats.error} onRetry={() => stats.refetch()} /> :
        <><p className="text-sm">{stats.data?.note ?? `Import #${stats.data?.import_id ?? "–"}`}</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2"><div><strong>Statuscodes</strong>
            {Object.entries(stats.data?.status_counts ?? {}).map(([s,n]) => <p key={s} className="text-sm">{s}: {n.toLocaleString("de-DE")}</p>)}</div>
            <div><strong>UA-Klassen</strong>{Object.entries(stats.data?.agent_counts ?? {}).map(([s,n]) => <p key={s} className="text-sm">{s}: {n.toLocaleString("de-DE")}</p>)}</div></div>
          {stats.data?.crawl_comparison && <p className="mt-3 text-sm">Indexierbare Crawl-URLs ohne beanspruchten Googlebot-Treffer im Logzeitraum: {stats.data.crawl_comparison.indexable_without_googlebot}. Das ist kein Nachweis fehlender Indexierung.</p>}
        </>}
    </Card>
    <Card title="Häufigste 404-Pfade">
      {!(stats.data?.top_404?.length) ? <p className="text-sm text-slate-500">Keine 404-Treffer im gewählten Datensatz.</p> :
        <div className="space-y-2">{stats.data.top_404.map((row,i) => <div key={i} className="border-b py-2 text-sm dark:border-slate-800">
          <div className="flex flex-wrap items-center justify-between gap-2"><span className="break-all">{row.path} · {row.count} Aufrufe · {row.referrer_host || "ohne Referrer"}</span>
            <Button variant="secondary" size="sm" onClick={() => setRedirectFor(row.path)}>Redirect vorschlagen</Button></div>
          {redirectFor === row.path && <div className="mt-2 flex flex-wrap gap-2">
            <input aria-label="Ziel-URL" className="min-w-52 flex-1 rounded border p-2 dark:bg-slate-900" value={target} placeholder="https://example.de/passendes-ziel" onChange={e=>setTarget(e.target.value)} />
            <Button disabled={!target || redirect.isPending} onClick={() => redirect.mutate(row.path)}>Entwurf speichern</Button>
            <Button variant="ghost" onClick={() => setRedirectFor("")}>Abbrechen</Button>
          </div>}
        </div>)}</div>}
      <p className="mt-3 text-xs text-slate-500">Die Umleitung wird nie automatisch aktiviert. <Link className="underline" to="/redirects">Weiterleitungsverwaltung öffnen</Link>.</p>
    </Card>
  </div>;
}
