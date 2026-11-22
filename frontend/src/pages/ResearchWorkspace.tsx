import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Kind = "directory_assessment" | "case_study" | "buyer_question" | "brand_claim" | "marketing_experiment" | "funnel_step" | "trust_proof" | "brand_profile" | "topic_map" | "paa_question" | "search_journey" | "content_evidence" | "cro_review" |
  "comparison" | "asset_brief" | "indexing" | "serp_feature" | "update_event" | "geo_sample";
type RecordItem = { id: number; kind: Kind; title: string; payload: Record<string, string | string[]>; notes: string; source: string };
type Result = { items: RecordItem[]; categories: string[]; method: string };
type Fields = { title: string; keys: string[]; helper: string };
const categories: Record<Kind, Fields> = {
  directory_assessment: { title: "Verzeichnisqualität", keys: ["directory", "listing_url", "relevance", "editorial_value", "cost_eur", "referral_visits", "source_note"], helper: "Relevanz und redaktionellen Nutzwert als eigene Einschätzung 0–3 bewerten. Tatsächliche Kosten/Besuche nur mit Beleg eingeben." },
  case_study: { title: "Fallstudie mit Belegen", keys: ["project", "challenge", "approach", "outcome", "target_url", "evidence_url", "evidence_note"], helper: "Nur belegte eigene Projektdaten; veröffentlichte Aussagen gesondert prüfen" },
  buyer_question: { title: "Echte Kundenfrage", keys: ["question", "context", "audience", "source_note", "suggested_url"], helper: "Frage anonymisieren, keine personenbezogenen Kundendaten eingeben" },
  brand_claim: { title: "Externe Markenaussage", keys: ["subject", "claim", "source_url", "expected_statement", "checked_at"], helper: "Nur tatsächliche Quellen dokumentieren; URL nicht als Beweis der Wahrheit verstehen" },
  marketing_experiment: { title: "Marketing-Experiment", keys: ["hypothesis", "metric", "unit", "start_date", "end_date", "baseline", "followup", "cost", "source_note"], helper: "Messwerte nur mit gleicher Einheit und vergleichbarem Zeitraum interpretieren; nicht kausal" },
  funnel_step: { title: "Conversion-Funnel-Schritt", keys: ["page_url", "stage", "action", "action_url", "friction", "form_fields", "evidence_url"], helper: "Stufe und Handlungsaufforderung dokumentieren; Formularfelder/Probleme manuell erfassen" },
  trust_proof: { title: "Vertrauensnachweis", keys: ["page_url", "claim", "proof_type", "proof_url", "checked_at"], helper: "Eine konkrete belegbare Aussage statt automatischer Vertrauens-Scores" },
  brand_profile: { title: "Markenpositionierung", keys: ["brand_name", "positioning", "offer", "audience", "tone", "evidence_url"], helper: "Leistungsversprechen, Zielgruppen und Quellen der eigenen Marke" },
  topic_map: { title: "Geschäftsbezogene Themenlandkarte", keys: ["offer", "attributes", "audience", "excluded_topics"], helper: "Attribute und Ausschlüsse mit Komma trennen" },
  paa_question: { title: "PAA-Fragenhierarchie", keys: ["topic", "question", "evidence_url"], helper: "Nur belegte Fragen erfassen; keine Live-PAA-Daten behaupten" },
  search_journey: { title: "Suchreise und Linkpfad", keys: ["source_url", "target_url", "stage", "intent"], helper: "Stage: awareness, consideration, decision oder conversion" },
  content_evidence: { title: "Content-Nachweise", keys: ["page_url", "claim", "evidence_url", "evidence_type"], helper: "Behauptung mit tatsächlicher Quelle und manuellem Prüfstatus dokumentieren" },
  cro_review: { title: "Landingpage-CRO-Audit", keys: ["page_url", "criterion", "result", "evidence_url"], helper: "Prüfungen sind Beobachtungen, keine gemessenen Conversion-Lifts" },
  comparison: { title: "Vergleichs-/Alternativen-Audit", keys: ["subject_a", "subject_b", "criterion", "source_url", "observed_value"], helper: "Vergleichsbehauptungen mit Quellen und Datum belegen" },
  asset_brief: { title: "Linkable-Asset-Briefing", keys: ["purpose", "audience", "format", "target_url", "success_metric"], helper: "Tool, Checkliste oder Rechner planen; kein automatisch erzeugter Website-Code" },
  indexing: { title: "Indexierungsprotokoll", keys: ["page_url", "status", "evidence_url"], helper: "Technische Crawl-Signale sind keine bestätigte Google-Indexierung" },
  serp_feature: { title: "SERP-Feature-Beobachtung", keys: ["keyword", "provider", "features", "country", "device"], helper: "Features mit Komma trennen und den Datenanbieter dokumentieren" },
  update_event: { title: "SEO-Änderungsjournal", keys: ["event_date", "event_type", "description", "affected_url"], helper: "Datierte Ereignisse; Beobachtungen sind kein Kausalitätsnachweis" },
  geo_sample: { title: "GEO-Quellenstichprobe", keys: ["platform", "prompt", "response", "cited_urls"], helper: "Zitierte URLs mit Komma trennen; keine repräsentative AI-Sichtbarkeit" },
};
const arrayKeys = new Set(["attributes", "excluded_topics", "features", "cited_urls"]);

