import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, EmptyState, ErrorBox, Input, Spinner } from "./ui";

type Snapshot = { id: number; title: string; origin: string; created_at: string; crawl_id: number };
export default function ReportSnapshotPanel() {
  const { site } = useSite();
  const [title, setTitle] = useState("SEO-Monatsbericht");
  const [message, setMessage] = useState("");
  const qc = useQueryClient();
  const base = `/sites/${site?.id}/reports/snapshots`;
  const list = useQuery<{ items: Snapshot[] }>({
    queryKey: ["report-snapshots", site?.id], enabled: !!site, queryFn: () => api.get(base),
  });
  const create = useMutation({
    mutationFn: () => api.post(base, { title }),
    onSuccess: () => { setMessage("Snapshot gespeichert."); void qc.invalidateQueries({ queryKey: ["report-snapshots", site?.id] }); },
    onError: e => setMessage(errorMessage(e)),
  });
  if (!site) return null;
  return <Card title="Unveränderliche Berichts-Snapshots" description="Messwerte werden beim Erstellen eingefroren. Für automatische Wiederholung einen Monitor vom Typ Bericht anlegen.">
    <div className="mb-3 flex flex-wrap gap-2">
      <Input value={title} maxLength={200} aria-label="Berichtstitel" onChange={e => setTitle(e.target.value)} className="min-w-48 flex-1" />
      <Button loading={create.isPending} disabled={!title.trim()} onClick={() => create.mutate()}>Snapshot erstellen</Button>
      <Link to="/monitoring" className="self-center text-sm underline">Zeitplan verwalten</Link>
    </div>
    {message && <p role="status" className="mb-3 text-sm">{message}</p>}
    {list.isLoading ? <Spinner /> : list.error ? <ErrorBox error={list.error} /> :
      !list.data?.items.length ? <EmptyState title="Noch keine archivierten Berichte" /> :
      <div className="space-y-2">{list.data.items.map(s => <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 border-t py-2 text-sm dark:border-slate-800">
        <div><strong>#{s.id} {s.title}</strong><p className="text-xs text-slate-500">{s.created_at.slice(0, 16)} · Crawl #{s.crawl_id} · {s.origin === "scheduled" ? "Monitor" : "manuell"}</p></div>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => api.download(`${base}/${s.id}.html`, undefined, `seo-snapshot-${s.id}.html`).catch(e => setMessage(errorMessage(e)))}>HTML</Button>
          <Button size="sm" onClick={() => api.download(`${base}/${s.id}.pdf`, undefined, `seo-snapshot-${s.id}.pdf`).catch(e => setMessage(errorMessage(e)))}>PDF</Button>
        </div>
      </div>)}</div>}
  </Card>;
}
