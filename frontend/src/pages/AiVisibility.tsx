import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, Checkbox, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { AiSourceStabilityPanel } from "../components/AuthorityPanels";
import { fmtDateTime } from "../lib/format";

type Observation = { id: number; platform: string; model_name: string | null; prompt: string; brand_mentioned: boolean;
  cited_url: string | null; evidence_url: string | null; response_excerpt: string; notes: string;
  observed_at: string; source: "manual"; verified: false };
type Result = { items: Observation[]; method: string; source: string };
const platforms = ["chatgpt", "perplexity", "claude", "gemini", "copilot", "google_ai", "other"];

export default function AiVisibility() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [platform, setPlatform] = useState("chatgpt");
  const [modelName, setModelName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [mentioned, setMentioned] = useState(false);
  const [citedUrl, setCitedUrl] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [notes, setNotes] = useState("");
  const path = "/sites/" + site?.id + "/ai-visibility/observations";
  const key = ["ai-visibility", site?.id];
  const q = useQuery<Result>({ queryKey: key, queryFn: () => api.get(path), enabled: !!site });
  const add = useMutation({ mutationFn: () => api.post(path, {
    platform, model_name: modelName || null, prompt, brand_mentioned: mentioned,
    cited_url: citedUrl || null, evidence_url: evidenceUrl || null, response_excerpt: excerpt, notes,
  }), onSuccess: () => { setPrompt(""); setMentioned(false); setCitedUrl(""); setEvidenceUrl("");
    setExcerpt(""); setNotes(""); void qc.invalidateQueries({ queryKey: key }); } });
  const remove = useMutation({ mutationFn: (id: number) => api.del(path + "/" + id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }) });
  return <div className="space-y-4">
    <PageHeader title="KI-Erwähnungen & Quellen" description="Manuell beobachtete KI-Antworten nachvollziehbar dokumentieren. Kein Live-Ranking, kein Zugriff auf interne Modelle oder versteckte Suchanfragen." />
    <Card title="Beobachtung dokumentieren" description="Eine Stichprobe ist nur für ihre konkrete Anfrage, Plattform, Modellversion und Zeitpunkt aussagekräftig.">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Plattform"><Select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            {platforms.map((p) => <option key={p} value={p}>{p}</option>)}
          </Select></Field>
          <Field label="Modell/Version (wenn bekannt)"><Input maxLength={100} value={modelName} onChange={(e) => setModelName(e.target.value)} /></Field>
        </div>
        <Field label="Tatsächlich gestellte Anfrage"><Textarea required maxLength={2000} rows={2} value={prompt} onChange={(e) => setPrompt(e.target.value)} /></Field>
        <Checkbox label="Marke tatsächlich in der Antwort erwähnt" checked={mentioned} onChange={setMentioned} />
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Tatsächlich angegebene Quellen-URL (optional)"><Input type="url" maxLength={2048} value={citedUrl} onChange={(e) => setCitedUrl(e.target.value)} /></Field>
          <Field label="Nachweis-URL (optional)"><Input type="url" maxLength={2048} value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} /></Field>
        </div>
        <Field label="Antwortauszug (optional)"><Textarea maxLength={5000} rows={3} value={excerpt} onChange={(e) => setExcerpt(e.target.value)} /></Field>
        <Field label="Anmerkungen"><Textarea maxLength={5000} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <Button type="submit" variant="primary" loading={add.isPending} disabled={!site}>Stichprobe speichern</Button>
      </form>
      {add.error && <ErrorBox error={add.error} />}
    </Card>
    <Card title="Methodik und Grenzen">
      <p className="text-sm text-slate-600 dark:text-slate-300">Alle Einträge sind manuelle Beobachtungen und werden nicht automatisch verifiziert.
        <strong> Marken-Erwähnung, URL-Zitation und tatsächlicher Websitebesuch sind drei unterschiedliche Sachverhalte.</strong>
        Es gibt keine garantierte Platzierung in generativen Antworten. Der <Link className="underline" to="/geo">GEO-Check</Link> bleibt eine technische Checkliste, keine KI-Reichweitenmessung.
      </p>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {q.isLoading && <Card><Spinner /></Card>}
    {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
    {q.data?.items.length === 0 && <Card><EmptyState title="Noch keine Beobachtungen" description="Eine beantwortete Anfrage mit Kontext und Quellennachweis dokumentieren." /></Card>}
    {q.data?.items.map((o) => <Card key={o.id} title={o.platform + (o.model_name ? " · " + o.model_name : "")}
      description={fmtDateTime(o.observed_at)} actions={<Button size="sm" variant="ghost" disabled={remove.isPending}
        onClick={() => { if (window.confirm("Beobachtung löschen?")) remove.mutate(o.id); }}>Löschen</Button>}>
      <div className="flex flex-wrap gap-2"><Badge>Manuell · unbestätigt</Badge>
        <Badge tone={o.brand_mentioned ? "green" : "gray"}>{o.brand_mentioned ? "Marke erwähnt" : "Marke nicht erwähnt"}</Badge>
        <Badge tone={o.cited_url ? "blue" : "gray"}>{o.cited_url ? "URL zitiert (laut Eintrag)" : "Keine URL erfasst"}</Badge>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm font-medium">{o.prompt}</p>
      {o.cited_url && <p className="mt-2 break-all text-xs">Quellen-URL: {o.cited_url}</p>}
      {o.evidence_url && <p className="mt-1 break-all text-xs">Nachweis: {o.evidence_url}</p>}
      {o.response_excerpt && <blockquote className="mt-2 whitespace-pre-wrap border-l-2 border-slate-300 pl-3 text-sm">{o.response_excerpt}</blockquote>}
      {o.notes && <p className="mt-2 whitespace-pre-wrap text-sm text-slate-500">{o.notes}</p>}
    </Card>)}
    {remove.error && <ErrorBox error={remove.error} />}
    {site && <AiSourceStabilityPanel siteId={site.id} />}
  </div>;
}
