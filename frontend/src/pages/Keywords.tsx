import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Layers, Plus, Save, Search, Trash2 } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge, Button, Card, Checkbox, type Column, DataBadge, DataTable, EmptyState, ErrorBox, ExportMenu, Field, FileButton, Input,
  NeedsCrawl, Notice, PageHeader, Pagination, SearchInput, Select, Spinner, Stat, Tabs, Textarea, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum, shortUrl, titleCase } from "../lib/format";

type Tab = "research" | "saved" | "mapping" | "cluster";

const INTENT_TONE: Record<string, string> = { transactional: "green", commercial: "purple", navigational: "blue", local: "orange", informational: "gray" };
const INTENTS = ["informational", "commercial", "transactional", "navigational", "local"];
const TYPES = ["question", "comparison", "preposition", "long-tail", "suggestion"];
const PER_PAGE = 100;

function IntentBadge({ intent, confidence }: { intent: string | null | undefined; confidence?: number | null }) {
  if (!intent) return <span className="text-slate-400">–</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Badge tone={INTENT_TONE[intent] ?? "gray"} title="Regelbasierte Schätzung">{titleCase(intent)}</Badge>
      {confidence !== undefined && confidence !== null && (
        <span className="text-xs tabular-nums text-slate-500 dark:text-slate-400" title="Grobe Sicherheit der regelbasierten Schätzung">{Math.round(confidence * 100)}%</span>
      )}
    </span>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">{children}</span>;
}

function RowCheck({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <input type="checkbox" aria-label={label} checked={checked} onChange={(e) => onChange(e.target.checked)}
      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-900" />
  );
}

