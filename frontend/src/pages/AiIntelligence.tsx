import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Sample = { id: number; provider: string; model_name: string | null; answer: string;
  source: string; observed_at: string; brand_matches: string[]; competitor_matches: string[];
  verified_search: false };
type PromptTest = { id: number; prompt: string; brand_terms: string[]; competitor_terms: string[];
  samples: Sample[] };
type List = { items: PromptTest[]; method: string };
type Referrals = { referrals: { host: string; visits: number | null; recorded_conversions: number | null }[];
  method: string; days: number };

export default function AiIntelligence() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [brands, setBrands] = useState("");
  const [competitors, setCompetitors] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [providers, setProviders] = useState<Record<number, string>>({});
  const [days, setDays] = useState(30);
  const root = "/sites/" + site?.id;
  const key = ["ai-prompt-tests", site?.id];
  const q = useQuery<List>({ queryKey: key, queryFn: () => api.get(root + "/ai-prompt-tests"), enabled: !!site });
  const referral = useQuery<Referrals>({ queryKey: ["ai-referrals", site?.id, days],
    queryFn: () => api.get(root + "/ai-referrals", { days }), enabled: false });
  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  const add = useMutation({
    mutationFn: () => api.post(root + "/ai-prompt-tests", {
      prompt, brand_terms: brands.split(",").map((v) => v.trim()).filter(Boolean),
      competitor_terms: competitors.split(",").map((v) => v.trim()).filter(Boolean),
    }),
    onSuccess: () => { setPrompt(""); setBrands(""); setCompetitors(""); refresh(); },
  });
  const sample = useMutation({
    mutationFn: (id: number) => api.post(root + "/ai-prompt-tests/" + id + "/samples", {
      provider: providers[id] || "manual", answer: answers[id],
    }),
    onSuccess: refresh,
  });
  const run = useMutation({ mutationFn: (id: number) => api.post(root + "/ai-prompt-tests/" + id + "/run", {}),
    onSuccess: refresh });
  const remove = useMutation({ mutationFn: (id: number) => api.del(root + "/ai-prompt-tests/" + id),
    onSuccess: refresh });
  return <div className="space-y-4">
    <PageHeader title="KI-Empfehlungen & Matomo-Referrals" description="Wiederholbare Prompts testen, Markenwörter in konkreten Antworten vergleichen und echte Analytics-Referrals getrennt betrachten." />
    <Card title="Prompt-Test anlegen">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Testfrage"><Textarea rows={2} maxLength={2000} value={prompt} required onChange={(e) => setPrompt(e.target.value)} /></Field>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Eigene Markennamen (kommagetrennt)"><Input required value={brands} onChange={(e) => setBrands(e.target.value)} /></Field>
          <Field label="Wettbewerbernamen (optional)"><Input value={competitors} onChange={(e) => setCompetitors(e.target.value)} /></Field>
        </div>
        <Button type="submit" variant="primary" loading={add.isPending} disabled={!site}>Test speichern</Button>
      </form>
      {add.error && <ErrorBox error={add.error} />}
      <p className="mt-2 text-xs text-slate-500">Vergleiche zählen Worttreffer in Einzelantworten – keine Platzierung oder verifizierte Empfehlung. Modelleinstellungen bleiben unter Einstellungen.</p>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {q.isLoading && <Card><Spinner /></Card>}
    {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
    {q.data?.items.length === 0 && <Card><EmptyState title="Noch keine Testprompts" /></Card>}
    {q.data?.items.map((test) => <Card key={test.id} title={test.prompt}
      actions={<Button size="sm" variant="ghost" disabled={remove.isPending}
        onClick={() => { if (window.confirm("Test mit allen Stichproben löschen?")) remove.mutate(test.id); }}>Löschen</Button>}>
      <p className="text-xs text-slate-500">Eigene Begriffe: {test.brand_terms.join(", ")} · Wettbewerber: {test.competitor_terms.join(", ") || "keine"}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" disabled={run.isPending}
          onClick={() => { if (window.confirm("Diesen Prompt einmal ausdrücklich an den konfigurierten Chatmodell-Anbieter senden?")) run.mutate(test.id); }}>
          Chatmodell-Stichprobe ausführen
        </Button>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        <Field label="Manuelle Quelle/Plattform"><Input maxLength={32} placeholder="z. B. chatgpt" value={providers[test.id] ?? ""}
          onChange={(e) => setProviders((p) => ({ ...p, [test.id]: e.target.value }))} /></Field>
        <Field label="Beobachtete Antwort"><Textarea rows={2} maxLength={20000} value={answers[test.id] ?? ""}
          onChange={(e) => setAnswers((p) => ({ ...p, [test.id]: e.target.value }))} /></Field>
      </div>
      <Button size="sm" disabled={!answers[test.id]?.trim() || sample.isPending} onClick={() => sample.mutate(test.id)}>Manuelle Antwort dokumentieren</Button>
      <div className="mt-3 space-y-2">{test.samples.map((s) => <div key={s.id} className="rounded border border-slate-200 p-2 text-sm dark:border-slate-700">
        <p className="text-xs text-slate-500">{s.observed_at.slice(0, 16)} · {s.provider} · {s.source} · nicht als KI-Suche verifiziert</p>
        <p className="whitespace-pre-wrap text-sm">{s.answer.slice(0, 1200)}{s.answer.length > 1200 ? "…" : ""}</p>
        <p className="text-xs text-slate-500">Worttreffer eigene Marke: {s.brand_matches.join(", ") || "keine"} · Konkurrenz: {s.competitor_matches.join(", ") || "keine"}</p>
      </div>)}</div>
    </Card>)}
    {sample.error && <ErrorBox error={sample.error} />}
    {run.error && <ErrorBox error={run.error} />}
    {remove.error && <ErrorBox error={remove.error} />}
    <Card title="KI-Referral-Besuche aus Matomo">
      <p className="mb-2 text-xs text-slate-500">Nur erkennbare Referral-Domains. Direkte und unbekannte KI-Trafficquellen fehlen. Kein automatischer Nachweis eines Verkaufs.</p>
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Zeitraum (Tage)"><Input type="number" min={1} max={180} value={days} onChange={(e) => setDays(Number(e.target.value))} /></Field>
        <Button disabled={!site || referral.isFetching} onClick={() => referral.refetch()}>Matomo bewusst abrufen</Button>
      </div>
      {referral.isFetching && <Spinner />}
      {referral.error && <ErrorBox error={referral.error} />}
      {referral.data?.referrals.map((r) => <p key={r.host} className="mt-2 text-sm">{r.host}: {r.visits ?? "?"} Besuche
        {" · "}zugeordnete Conversion-Ereignisse: {r.recorded_conversions ?? "nicht verfügbar"}</p>)}
      {referral.data && !referral.data.referrals.length && <EmptyState title="Keine erkannten KI-Referral-Domains" />}
      <p className="mt-2 text-xs text-slate-500">{referral.data?.method}</p>
    </Card>
  </div>;
}
