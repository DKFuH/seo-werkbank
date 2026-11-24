import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, EmptyState, ErrorBox, Spinner } from "./ui";
type Candidate = { id: number; source_url: string; source_domain: string; target_url: string | null;
  confirmed_live_before: boolean; evidence: string; last_checked: string | null };
export default function LinkRecoveryPanel() {
  const { site } = useSite();
  const [message, setMessage] = useState("");
  const base = `/sites/${site?.id}/link-recovery`;
  const list = useQuery<{ items: Candidate[]; total_lost: number; note: string }>({
    queryKey: ["link-recovery", site?.id], enabled: !!site, queryFn: () => api.get(base),
  });
  const create = useMutation({
    mutationFn: (id: number) => api.post(`${base}/${id}/work`),
    onSuccess: x => setMessage(`SEO-Maßnahme #${x.work_item_id} erstellt; es wurde niemand kontaktiert.`),
    onError: e => setMessage(errorMessage(e)),
  });
  if (!site) return null;
  return <Card title="Verlorene Links zurückgewinnen" description="Nur importierte und überprüfte Links. Bisher nachweislich live gewesene Links zuerst prüfen.">
    {message && <p role="status" className="mb-3 text-sm">{message} <Link to="/seo-work" className="underline">Maßnahmen</Link></p>}
    {list.isLoading ? <Spinner /> : list.error ? <ErrorBox error={list.error} /> :
      !list.data?.items.length ? <EmptyState title="Keine derzeit als verloren geprüften Backlinks" /> :
      <div className="space-y-2">{list.data.items.map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 border-t py-2 text-sm dark:border-slate-800">
        <div className="min-w-0 flex-1">
          <a href={item.source_url} target="_blank" rel="noreferrer" className="break-all underline">{item.source_url}</a>
          <p className="text-xs text-slate-500">{item.evidence} · Ziel: {item.target_url || "unbekannt"}</p>
        </div>
        <Button size="sm" disabled={create.isPending} onClick={() => create.mutate(item.id)}>Recovery-Aufgabe</Button>
      </div>)}</div>}
    <p className="mt-2 text-xs text-slate-500">{list.data?.note}</p>
  </Card>;
}