function csvCell(v: unknown): string {
  let s = v === null || v === undefined ? "" : String(v);
  if (/^[=+\-@]/.test(s)) s = `'${s}`; // neutralise spreadsheet formula injection
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(filename: string, header: string[], rows: unknown[][]) {
  const text = [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿", text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function parseLines(text: string): string[] {
  return Array.from(new Set(text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)));
}

function ClusterGrid({ clusters }: { clusters: any[] }) {
  const [showAll, setShowAll] = useState<Record<string, boolean>>({});
  if (!clusters.length) return <EmptyState title="Keine Cluster" description="Zu wenige Keywords zum Gruppieren." />;
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {clusters.map((c, i) => {
        const key = `${c.label}-${i}`;
        const kws: string[] = c.keywords ?? [];
        const shown = showAll[key] ? kws : kws.slice(0, 12);
        return (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="min-w-0 break-words text-sm font-semibold text-slate-900 dark:text-slate-100">{c.label}</h3>
              <div className="flex items-center gap-1.5">
                <Badge>{c.size} keyword{c.size === 1 ? "" : "s"}</Badge>
                <IntentBadge intent={c.dominant_intent} />
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {shown.map((k) => <Chip key={k}>{k}</Chip>)}
              {kws.length > 12 && (
                <button className="text-xs font-medium text-brand-700 hover:underline dark:text-brand-300" onClick={() => setShowAll((s) => ({ ...s, [key]: !s[key] }))}>
                  {showAll[key] ? "Weniger anzeigen" : `+${kws.length - 12} weitere`}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ research */
function ResearchTab() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [seed, setSeed] = useState("");
  const [lang, setLang] = useState("en");
  const [country, setCountry] = useState("us");
  const [sources, setSources] = useState<Record<string, boolean>>({ google: true, bing: true, duckduckgo: true });
  const [depth, setDepth] = useState("basic");
  const [view, setView] = useState<"keywords" | "clusters">("keywords");
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [intent, setIntent] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const activeSources = Object.keys(sources).filter((s) => sources[s]);
  const suggest = useMutation({
    mutationFn: () => api.post("/keywords/suggest", { seed: seed.trim(), lang: lang.trim().toLowerCase(), country: country.trim().toLowerCase(), sources: activeSources, depth }),
    onSuccess: () => { setSelected(new Set()); setPage(1); save.reset(); },
  });
  const save = useMutation({
    mutationFn: async (keywords: string[]) => {
      let added = 0;
      let total = 0;
      for (let i = 0; i < keywords.length; i += 2000) {
        const r = await api.post(`/sites/${site!.id}/keywords`, { keywords: keywords.slice(i, i + 2000), source: "suggest" });
        added += r.added;
        total = r.total;
      }
      return { added, total };
    },
    onSuccess: () => {
      setSelected(new Set());
      void qc.invalidateQueries({ queryKey: ["keywords", site?.id] });
      void qc.invalidateQueries({ queryKey: ["keyword-mapping", site?.id] });
    },
  });

  const result = suggest.data;
  const all: any[] = result?.keywords ?? [];
  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return all.filter((k) => (!needle || k.keyword.includes(needle)) && (!type || k.type === type) && (!intent || k.intent === intent));
  }, [all, q, type, intent]);
  const pageRows = visible.slice((page - 1) * PER_PAGE, page * PER_PAGE);
  const allVisibleSelected = visible.length > 0 && visible.every((k) => selected.has(k.keyword));
  const errors = Object.entries((result?.errors ?? {}) as Record<string, string>);

  const toggle = (kw: string, on: boolean) => setSelected((s) => { const n = new Set(s); if (on) n.add(kw); else n.delete(kw); return n; });
  const toggleAll = (on: boolean) => setSelected((s) => { const n = new Set(s); visible.forEach((k) => (on ? n.add(k.keyword) : n.delete(k.keyword))); return n; });

  const submit = (e: FormEvent) => { e.preventDefault(); if (seed.trim() && activeSources.length) suggest.mutate(); };

  const columns: Column<any>[] = [
    { key: "sel", width: "32px", header: <RowCheck label="Alle sichtbaren Keywords auswählen" checked={allVisibleSelected} onChange={toggleAll} />,
      render: (k) => <RowCheck label={`${k.keyword} auswählen`} checked={selected.has(k.keyword)} onChange={(v) => toggle(k.keyword, v)} /> },
    { key: "keyword", header: "Keyword", render: (k) => <span className="font-medium text-slate-900 dark:text-slate-100">{k.keyword}</span> },
    { key: "type", header: "Typ", render: (k) => <Badge tone={k.type === "question" ? "blue" : "gray"}>{titleCase(k.type)}</Badge> },
    { key: "intent", header: <span className="inline-flex items-center gap-1.5">Intention <DataBadge kind="estimated" /></span>,
      render: (k) => <IntentBadge intent={k.intent} confidence={k.intent_confidence} /> },
    { key: "sources", header: "Quellen", tooltip: "Welche Autocomplete-Dienste diesen Vorschlag geliefert haben",
      render: (k) => <span className="flex flex-wrap gap-1">{(k.sources ?? []).map((s: string) => <Chip key={s}>{s}</Chip>)}</span> },
    { key: "words", header: "Wörter", align: "right", render: (k) => k.words },
    { key: "volume", header: "Suchvolumen", tooltip: "Autocomplete liefert kein Suchvolumen. Unter Gespeicherte Keywords eine Keyword-Planer-CSV importieren.",
      render: (k) => (k.search_volume !== null && k.search_volume !== undefined ? fmtInt(k.search_volume) : <DataBadge kind="unavailable" />) },
  ];

  return (
    <div className="space-y-4">
      <Card title="Keyword-Ideen finden" description="Echte Vervollständigungen öffentlicher Autocomplete-Dienste, live abgefragt.">
        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-12">
            <Field label="Ausgangs-Keyword" className="sm:col-span-2 lg:col-span-5">
              <Input required maxLength={120} value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="z. B. küchenplanung" />
            </Field>
            <Field label="Sprache" hint="2-stelliger Code" className="lg:col-span-2">
              <Input required pattern="[A-Za-z]{2}" maxLength={2} value={lang} onChange={(e) => setLang(e.target.value)} placeholder="en" />
            </Field>
            <Field label="Land" hint="2-stelliger Code" className="lg:col-span-2">
              <Input required pattern="[A-Za-z]{2}" maxLength={2} value={country} onChange={(e) => setCountry(e.target.value)} placeholder="us" />
            </Field>
            <Field label="Tiefe" className="lg:col-span-3">
              <Select value={depth} onChange={(e) => setDepth(e.target.value)}>
                <option value="basic">Einfach (Fragen + Präpositionen)</option>
                <option value="deep">Tief (zusätzlich A–Z, langsamer)</option>
              </Select>
            </Field>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Quellen</span>
              <Checkbox label="Google" checked={sources.google} onChange={(v) => setSources((s) => ({ ...s, google: v }))} />
              <Checkbox label="Bing" checked={sources.bing} onChange={(v) => setSources((s) => ({ ...s, bing: v }))} />
              <Checkbox label="DuckDuckGo" checked={sources.duckduckgo} onChange={(v) => setSources((s) => ({ ...s, duckduckgo: v }))} />
            </div>
            <Button type="submit" variant="primary" loading={suggest.isPending} disabled={!seed.trim() || !activeSources.length} icon={<Search className="h-4 w-4" />}>Vorschläge holen</Button>
          </div>
          {!activeSources.length && <p className="text-xs text-amber-700 dark:text-amber-300">Mindestens eine Quelle wählen.</p>}
        </form>
      </Card>

      {suggest.isPending && <Card><Spinner label={depth === "deep" ? "Vorschläge werden gesammelt (tiefer Modus kann eine Minute dauern)…" : "Vorschläge werden gesammelt…"} /></Card>}
      {suggest.error && <ErrorBox error={suggest.error} onRetry={() => suggest.mutate()} />}

      {result && !suggest.isPending && (
        <>
          {errors.length > 0 && (
            <Notice tone="warn">
              <p className="font-medium">Einige Quellen sind fehlgeschlagen und fehlen in den Ergebnissen:</p>
              <ul className="mt-1 list-disc pl-5">{errors.map(([s, m]) => <li key={s}><span className="font-medium">{s}</span>: {m}</li>)}</ul>
            </Notice>
          )}
          {(result.data_notes ?? []).length > 0 && (
            <Notice>
              <ul className="list-disc space-y-0.5 pl-5">{result.data_notes.map((n: string) => <li key={n}>{n}</li>)}</ul>
            </Notice>
          )}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Vorschläge" value={fmtInt(all.length)} hint={`für „${result.seed}“`} />
            <Stat label="Fragen" value={fmtInt(all.filter((k) => k.type === "question").length)} />
            <Stat label="Clusters" value={fmtInt((result.clusters ?? []).length)} tooltip="Lexikalische Gruppierung nach gemeinsamen Wortstämmen. Höchstens 60 Cluster." />
            <Stat label="Autocomplete-Abfragen" value={fmtInt(result.queries)} hint={Object.keys(result.sources ?? {}).join(", ")} />
          </div>

          <Card padded={false}
            title={<span className="inline-flex gap-1">
              {(["keywords", "clusters"] as const).map((v) => (
                <button key={v} onClick={() => setView(v)} aria-pressed={view === v}
                  className={`rounded-md px-2 py-1 text-xs font-medium ${view === v ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}>
                  {v === "keywords" ? `Keywords (${all.length})` : `Clusters (${(result.clusters ?? []).length})`}
                </button>
              ))}
            </span>}
            actions={view === "keywords" ? (
              <>
                <Button size="sm" icon={<Download className="h-3.5 w-3.5" />} disabled={!visible.length}
                  onClick={() => downloadCsv(`keywords-${result.seed.replace(/[^a-z0-9]+/gi, "-")}.csv`,
                    ["keyword", "type", "intent (estimate)", "intent confidence", "sources", "words", "search volume"],
                    visible.map((k) => [k.keyword, k.type, k.intent, k.intent_confidence, (k.sources ?? []).join(" "), k.words, k.search_volume ?? "unavailable"]))}>
                  CSV ({visible.length})
                </Button>
                <Button size="sm" variant="primary" icon={<Save className="h-3.5 w-3.5" />} loading={save.isPending} disabled={!site || !selected.size}
                  title={site ? undefined : "Zum Speichern zuerst eine Website anlegen"} onClick={() => save.mutate(Array.from(selected))}>
                  Auswahl speichern{selected.size ? ` (${selected.size})` : ""}
                </Button>
              </>
            ) : undefined}>
            {view === "keywords" ? (
              <>
                <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
                  <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Keywords filtern…" />
                  <Select className="w-auto" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} aria-label="Nach Typ filtern">
                    <option value="">Alle Typen</option>
                    {TYPES.map((t) => <option key={t} value={t}>{t === "question" ? "Fragen" : titleCase(t)}</option>)}
                  </Select>
                  <Select className="w-auto" value={intent} onChange={(e) => { setIntent(e.target.value); setPage(1); }} aria-label="Nach Suchintention filtern">
                    <option value="">Alle Suchintentionen</option>
                    {INTENTS.map((t) => <option key={t} value={t}>{t}</option>)}
                  </Select>
                  {!site && <span className="text-xs text-slate-500 dark:text-slate-400">Zum Speichern eine Website anlegen.</span>}
                </div>
                {save.error && <div className="p-3"><ErrorBox error={save.error} /></div>}
                {save.data && <div className="p-3"><Notice tone="success">{save.data.added} new keyword{save.data.added === 1 ? "" : "s"} saved to {site?.name}. The site now has {save.data.total} saved keywords.</Notice></div>}
                <DataTable dense columns={columns} rows={pageRows} rowKey={(k) => k.keyword}
                  empty={<EmptyState title={all.length ? "Keine passenden Keywords" : "Keine Vorschläge"}
                    description={all.length ? "Filter oben zurücksetzen oder ändern." : "Die gewählten Quellen lieferten nichts. Allgemeineres Keyword oder andere Sprache/Land versuchen."} />} />
                {visible.length > 0 && <Pagination page={page} perPage={PER_PAGE} total={visible.length} onPage={setPage} />}
              </>
            ) : (
              <div className="p-4"><ClusterGrid clusters={result.clusters ?? []} /></div>
            )}
          </Card>
        </>
      )}

      {!result && !suggest.isPending && !suggest.error && (
        <Card><EmptyState icon={<Search className="h-6 w-6" />} title="Ausgangs-Keyword eingeben"
          description="Vorschläge kommen live aus Autocomplete-Diensten. Suchvolumen wird nie erfunden, sondern nur nach Import angezeigt." /></Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ saved */
function SavedTab() {
  const { site } = useSite();
  const qc = useQueryClient();
  const siteId = site?.id;
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [adding, setAdding] = useState(false);
  const [manual, setManual] = useState("");

  const list = useQuery({ queryKey: ["keywords", siteId], queryFn: () => api.get(`/sites/${siteId}/keywords`), enabled: !!siteId });
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["keywords", siteId] });
    void qc.invalidateQueries({ queryKey: ["keyword-mapping", siteId] });
  };
  const add = useMutation({
    mutationFn: (keywords: string[]) => api.post(`/sites/${siteId}/keywords`, { keywords, source: "manual" }),
    onSuccess: () => { setManual(""); invalidate(); },
  });
  const importCsv = useMutation({ mutationFn: (file: File) => api.upload(`/sites/${siteId}/keywords/import`, file), onSuccess: invalidate });
  const remove = useMutation({
    mutationFn: (ids: number[]) => api.del(`/sites/${siteId}/keywords`, ids),
    onSuccess: () => { setSelected(new Set()); invalidate(); },
  });

  const items: any[] = list.data?.items ?? [];
  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? items.filter((k) => k.keyword.includes(needle) || (k.cluster ?? "").includes(needle)) : items;
  }, [items, q]);

  if (!site) return <NeedsCrawl hasSite={false} />;

  const pageRows = visible.slice((page - 1) * PER_PAGE, page * PER_PAGE);
  const allSelected = visible.length > 0 && visible.every((k) => selected.has(k.id));
  const toggle = (id: number, on: boolean) => setSelected((s) => { const n = new Set(s); if (on) n.add(id); else n.delete(id); return n; });
  const manualList = parseLines(manual);
  const legend = (list.data?.legend ?? {}) as Record<string, string>;
  const dash = <span className="text-slate-400">–</span>;

  const columns: Column<any>[] = [
    { key: "sel", width: "32px", header: <RowCheck label="Alle auswählen" checked={allSelected} onChange={(on) => setSelected(on ? new Set(visible.map((k) => k.id)) : new Set())} />,
      render: (k) => <RowCheck label={`${k.keyword} auswählen`} checked={selected.has(k.id)} onChange={(v) => toggle(k.id, v)} /> },
    { key: "keyword", header: "Keyword", render: (k) => <span className="font-medium text-slate-900 dark:text-slate-100">{k.keyword}</span> },
    { key: "cluster", header: "Cluster", tooltip: "Lexikalisches Cluster, neu berechnet, sobald Keywords hinzukommen", render: (k) => (k.cluster ? <Chip>{k.cluster}</Chip> : dash) },
    { key: "intent", header: <span className="inline-flex items-center gap-1.5">Intention <DataBadge kind="estimated" /></span>, render: (k) => <IntentBadge intent={k.intent} /> },
    { key: "clicks", header: <span className="inline-flex items-center gap-1.5">Klicks <DataBadge kind="measured" /></span>, align: "right", render: (k) => (k.gsc ? fmtInt(k.gsc.clicks) : dash) },
    { key: "impressions", header: "Impressionen", align: "right", tooltip: "Google Search Console, gemessen", render: (k) => (k.gsc ? fmtInt(k.gsc.impressions) : dash) },
    { key: "position", header: "Ø Position", align: "right", tooltip: "Google Search Console, nach Impressionen gewichteter Durchschnitt", render: (k) => (k.gsc && k.gsc.position !== null ? fmtNum(k.gsc.position) : dash) },
    { key: "volume", header: <span className="inline-flex items-center gap-1.5">Volumen <DataBadge kind="imported" /></span>, align: "right",
      render: (k) => (k.volume_status === "imported" ? fmtInt(k.search_volume) : <DataBadge kind="unavailable" />) },
    { key: "competition", header: "Wettbewerb", tooltip: "Aus deiner importierten Datei, unverändert", render: (k) => k.imported?.competition ?? dash },
    { key: "source", header: "Quelle", render: (k) => <Badge>{k.source}</Badge> },
  ];

  return (
    <div className="space-y-4">
      {Object.keys(legend).length > 0 && (
        <Notice>
          <div className="flex flex-wrap gap-x-6 gap-y-1.5">
            {legend.gsc && <span className="inline-flex items-center gap-1.5"><DataBadge kind="measured" /> {legend.gsc}</span>}
            {legend.imported && <span className="inline-flex items-center gap-1.5"><DataBadge kind="imported" /> {legend.imported}</span>}
            {legend.unavailable && <span className="inline-flex items-center gap-1.5"><DataBadge kind="unavailable" /> {legend.unavailable}</span>}
            <span className="inline-flex items-center gap-1.5"><DataBadge kind="estimated" /> Intentionen sind regelbasierte Schätzungen</span>
          </div>
        </Notice>
      )}
      {list.data && !list.data.has_gsc_data && (
        <Notice tone="warn">Für diese Website gibt es noch keine Search-Console-Daten, Klicks, Impressionen und Position bleiben leer. <Link to="/search-console" className="font-medium underline">Search Console verbinden oder Daten importieren</Link>.</Notice>
      )}

      <Card padded={false} title={`Gespeicherte Keywords für ${site.name}`}
        actions={<>
          <Button size="sm" icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setAdding((a) => !a)}>Keywords hinzufügen</Button>
          <FileButton label="Keyword-Planer-CSV importieren" loading={importCsv.isPending} onFile={(f) => importCsv.mutate(f)} />
          <ExportMenu formats={[
            { label: "CSV", path: `/sites/${site.id}/keywords/export`, query: { format: "csv" } },
            { label: "Excel (XLSX, mit Seitenzuordnung)", path: `/sites/${site.id}/keywords/export`, query: { format: "xlsx" } },
          ]} />
        </>}>
        {adding && (
          <div className="space-y-2 border-b border-slate-100 p-3 dark:border-slate-800">
            <Field label="Keywords, eines pro Zeile" hint={`${manualList.length} ${manualList.length === 1 ? "Keyword" : "Keywords"} (max. 2.000 pro Durchgang). Duplikate werden übersprungen.`}>
              <Textarea rows={5} value={manual} onChange={(e) => setManual(e.target.value)} placeholder={"küche planen\nküchenstudio in der nähe"} />
            </Field>
            <div className="flex gap-2">
              <Button variant="primary" size="sm" loading={add.isPending} disabled={!manualList.length || manualList.length > 2000} onClick={() => add.mutate(manualList)}>Keywords speichern</Button>
              <Button variant="ghost" size="sm" onClick={() => setAdding(false)}>Schließen</Button>
            </div>
          </div>
        )}
        {(add.error || importCsv.error || remove.error || add.data || importCsv.data) && (
          <div className="space-y-2 p-3">
            {add.error && <ErrorBox error={add.error} />}
            {importCsv.error && <ErrorBox error={importCsv.error} />}
            {remove.error && <ErrorBox error={remove.error} />}
            {add.data && <Notice tone="success">{add.data.added} {add.data.added === 1 ? "Keyword" : "Keywords"} hinzugefügt ({add.data.total} insgesamt gespeichert).</Notice>}
            {importCsv.data && <Notice tone="success">Import fertig: {importCsv.data.added} neu, {importCsv.data.updated} mit importierten Werten aktualisiert.</Notice>}
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Nach Keyword oder Cluster filtern…" />
          <Button size="sm" variant="danger" icon={<Trash2 className="h-3.5 w-3.5" />} disabled={!selected.size} loading={remove.isPending}
            onClick={() => remove.mutate(Array.from(selected))}>Delete selected{selected.size ? ` (${selected.size})` : ""}</Button>
        </div>
        {list.isLoading ? <Spinner /> : list.error ? <div className="p-3"><ErrorBox error={list.error} onRetry={() => list.refetch()} /></div> : (
          <>
            <DataTable dense columns={columns} rows={pageRows} rowKey={(k) => k.id}
              empty={<EmptyState title={items.length ? "Keine passenden Keywords" : "Noch keine gespeicherten Keywords"}
                description={items.length ? "Filter zurücksetzen, um alle Keywords zu sehen." : "Vorschläge aus dem Reiter Recherche speichern, Keywords manuell anlegen oder eine CSV aus dem Google-Ads-Keyword-Planer importieren (Keyword, Avg. monthly searches, Competition)."} />} />
            {visible.length > 0 && <Pagination page={page} perPage={PER_PAGE} total={visible.length} onPage={setPage} />}
          </>
        )}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ mapping */
function MappingTab() {
  const { site } = useSite();
  const siteId = site?.id;
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const mapping = useQuery({ queryKey: ["keyword-mapping", siteId], queryFn: () => api.get(`/sites/${siteId}/keywords/mapping`), enabled: !!siteId });

  if (!site) return <NeedsCrawl hasSite={false} />;
  if (mapping.isLoading) return <Card><Spinner label="Keywords werden mit den gecrawlten Seiten abgeglichen…" /></Card>;
  if (mapping.error) return <ErrorBox error={mapping.error} onRetry={() => mapping.refetch()} />;

  const data = mapping.data ?? {};
  const items: any[] = data.items ?? [];
  const summary = (data.summary ?? {}) as Record<string, number>;
  const visible = status ? items.filter((i) => i.status === status) : items;
  const pageRows = visible.slice((page - 1) * PER_PAGE, page * PER_PAGE);
  const tone: Record<string, string> = { mapped: "green", "cannibalisation risk": "orange", "no matching page": "gray" };

  if (!data.crawl_id) {
    return <Card><EmptyState title="Noch kein abgeschlossener Crawl" description={data.message ?? "Zuerst crawlen, damit Keywords Seiten zugeordnet werden können."}
      action={<Link to="/crawler" className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">Zum Crawler</Link>} /></Card>;
  }

  const columns: Column<any>[] = [
    { key: "keyword", header: "Keyword", render: (i) => <span className="font-medium text-slate-900 dark:text-slate-100">{i.keyword}</span> },
    { key: "status", header: "Status", render: (i) => <Badge tone={tone[i.status] ?? "gray"}>{({ mapped: "zugeordnet", "cannibalisation risk": "Kannibalisierungsrisiko", "no matching page": "keine passende Seite" } as Record<string, string>)[i.status] ?? i.status}</Badge> },
    { key: "best", header: "Passendste Seite", render: (i) => i.best_page ? (
      <div className="max-w-md">
        <Url href={i.best_page.url} label={shortUrl(i.best_page.url, site.url)} />
        <div className="text-xs text-slate-500 dark:text-slate-400">{i.best_page.title || "Kein Title"} · Relevanz {fmtNum(i.best_page.score, 2)}</div>
      </div>
    ) : <span className="text-slate-400">Keine Seite erreicht die Relevanzschwelle</span> },
    { key: "competing", header: "Konkurrierende Seiten", tooltip: "Andere Seiten mit mindestens 85 % der Relevanz der besten Seite", render: (i) => (i.competing_pages ?? []).length ? (
      <ul className="max-w-md space-y-1">
        {i.competing_pages.map((c: any) => (
          <li key={c.url}><Url href={c.url} label={shortUrl(c.url, site.url)} /> <span className="text-xs text-slate-500 dark:text-slate-400">({fmtNum(c.score, 2)})</span></li>
        ))}
      </ul>
    ) : <span className="text-slate-400">–</span> },
  ];

  return (
    <div className="space-y-4">
      <Notice>
        <span className="mr-1.5"><DataBadge kind="estimated" /></span>
        Onpage-Relevanzschätzung: Jedes gespeicherte Keyword wird mit Title, H1, URL, Meta-Description und Text der indexierbaren Seiten des letzten Crawls abgeglichen. Das zeigt, welche Seite ein Keyword am stärksten bedient, nicht welche dafür rankt. Gemessene Kannibalisierung siehe <Link to="/search-console" className="font-medium underline">Search-Console-Auswertungen</Link>.
      </Notice>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Zugeordnet" value={fmtInt(summary.mapped ?? 0)} tone="good" hint="Eine klar beste Seite" />
        <Stat label="Kannibalisierungsrisiko" value={fmtInt(summary["cannibalisation risk"] ?? 0)} tone={summary["cannibalisation risk"] ? "warn" : undefined} hint="Mehrere Seiten konkurrieren" />
        <Stat label="Keine passende Seite" value={fmtInt(summary["no matching page"] ?? 0)} hint="Kandidaten für Inhaltslücken" />
        <Stat label="Berücksichtigte Seiten" value={fmtInt(data.pages_considered)} hint="Indexierbare Seiten im letzten Crawl" />
      </div>
      <Card padded={false} title="Zuordnung Keyword zu Seite" description="Bis zu 500 gespeicherte Keywords werden zugeordnet."
        actions={<Select className="w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Nach Status filtern">
          <option value="">Alle Status</option>
          <option value="mapped">Zugeordnet</option>
          <option value="cannibalisation risk">Kannibalisierungsrisiko</option>
          <option value="no matching page">Keine passende Seite</option>
        </Select>}>
        <DataTable columns={columns} rows={pageRows} rowKey={(i) => i.keyword}
          empty={<EmptyState title={items.length ? "Keine Keywords mit diesem Status" : "Keine gespeicherten Keywords zum Zuordnen"}
            description={items.length ? "Anderen Status wählen." : "Zuerst Keywords aus der Recherche speichern oder unter Gespeicherte Keywords anlegen."} />} />
        {visible.length > 0 && <Pagination page={page} perPage={PER_PAGE} total={visible.length} onPage={setPage} />}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ cluster tool */
function ClusterTab() {
  const [text, setText] = useState("");
  const [seed, setSeed] = useState("");
  const [threshold, setThreshold] = useState(0.5);
  const keywords = parseLines(text);
  const cluster = useMutation({ mutationFn: () => api.post("/keywords/cluster", { keywords, seed: seed.trim() || null, threshold }) });
  const clusters: any[] = cluster.data?.clusters ?? [];

  return (
    <div className="space-y-4">
      <Card title="Keyword-Liste clustern" description="Beliebige Keyword-Liste nach gemeinsamen Begriffen gruppieren. Es wird nichts aus dem Netz geladen.">
        <div className="grid gap-4 lg:grid-cols-3">
          <Field label="Keywords, eines pro Zeile" className="lg:col-span-2" hint={`${keywords.length} eindeutige ${keywords.length === 1 ? "Keyword" : "Keywords"} (max. 3.000)`}>
            <Textarea rows={9} value={text} onChange={(e) => setText(e.target.value)} placeholder={"küche planen\nküche planen kosten\nküche planen online"} />
          </Field>
          <div className="space-y-4">
            <Field label="Ausgangsbegriff ignorieren (optional)" hint="Wörter des Ausgangsbegriffs werden ignoriert, damit die Cluster die Zusätze zeigen.">
              <Input maxLength={120} value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="küche planen" />
            </Field>
            <Field label={`Ähnlichkeitsschwelle: ${threshold.toFixed(2)}`} hint="Niedriger fasst mehr Keywords zu weniger, breiteren Clustern zusammen. Höher hält Cluster eng.">
              <input type="range" min={0.1} max={1} step={0.05} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}
                className="w-full accent-brand-600" aria-label="Ähnlichkeitsschwelle" />
            </Field>
            <Button variant="primary" icon={<Layers className="h-4 w-4" />} loading={cluster.isPending} disabled={!keywords.length || keywords.length > 3000} onClick={() => cluster.mutate()}>Keywords clustern</Button>
          </div>
        </div>
      </Card>
      {cluster.error && <ErrorBox error={cluster.error} onRetry={() => cluster.mutate()} />}
      {cluster.isPending && <Card><Spinner label="Clustere…" /></Card>}
      {cluster.data && !cluster.isPending && (
        <Card title={`${clusters.length} Cluster`}
          description={<span className="inline-flex flex-wrap items-center gap-1.5">Method: {cluster.data.method}. Dominant intent is a rule-based estimate. <DataBadge kind="estimated" /></span>}
          actions={<Button size="sm" icon={<Download className="h-3.5 w-3.5" />} disabled={!clusters.length}
            onClick={() => downloadCsv("keyword-clusters.csv", ["cluster", "cluster size", "dominant intent (estimate)", "keyword"],
              clusters.flatMap((c) => (c.keywords as string[]).map((k) => [c.label, c.size, c.dominant_intent, k])))}>CSV</Button>}>
          <ClusterGrid clusters={clusters} />
        </Card>
      )}
    </div>
  );
}

export default function Keywords() {
  const [tab, setTab] = useState<Tab>("research");
  return (
    <div>
      <PageHeader title="Keyword-Recherche"
        description="Keyword-Ideen aus Live-Autocomplete finden, in Cluster gruppieren und deinen Seiten zuordnen. Nachfragezahlen erscheinen nur, wenn die Search Console sie misst oder du sie importierst." />
      <Tabs<Tab> value={tab} onChange={setTab} tabs={[
        { id: "research", label: "Recherche" },
        { id: "saved", label: "Gespeicherte Keywords" },
        { id: "mapping", label: "Seitenzuordnung & Kannibalisierung" },
        { id: "cluster", label: "Cluster-Werkzeug" },
      ]} />
      {tab === "research" && <ResearchTab />}
      {tab === "saved" && <SavedTab />}
      {tab === "mapping" && <MappingTab />}
      {tab === "cluster" && <ClusterTab />}
    </div>
  );
}
