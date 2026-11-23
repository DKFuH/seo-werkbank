import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../lib/api";
import { Button, Card, EmptyState, ErrorBox, Field, Input, Notice, Select, Spinner, Textarea } from "./ui";

type CrawlPage = { url: string; title: string };
type Prefilled = {
  jsonld: Record<string, unknown>; existing: unknown[]; type: string; diff: string[];
  warnings: string[]; validation: { errors: number; warnings: number; findings: unknown[] };
  rich_result_eligibility_confirmed: false;
};
type Template = { id: number; name: string; schema_type: string; url_pattern: string; field_mapping: Record<string, string> };

const TYPES = ["WebPage", "WebSite", "Organization", "LocalBusiness", "Article", "BlogPosting", "Product",
  "BreadcrumbList", "FAQPage", "Service", "Person", "Event"];

export default function SchemaManagementPanel({ siteId }: { siteId: number }) {
  const base = `/sites/${siteId}/schema-manager`;
  const qc = useQueryClient();
  const [url, setUrl] = useState("");
  const [schemaType, setSchemaType] = useState("WebPage");
  const [editor, setEditor] = useState("");
  const [diff, setDiff] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [workId, setWorkId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [pattern, setPattern] = useState("/*");
  const [mapping, setMapping] = useState("{}");
  const [preview, setPreview] = useState<any>(null);
  const [editingTemplateId, setEditingTemplateId] = useState<number | null>(null);

  const pages = useQuery<{ pages: CrawlPage[]; crawl_id: number | null }>({
    queryKey: ["schema-pages", siteId], queryFn: () => api.get(`${base}/pages`),
  });
  const templates = useQuery<Template[]>({
    queryKey: ["schema-templates", siteId], queryFn: () => api.get(`${base}/templates`),
  });
  const fill = useMutation<Prefilled, Error, { url: string; schema_type: string }>({
    mutationFn: (body) => api.post(`${base}/prefill`, body),
    onSuccess: (result) => {
      setEditor(JSON.stringify(result.jsonld, null, 2));
      setDiff(result.diff); setWarnings(result.warnings);
      setWorkId(null); setMessage("Entwurf aus dem letzten Crawl erstellt. Fehlende Fakten manuell ergänzen.");
    },
    onError: e => setMessage(errorMessage(e)),
  });
  const save = useMutation({
    mutationFn: (jsonld: Record<string, unknown>) => api.post(`${base}/proposals`, {
      url, schema_type: schemaType, jsonld,
      rationale: "Aus Crawl vorbefüllt, Änderungen redaktionell prüfen",
    }),
    onSuccess: result => {
      setWorkId(result.work_item_id); setMessage("Schema-Entwurf gespeichert – noch nicht freigegeben.");
    },
    onError: e => setMessage(errorMessage(e)),
  });
  const createTemplate = useMutation({
    mutationFn: (value: Record<string, unknown>) => editingTemplateId != null
      ? api.put(`${base}/templates/${editingTemplateId}`, value) : api.post(`${base}/templates`, value),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["schema-templates", siteId] }); setMessage("Vorlage gespeichert."); setEditingTemplateId(null); },
    onError: e => setMessage(errorMessage(e)),
  });
  const removeTemplate = useMutation({
    mutationFn: (id: number) => api.del(`${base}/templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schema-templates", siteId] }),
    onError: e => setMessage(errorMessage(e)),
  });
  const testTemplate = useMutation({
    mutationFn: (id: number) => api.post(`${base}/templates/${id}/preview`),
    onSuccess: setPreview, onError: e => setMessage(errorMessage(e)),
  });
  const saveJson = () => {
    try {
      const parsed: unknown = JSON.parse(editor);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("JSON-LD muss ein Objekt sein");
      save.mutate(parsed as Record<string, unknown>);
    } catch (error) {
      setMessage(errorMessage(error));
    }
  };
  const saveTemplate = () => {
    try {
      const parsed: unknown = JSON.parse(mapping);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Feldzuordnung muss ein JSON-Objekt sein");
      createTemplate.mutate({ name, url_pattern: pattern, schema_type: schemaType, field_mapping: parsed });
    } catch (error) {
      setMessage(errorMessage(error));
    }
  };
  return <div className="space-y-5">
    <Notice tone="warn">Nur der letzte abgeschlossene Crawl dient als Datenbasis. Ein gültiges Schema bedeutet nicht, dass Google Rich Results anzeigt. Preis, Verfügbarkeit, Anschrift, FAQ-Antworten und Breadcrumb-Namen müssen fachlich bestätigt werden.</Notice>
    <Card title="Schema-Entwurf aus einer Seite erstellen">
      {pages.isLoading ? <Spinner /> : pages.error ? <ErrorBox error={pages.error} onRetry={() => pages.refetch()} /> :
        !pages.data?.pages.length ? <EmptyState title="Zuerst Website crawlen" /> :
        <div className="space-y-3">
          <Field label="Gecrawlte Seite">
            <Select value={url} onChange={e => setUrl(e.target.value)}>
              <option value="">Seite auswählen</option>
              {pages.data.pages.map(p => <option key={p.url} value={p.url}>{p.title ? `${p.title} – ` : ""}{p.url}</option>)}
            </Select>
          </Field>
          <Field label="Schema-Typ">
            <Select value={schemaType} onChange={e => setSchemaType(e.target.value)}>{TYPES.map(t => <option key={t} value={t}>{t}</option>)}</Select>
          </Field>
          <Button variant="primary" disabled={!url || fill.isPending} onClick={() => fill.mutate({ url, schema_type: schemaType })}>Entwurf erstellen</Button>
        </div>}
      {editor && <div className="mt-4 space-y-3">
        <Field label="JSON-LD-Entwurf – bearbeitbar">
          <Textarea value={editor} onChange={e => setEditor(e.target.value)} rows={15} className="font-mono text-xs" />
        </Field>
        {warnings.map((w,i) => <p key={i} className="text-xs text-amber-700 dark:text-amber-300">{w}</p>)}
        <Button disabled={save.isPending} onClick={saveJson}>Als Maßnahme speichern</Button>
        {workId != null && <p className="text-sm">Maßnahme #{workId} gespeichert. <Link className="underline" to={`/content-proposals?item=${workId}`}>Entwurf prüfen und freigeben</Link></p>}
      </div>}
      {diff.length > 0 && <div className="mt-4">
        <h3 className="mb-2 text-sm font-medium">Änderungsübersicht gegenüber Crawl-Markup</h3>
        <pre className="max-h-72 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">{diff.join("\n")}</pre>
      </div>}
      {fill.error && <ErrorBox error={fill.error} />}
      {save.error && <ErrorBox error={save.error} />}
    </Card>
    <Card title="Wiederverwendbare Vorlagen – nur Vorschau">
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Vorlagenname"><Input value={name} onChange={e => setName(e.target.value)} placeholder="Ratgeberartikel" /></Field>
        <Field label="Pfadmuster (Glob)"><Input value={pattern} onChange={e => setPattern(e.target.value)} placeholder="/ratgeber/*" /></Field>
      </div>
      <Field label="Feldzuordnungen als JSON, z. B. {\u0022headline\u0022:\u0022{title}\u0022}">
        <Textarea rows={3} className="font-mono text-xs" value={mapping} onChange={e => setMapping(e.target.value)} />
      </Field>
      <div className="flex flex-wrap gap-2"><Button disabled={!name || createTemplate.isPending} onClick={saveTemplate}>{editingTemplateId != null ? "Vorlage aktualisieren" : "Vorlage speichern"}</Button>
        {editingTemplateId != null && <Button variant="secondary" onClick={() => setEditingTemplateId(null)}>Bearbeitung abbrechen</Button>}</div>
      <div className="mt-4 space-y-2">{templates.isLoading ? <Spinner /> :
        templates.error ? <ErrorBox error={templates.error} onRetry={() => templates.refetch()} /> :
        !(templates.data ?? []).length ? <p className="text-sm text-slate-500">Noch keine Vorlagen.</p> :
        templates.data?.map(t => <div key={t.id} className="flex flex-wrap items-center justify-between gap-2 border-t py-2 text-sm dark:border-slate-800">
          <span>{t.name} · {t.schema_type} · <code>{t.url_pattern}</code></span>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => testTemplate.mutate(t.id)}>Vorschau</Button>
            <Button size="sm" variant="secondary" onClick={() => { setEditingTemplateId(t.id); setName(t.name); setPattern(t.url_pattern); setSchemaType(t.schema_type); setMapping(JSON.stringify(t.field_mapping, null, 2)); }}>Bearbeiten</Button>
            <Button size="sm" variant="danger" onClick={() => removeTemplate.mutate(t.id)}>Löschen</Button>
          </div>
        </div>)}</div>
      {testTemplate.isPending && <Spinner />}
      {preview && <div className="mt-3 text-sm">
        <p>{preview.matched} passende Seiten · {preview.shown} in Vorschau, keine Änderungen gespeichert</p>
        <pre className="mt-2 max-h-72 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(preview.items, null, 2)}</pre>
      </div>}
    </Card>
    {message && <p role="status" className="text-sm">{message}</p>}
  </div>;
}
