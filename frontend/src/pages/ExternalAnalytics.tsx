import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "../lib/api";
import { useSite } from "../lib/context";
import { Button, Card, ErrorBox, Input, PageHeader, Select, Spinner } from "../components/ui";

type Status = { provider: string; connected: boolean; note: string };
export default function ExternalAnalytics() {
  const { site } = useSite();
  const [provider, setProvider] = useState<"ga4" | "clarity" | "dataforseo">("ga4");
  const [values, setValues] = useState<Record<string,string>>({});
  const [message, setMessage] = useState("");
  const [ga, setGa] = useState<any>(null);
  const [clarity, setClarity] = useState<any>(null);
  const base = `/sites/${site?.id}/external-intelligence`;
  const status = useQuery<{ providers: Status[] }>({ queryKey: ["external-status", site?.id],
    enabled: !!site, queryFn: () => api.get(base + "/status") });
  const save = useMutation({ mutationFn: () => api.put(base + "/config", { provider, ...values }),
    onSuccess: () => { setMessage("Zugangsdaten gespeichert."); setValues({}); void status.refetch(); },
    onError: e => setMessage(errorMessage(e)) });
  const disconnect = useMutation({ mutationFn: () => api.del(`${base}/config/${provider}`),
    onSuccess: () => { setMessage("Verbindungskonfiguration entfernt."); void status.refetch(); },
    onError: e => setMessage(errorMessage(e)) });
  const load = useMutation({ mutationFn: (p: "ga4" | "clarity") => api.get(`${base}/${p}`),
    onSuccess: (d, p) => { if (p === "ga4") setGa(d); else setClarity(d); },
    onError: e => setMessage(errorMessage(e)) });
  const fields = provider === "ga4"
    ? [["property_id", "GA4-Property-ID"], ["client_email", "Service-Account-E-Mail"], ["private_key", "Service-Account Private Key (PEM)"]]
    : provider === "clarity" ? [["token", "Clarity API-Token"]]
    : [["login", "DataForSEO API-Login"], ["password", "DataForSEO API-Passwort"]];
  return <div className="space-y-4">
    <PageHeader title="Externe Analytics & SERP-Daten" description="Optionale echte GA4-, Microsoft-Clarity- und kostenpflichtige lokale DataForSEO-Abfragen. Ohne Zugangsdaten werden keine Live-Zahlen behauptet." />
    {!site ? <Card>Bitte eine Website auswählen.</Card> : <>
      <Card title="Zugangsdaten je Website verschlüsselt hinterlegen">
        {status.isLoading && <Spinner />}
        {status.error && <ErrorBox error={status.error} />}
        <p className="mb-3 text-sm">{status.data?.providers?.map(p => `${p.provider}: ${p.connected ? "konfiguriert" : "nicht verbunden"}`).join(" · ")}</p>
        <Select value={provider} onChange={e => { setProvider(e.target.value as typeof provider); setValues({}); }} className="mb-3 w-56">
          <option value="ga4">Google Analytics 4</option><option value="clarity">Microsoft Clarity</option><option value="dataforseo">DataForSEO / Lokales Ranktracking</option>
        </Select>
        <div className="space-y-2">{fields.map(([key, label]) => <label key={key} className="block text-xs font-medium">{label}
          {key === "private_key" ? <textarea className="mt-1 w-full rounded border p-2 font-mono text-xs dark:bg-slate-900" rows={4} value={values[key] || ""} onChange={e => setValues(s => ({ ...s, [key]: e.target.value }))} /> :
          <Input className="mt-1" type={["token", "password"].includes(key) ? "password" : "text"} value={values[key] || ""} onChange={e => setValues(s => ({ ...s, [key]: e.target.value }))} />}
        </label>)}</div>
        <div className="mt-3 flex gap-2"><Button loading={save.isPending} onClick={() => save.mutate()}>Konfiguration speichern</Button>
          <Button variant="danger" loading={disconnect.isPending} onClick={() => disconnect.mutate()}>Trennen</Button></div>
      </Card>
      <Card title="Echte Anbieterkennzahlen abrufen">
        <div className="flex flex-wrap gap-2">
          <Button loading={load.isPending} onClick={() => load.mutate("ga4")}>GA4: 28 Tage abrufen</Button>
          <Button loading={load.isPending} onClick={() => load.mutate("clarity")}>Clarity: 3 Tage abrufen</Button>
        </div>
        {message && <p role="status" className="mt-2 text-sm">{message}</p>}
        {ga && <div className="mt-3 text-sm"><strong>GA4 · {ga.days} Tage</strong>
          {Object.entries(ga.metrics || {}).map(([name, value]) => <p key={name}>{name}: {value == null ? "–" : String(value)}</p>)}</div>}
        {clarity && <div className="mt-3 text-sm"><strong>Clarity · {clarity.days} Tage</strong>
          {(clarity.metrics || []).map((item: any, i: number) => <p key={i}>{item.metric}: {JSON.stringify(item.rows)}</p>)}</div>}
        <p className="mt-2 text-xs text-slate-500">Clarity begrenzt Daten auf die letzten 1–3 Tage und hat ein strenges Tageskontingent. GA4 benötigt eine freigegebene Service-Account-E-Mail in der Property. DataForSEO-Messungen werden einzeln im Ranktracker ausgelöst.</p>
      </Card>
    </>}
  </div>;
}