export default function ResearchWorkspace() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [kind, setKind] = useState<Kind>("topic_map");
  const [title, setTitle] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState("");
  const [filter, setFilter] = useState<Kind | "all">("all");
  const path = "/sites/" + site?.id + "/research";
  const key = ["seo-research", site?.id];
  const q = useQuery<Result>({ queryKey: key, queryFn: () => api.get(path), enabled: !!site });
  const topic = useQuery<{ items: { offer: string; attribute: string; heading_match_count: number }[] }>({
    queryKey: ["research-topic", site?.id], queryFn: () => api.get(path + "/topic-coverage"), enabled: !!site });
  const journey = useQuery<{ items: { title: string; stage: string; link_observed: boolean | null }[] }>({
    queryKey: ["research-journey", site?.id], queryFn: () => api.get(path + "/journeys"), enabled: !!site });
  const questions = useQuery<{ topics: { topic: string; questions: { question: string }[] }[] }>({
    queryKey: ["research-questions", site?.id], queryFn: () => api.get(path + "/question-tree"), enabled: !!site });
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: key });
    for (const k of ["research-topic", "research-journey", "research-questions"]) {
      void qc.invalidateQueries({ queryKey: [k, site?.id] });
    }
  };
  const add = useMutation({ mutationFn: () => {
    const payload: Record<string, string | string[]> = {};
    for (const name of categories[kind].keys) {
      const value = (values[name] ?? "").trim();
      if (value) payload[name] = arrayKeys.has(name) ? value.split(",").map((v) => v.trim()).filter(Boolean) : value;
    }
    return api.post(path, { kind, title, payload, notes, source: "manual" });
  }, onSuccess: () => { setTitle(""); setValues({}); setNotes(""); refresh(); } });
  const remove = useMutation({ mutationFn: (id: number) => api.del(path + "/" + id), onSuccess: refresh });
  const entries = (q.data?.items ?? []).filter((r) => filter === "all" || r.kind === filter);
  const inputField = (name: string) => <Field key={name} label={name.replaceAll("_", " ")}>
    <Input value={values[name] ?? ""} maxLength={3000} onChange={(e) => setValues((prev) => ({ ...prev, [name]: e.target.value }))}
      required={["offer", "attributes", "topic", "question", "source_url", "target_url", "stage", "page_url", "claim",
        "criterion", "result", "subject_a", "subject_b", "purpose", "audience", "format", "status",
        "keyword", "provider", "features", "event_date", "event_type", "description", "platform", "prompt", "response",
        "action", "brand_name", "positioning", "offer", "project", "challenge", "approach", "outcome",
        "context", "audience", "subject", "source_url", "hypothesis", "metric", "unit", "start_date",
        "directory", "listing_url", "relevance", "editorial_value"].includes(name)} />
  </Field>;
  return <div className="space-y-4">
    <PageHeader title="SEO-Research-Workspace" description="Geschäftsbezogene Themen, echte Fragen, Inhaltsnachweise und Analysebeobachtungen mit sichtbarer Herkunft dokumentieren." />
    <Card title="Rechercheeintrag erstellen" description={categories[kind].helper}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Funktion"><Select value={kind} onChange={(e) => { setKind(e.target.value as Kind); setValues({}); }}>
          {(Object.keys(categories) as Kind[]).map((k) => <option key={k} value={k}>{categories[k].title}</option>)}
        </Select></Field>
        <Field label="Titel"><Input required maxLength={300} value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <div className="grid gap-3 md:grid-cols-2">{categories[kind].keys.map(inputField)}</div>
        <Field label="Redaktionelle Notizen"><Textarea rows={2} maxLength={5000} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <Button type="submit" variant="primary" loading={add.isPending} disabled={!site}>Eintrag speichern</Button>
      </form>
      {add.error && <ErrorBox error={add.error} />}
      <p className="mt-3 text-xs text-slate-500">Nur selbst eingetragene bzw. importierte Beobachtungen. Keine automatische Veröffentlichung, keine behaupteten Google-Rankingfaktoren.</p>
    </Card>
    <Card title="Erfasste Einträge">
      <Field label="Kategorie"><Select value={filter} onChange={(e) => setFilter(e.target.value as Kind | "all")}>
        <option value="all">Alle Kategorien</option>
        {(Object.keys(categories) as Kind[]).map((k) => <option key={k} value={k}>{categories[k].title}</option>)}
      </Select></Field>
      {!site && <EmptyState title="Website auswählen" />}
      {q.isLoading && <Spinner />}
      {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
      {entries.length === 0 && site && !q.isLoading && <EmptyState title="Keine passenden Einträge" />}
      <div className="mt-3 space-y-3">{entries.map((r) => <div key={r.id} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
        <div className="flex items-center justify-between gap-2">
          <strong>{r.title}</strong><Button size="sm" variant="ghost" disabled={remove.isPending}
            onClick={() => { if (window.confirm("Rechercheeintrag löschen?")) remove.mutate(r.id); }}>Löschen</Button>
        </div>
        <Badge>{categories[r.kind].title}</Badge>
        <p className="mt-2 whitespace-pre-wrap break-words text-xs text-slate-500">{Object.entries(r.payload)
          .map(([k, v]) => k + ": " + (Array.isArray(v) ? v.join(", ") : v)).join(" · ")}</p>
        {r.notes && <p className="mt-1 whitespace-pre-wrap text-xs">{r.notes}</p>}
      </div>)}</div>
    </Card>
    {topic.data && topic.data.items.length > 0 && <Card title="Überschriften-Wortabgleich">
      <p className="mb-2 text-xs text-slate-500">Worttreffer in gecrawlten H1/Titeln – keine bestätigte Themenabdeckung.</p>
      {topic.data.items.slice(0, 60).map((x, i) => <p className="text-sm" key={i}>
        {x.offer} · {x.attribute}: {x.heading_match_count} passende Seitentitel/H1</p>)}
    </Card>}
    {journey.data && journey.data.items.length > 0 && <Card title="Geplante Suchreisen">
      {journey.data.items.map((x) => <p className="text-sm" key={x.title + x.stage}>
        {x.title} ({x.stage}): {x.link_observed === null ? "kein Crawl" : x.link_observed ? "Link beobachtet" : "Link im Crawl nicht gefunden"}</p>)}
    </Card>}
    {questions.data && questions.data.topics.length > 0 && <Card title="Fragenhierarchie">
      {questions.data.topics.map((x) => <div key={x.topic} className="mb-2 text-sm">
        <strong>{x.topic}</strong><ul className="ml-4 list-disc">{x.questions.map((q) => <li key={q.question}>{q.question}</li>)}</ul>
      </div>)}
    </Card>}
    {remove.error && <ErrorBox error={remove.error} />}
  </div>;
}
