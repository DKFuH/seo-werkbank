import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, EmptyState, ErrorBox, Input, Notice, PageHeader, Spinner } from "../components/ui";

type Rule = {
  id: number; source_url: string; target_url: string; status_code: number;
  origin: string; state: string; confidence: number | null; note: string;
};
type Simulation = { rules: number; findings: { source_url: string; issue: string; status?: number }[]; note: string };

export default function Redirects() {
  const { site } = useSite();
  const siteId = site?.id;
  const qc = useQueryClient();
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [status, setStatus] = useState<301 | 308>(301);
  const [message, setMessage] = useState("");
  const base = `/sites/${siteId}/redirects`;
  const query = useQuery<Rule[]>({
    queryKey: ["redirects", siteId], enabled: !!siteId,
    queryFn: () => api.get(base),
  });
  const mutation = useMutation({
    mutationFn: (action: { path: string; body?: unknown }) => api.post(action.path, action.body),
    onSuccess: () => { setMessage("Änderung gespeichert"); qc.invalidateQueries({ queryKey: ["redirects", siteId] }); },
    onError: (error) => setMessage(errorMessage(error)),
  });
  const sim = useQuery<Simulation>({
    queryKey: ["redirect-simulation", siteId], enabled: false,
    queryFn: () => api.post(`${base}/simulate`),
  });
  if (!siteId) return <EmptyState title="Website auswählen" />;
  return <div className="space-y-5">
    <PageHeader title="Weiterleitungsverwaltung" description="Vorschläge prüfen, simulieren und nach Freigabe exportieren. Es werden keine Serverregeln automatisch installiert." />
    <Notice>302/307 auf 301 umzustellen ist nur sinnvoll, wenn die Änderung wirklich dauerhaft ist. Die URL-Ähnlichkeit bei 404-Seiten ist lediglich ein Kandidat, keine bestätigte fachliche Zuordnung.</Notice>
    <Card title="Regel als Entwurf anlegen">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm">Quell-URL<Input value={source} onChange={(e) => setSource(e.target.value)} placeholder="https://example.de/alt" /></label>
        <label className="text-sm">Ziel-URL<Input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="https://example.de/neu" /></label>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <select aria-label="HTTP-Status" value={status} onChange={(e) => setStatus(Number(e.target.value) as 301 | 308)} className="rounded border p-2 dark:bg-slate-900">
          <option value={301}>301</option><option value={308}>308</option>
        </select>
        <Button disabled={!source || !target || mutation.isPending} onClick={() => {
          mutation.mutate({ path: base, body: { source_url: source, target_url: target, status_code: status } });
        }}>Entwurf anlegen</Button>
        <Button variant="secondary" disabled={mutation.isPending} onClick={() => mutation.mutate({ path: `${base}/suggest` })}>Aus letztem Crawl vorschlagen</Button>
      </div>
    </Card>
    {message && <p role="status" className="text-sm">{message}</p>}
    <Card title="Regeln und Entscheidungen">
      {query.isLoading ? <Spinner /> : query.error ? <ErrorBox error={query.error} onRetry={() => query.refetch()} /> :
        !(query.data ?? []).length ? <p className="text-sm text-slate-500">Noch keine Vorschläge vorhanden.</p> :
        <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>
          <th className="p-2">Quelle</th><th className="p-2">Ziel</th><th className="p-2">Status</th><th className="p-2">Bewertung</th><th className="p-2">Aktion</th>
        </tr></thead><tbody>{query.data?.map((r) => <tr key={r.id} className="border-t border-slate-200 dark:border-slate-800">
          <td className="break-all p-2">{r.source_url}</td><td className="break-all p-2">{r.target_url}</td>
          <td className="p-2">{r.status_code} · {r.state}</td>
          <td className="p-2">{r.origin}{r.confidence != null ? ` · ${Math.round(r.confidence * 100)}% Ähnlichkeit` : ""}<p className="text-xs text-slate-500">{r.note}</p></td>
          <td className="p-2">{r.state === "proposed" ? <div className="flex gap-2">
            <Button size="sm" onClick={() => mutation.mutate({ path: `${base}/${r.id}/approve` })}>Freigeben</Button>
            <Button size="sm" variant="secondary" onClick={() => mutation.mutate({ path: `${base}/${r.id}/reject` })}>Verwerfen</Button>
          </div> : <Button size="sm" variant="secondary" onClick={() => mutation.mutate({ path: `${base}/${r.id}/reopen` })}>Neu prüfen</Button>}</td>
        </tr>)}</tbody></table></div>}
    </Card>
    <Card title="Simulation und Export">
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => sim.refetch()}>Regeln simulieren</Button>
        {(["apache", "nginx", "csv"] as const).map((fmt) => <Button key={fmt} variant="secondary" onClick={() => {
          api.download(`${base}/export`, { format: fmt }, `redirects.${fmt}`).catch(e => setMessage(errorMessage(e)));
        }}>{fmt.toUpperCase()} exportieren</Button>)}
      </div>
      {sim.isFetching && <Spinner />}
      {sim.error && <ErrorBox error={sim.error} onRetry={() => sim.refetch()} />}
      {sim.data && <div className="mt-3 text-sm"><p>{sim.data.rules} Regeln · {sim.data.findings.length} Hinweise</p>
        <ul className="mt-2 list-disc pl-5">{sim.data.findings.map((f, i) => <li key={i}>{f.issue}: {f.source_url}</li>)}</ul>
        <p className="mt-2 text-xs text-slate-500">{sim.data.note}</p></div>}
    </Card>
  </div>;
}
