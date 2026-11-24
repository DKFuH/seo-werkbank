import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, EmptyState, ErrorBox, Spinner } from "./ui";

type Target = { id: number; keyword: string; engine: string; location: string | null };
export default function LocalRankPanel() {
  const { site } = useSite();
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<any>(null);
  const base = `/sites/${site?.id}`;
  const targets = useQuery<{ items: Target[] }>({
    queryKey: ["local-rank-targets", site?.id], enabled: !!site,
    queryFn: () => api.get(base + "/rank-targets"),
  });
  const measure = useMutation({
    mutationFn: (id: number) => api.post(base + "/external-intelligence/local-rank",
      { target_id: id, acknowledge_cost: true }),
    onSuccess: d => { setResult(d); setMessage("Anbieterantwort erhalten; Beobachtungen im Ranktracking gespeichert."); },
    onError: e => setMessage(errorMessage(e)),
  });
  if (!site) return null;
  const valid = (targets.data?.items ?? []).filter(t => t.engine === "google" && t.location?.trim());
  return <Card title="Lokale Suchpositionen (DataForSEO)" description="Organische und Maps-Ergebnisse für einen konkreten Ort – keine GSC-Durchschnittsposition. Jede Messung ist kostenpflichtig.">
    <p className="mb-3 text-xs text-slate-500">Zugangsdaten unter <Link to="/external-analytics" className="underline">Externe Analytics & SERP-Daten</Link> hinterlegen. Google-Targets mit einer vollständigen DataForSEO-Ortsangabe anlegen.</p>
    {targets.isLoading && <Spinner />}
    {targets.error && <ErrorBox error={targets.error} />}
    {!valid.length && <EmptyState title="Keine ortsbezogenen Google-Targets" description="Im Ranktracker ein Keyword mit Suchmaschine Google und konkretem Standort anlegen." />}
    {valid.slice(0, 30).map(t => <div key={t.id} className="flex flex-wrap items-center justify-between gap-3 border-t py-2 text-sm dark:border-slate-800">
      <span><strong>{t.keyword}</strong> · {t.location}</span>
      <Button size="sm" loading={measure.isPending} onClick={() => {
        if (window.confirm("Die DataForSEO-Abfrage kostet Geld und führt zwei Anfragen (organisch und Maps) aus. Jetzt ausführen?")) measure.mutate(t.id);
      }}>Kostenpflichtig messen</Button>
    </div>)}
    {message && <p role="status" className="mt-2 text-sm">{message}</p>}
    {result && <div className="mt-2 text-sm">
      <strong>{result.keyword} · {result.location}</strong>
      <p>Organisch: {result.organic?.position ?? "Nicht gefunden / nicht zuordenbar"}</p>
      <p>Google Maps: {result.maps?.position ?? "Nicht gefunden / nicht zuordenbar"}</p>
      <p className="text-xs text-slate-500">{result.note}</p>
    </div>}
  </Card>;
}
