import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ChevronDown, ChevronUp, Play, Square, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, Checkbox, chartColors, type Column, DataTable, EmptyState, ErrorBox, ExportMenu, Field, Input, Modal, Notice,
  PageHeader, Pagination, ProgressBar, SearchInput, Select, Spinner, Stat, StatusCode, Tabs, Textarea, Url,
} from "../components/ui";
import { RelaunchPanel } from "../components/AdvancedSeoPanels";
import { api } from "../lib/api";
import { type CrawlSummary, useSite } from "../lib/context";
import { fmtBytes, fmtDateTime, fmtInt, fmtMs, fmtNum, scoreColor, shortUrl, timeAgo, titleCase } from "../lib/format";

/* ------------------------------------------------------------------ crawl configuration form (shared with the Websites page) */
export type CrawlCfg = Record<string, any>;

/** Drop empty values so the backend applies its defaults, and tidy pattern lists. */
export function cleanConfig(cfg: CrawlCfg): CrawlCfg {
  const out: CrawlCfg = {};
  for (const [k, v] of Object.entries(cfg)) {
    if (v === "" || v === null || v === undefined || (typeof v === "number" && Number.isNaN(v))) continue;
    if (Array.isArray(v)) out[k] = v.map((s) => String(s).trim()).filter(Boolean);
    else if (typeof v === "string") {
      if (v.trim()) out[k] = v.trim();
    } else out[k] = v;
  }
  return out;
}

export function CrawlConfigForm({ value, onChange, advanced = false }: { value: CrawlCfg; onChange: (v: CrawlCfg) => void; advanced?: boolean }) {
  const set = (k: string, v: any) => onChange({ ...value, [k]: v });
  const num = (k: string, label: string, hint: string, min: number, max?: number, step = 1) => (
    <Field label={label} hint={hint}>
      <Input type="number" inputMode="numeric" min={min} max={max} step={step} value={value[k] ?? ""}
        onChange={(e) => set(k, e.target.value === "" ? "" : Number(e.target.value))} />
    </Field>
  );
  const flag = (k: string, label: string, hint: string) => <Checkbox label={label} hint={hint} checked={!!value[k]} onChange={(v) => set(k, v)} />;
  const patterns = (k: string, label: string, hint: string, placeholder: string) => (
    <Field label={label} hint={hint}>
      <Textarea rows={3} spellCheck={false} placeholder={placeholder} className="font-mono text-xs"
        value={(value[k] ?? []).join("\n")} onChange={(e) => set(k, e.target.value.split("\n"))} />
    </Field>
  );
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {num("max_urls", "Max. URLs", "Nach so vielen URLs stoppen. Der Server kann ein niedrigeres Limit erzwingen.", 1)}
        {num("max_depth", "Max. Tiefe", "Klicks ab der Start-URL (0–100).", 0, 100)}
        {num("concurrency", "Parallelität", "Gleichzeitige Anfragen (1–32). Bei kleinen Servern niedrig halten.", 1, 32)}
        {num("delay_ms", "Pause (ms)", "Pause zwischen Anfragen, um den Server zu schonen (0–60000).", 0, 60000, 50)}
        {advanced && num("timeout_s", "Timeout (s)", "Zeitlimit pro Anfrage (2–120).", 2, 120)}
        {advanced && num("retries", "Wiederholungen", "Wiederholungen bei Fehlern (0–5).", 0, 5)}
        {advanced && num("max_external_links", "Max. externe Links", "Externe Links für die Statusprüfung (0–20000).", 0, 20000)}
        {advanced && num("max_images", "Max. Bilder", "Bilder für die Statusprüfung (0–5000).", 0, 5000)}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {flag("respect_robots", "robots.txt beachten", "Für Crawler gesperrte URLs auslassen.")}
        {flag("use_sitemaps", "XML-Sitemaps nutzen", "URLs aus Sitemaps finden und prüfen.")}
        {flag("include_subdomains", "Subdomains einbeziehen", "Subdomains als Teil der Website behandeln.")}
        {flag("follow_nofollow", "nofollow-Links folgen", "Auch Links mit rel=nofollow crawlen.")}
        {flag("check_external_links", "Externe Links prüfen", "Ausgehende Links abrufen, um defekte zu finden.")}
        {flag("check_images", "Bilder prüfen", "Bilder abrufen, um defekte oder zu große Dateien zu finden.")}
        {flag("render_js", "JavaScript rendern", "Braucht Playwright auf dem Server. Deutlich langsamer.")}
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {patterns("include_patterns", "Einschluss-Muster", "Eines pro Zeile, reiner Text. * steht für beliebige Zeichen, ^ für den Anfang, $ für das Ende. Wenn gesetzt, werden nur passende URLs gecrawlt (max. 20).", "^https://example.com/blog/")}
        {patterns("exclude_patterns", "Ausschluss-Muster", "Eines pro Zeile, reiner Text. * steht für beliebige Zeichen, ^ für den Anfang, $ für das Ende. Passende URLs werden übersprungen (max. 20).", "?sort=\n/cart\n.pdf$")}
      </div>
      {advanced && (
        <Field label="User-Agent" hint="Leer lassen für den Standard-User-Agent des Tools.">
          <Input value={value.user_agent ?? ""} maxLength={300} onChange={(e) => set("user_agent", e.target.value)} placeholder="Standard" />
        </Field>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ small helpers */
const ACTIVE = ["queued", "running"];
const STATUS_TONE: Record<string, string> = { completed: "green", running: "blue", queued: "gray", failed: "red", cancelled: "amber" };
const STATUS_CLASS_COLOR: Record<string, string> = { "2xx": "#16a34a", "3xx": "#3866f5", "4xx": "#ea580c", "5xx": "#dc2626", error: "#991b1b", blocked: "#64748b", "1xx": "#0891b2" };
const tooltipStyle = { background: "#0f172a", border: "none", borderRadius: 8, color: "#f1f5f9", fontSize: 12 };
const axisTick = { fontSize: 11, fill: "#94a3b8" };

export function CrawlStatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "gray"}>{titleCase(status)}</Badge>;
}

function Score({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-slate-400">–</span>;
  return <span className="font-semibold tabular-nums" style={{ color: scoreColor(value) }}>{fmtNum(value, 0)}</span>;
}

function DistChart({ data, color, vertical }: { data: { name: string; value: number }[]; color?: (name: string, i: number) => string; vertical?: boolean }) {
  if (!data.length) return <EmptyState title="Keine Daten" description="Dieser Crawl hat dafür nichts erfasst." />;
  const fill = (name: string, i: number) => (color ? color(name, i) : chartColors[0]);
  if (vertical) {
    return (
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 30 + 30)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={axisTick} />
          <YAxis type="category" dataKey="name" width={130} tick={axisTick} />
          <ChartTooltip contentStyle={tooltipStyle} cursor={{ fill: "#94a3b81a" }} />
          <Bar dataKey="value" name="URLs" radius={[0, 4, 4, 0]}>{data.map((d, i) => <Cell key={d.name} fill={fill(d.name, i)} />)}</Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" vertical={false} />
        <XAxis dataKey="name" tick={axisTick} />
        <YAxis allowDecimals={false} tick={axisTick} />
        <ChartTooltip contentStyle={tooltipStyle} cursor={{ fill: "#94a3b81a" }} />
        <Bar dataKey="value" name="URLs" radius={[4, 4, 0, 0]}>{data.map((d, i) => <Cell key={d.name} fill={fill(d.name, i)} />)}</Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

const toSeries = (obj: Record<string, number> | undefined | null) => Object.entries(obj ?? {}).map(([name, value]) => ({ name, value: Number(value) || 0 }));

/* ------------------------------------------------------------------ tabs */
function PagesTab({ crawlId, base }: { crawlId: number; base: string }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [indexable, setIndexable] = useState("");
  const [kind, setKind] = useState("");
  const [sort, setSort] = useState("url");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [crawlId, q, status, indexable, kind, sort, order]);
  const query = useQuery({
    queryKey: ["crawl-pages", crawlId, q, status, indexable, kind, sort, order, page],
    queryFn: () => api.get(`/crawls/${crawlId}/pages`, { q, status, indexable, kind, sort, order, page, per_page: 50 }),
    placeholderData: keepPreviousData,
  });
  const onSort = (key: string) => {
    if (key === sort) setOrder(order === "asc" ? "desc" : "asc");
    else {
      setSort(key);
      setOrder(key === "url" ? "asc" : "desc");
    }
  };
  const columns: Column<any>[] = [
    { key: "url", header: "URL", sortKey: "url", render: (p) => (
      <div className="max-w-[26rem]">
        <div className="truncate font-medium text-slate-900 dark:text-slate-100" title={p.url}>{shortUrl(p.url, base)}</div>
        {p.title && <div className="truncate text-xs text-slate-500 dark:text-slate-400" title={p.title}>{p.title}</div>}
        {p.redirect_to && <div className="truncate text-xs text-slate-500 dark:text-slate-400" title={p.redirect_to}>→ {shortUrl(p.redirect_to, base)}</div>}
      </div>
    ) },
    { key: "status", header: "Status", sortKey: "status", render: (p) => (p.blocked_by_robots ? <Badge tone="gray" title="Durch robots.txt gesperrt">gesperrt</Badge> : <StatusCode code={p.status_code} error={p.error} />) },
    { key: "indexable", header: "Indexierbar", render: (p) => (!p.is_html ? <span className="text-slate-400">–</span>
      : p.indexable ? <Badge tone="green">ja</Badge>
      : <span className="inline-flex items-center gap-1.5"><Badge tone="amber">nein</Badge><span className="text-xs text-slate-500 dark:text-slate-400">{p.indexability_reason}</span></span>) },
    { key: "depth", header: "Tiefe", sortKey: "depth", align: "right", tooltip: "Klicks ab der Start-URL", render: (p) => p.depth ?? "–" },
    { key: "inlinks", header: "Eingehend", sortKey: "inlinks", align: "right", render: (p) => fmtInt(p.inlinks) },
    { key: "words", header: "Wörter", sortKey: "words", align: "right", render: (p) => (p.is_html ? fmtInt(p.word_count) : "–") },
    { key: "response", header: "Antwort", sortKey: "response", align: "right", render: (p) => fmtMs(p.response_ms) },
    { key: "size", header: "Größe", sortKey: "size", align: "right", render: (p) => fmtBytes(p.size_bytes) },
    { key: "issues", header: "Befunde", sortKey: "issues", align: "right", render: (p) => (p.issue_count ? <Badge tone="amber">{p.issue_count}</Badge> : <span className="text-slate-400">0</span>) },
    { key: "score", header: "Score", sortKey: "score", align: "right", render: (p) => <Score value={p.score} /> },
  ];
  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
        <SearchInput value={q} onChange={setQ} placeholder="URL oder Title suchen…" />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-auto" aria-label="Status-Filter">
          <option value="">Alle Status</option>
          {["2xx", "3xx", "4xx", "5xx", "error", "blocked"].map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <Select value={indexable} onChange={(e) => setIndexable(e.target.value)} className="w-auto" aria-label="Indexierbarkeits-Filter">
          <option value="">Alle</option>
          <option value="true">Indexierbar</option>
          <option value="false">Nicht indexierbar</option>
        </Select>
        <Select value={kind} onChange={(e) => setKind(e.target.value)} className="w-auto" aria-label="Typ-Filter">
          <option value="">Alle Typen</option>
          <option value="html">HTML-Seiten</option>
          <option value="other">Andere Ressourcen</option>
        </Select>
      </div>
      {query.isLoading ? <Spinner /> : query.error ? <div className="p-3"><ErrorBox error={query.error} onRetry={() => query.refetch()} /></div> : (
        <div className={query.isPlaceholderData ? "opacity-60 transition-opacity" : ""}>
          <DataTable columns={columns} rows={query.data.items} rowKey={(p) => p.id} dense sort={sort} order={order} onSort={onSort}
            onRowClick={(p) => navigate(`/pages/${crawlId}/${p.id}`)}
            empty={<EmptyState title="Keine passenden URLs" description="Suche oder Filter ändern, um mehr aus diesem Crawl zu sehen." />} />
          <Pagination page={page} perPage={query.data.per_page} total={query.data.total} onPage={setPage} />
        </div>
      )}
    </Card>
  );
}

function LinksTab({ crawlId, base }: { crawlId: number; base: string }) {
  const [kind, setKind] = useState("broken");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [crawlId, kind, q]);
  const query = useQuery({
    queryKey: ["crawl-links", crawlId, kind, q, page],
    queryFn: () => api.get(`/crawls/${crawlId}/links`, { kind, q, page, per_page: 50 }),
    placeholderData: keepPreviousData,
  });
  const columns: Column<any>[] = [
    { key: "source", header: "Quellseite", render: (l) => (
      <div className="max-w-[22rem] truncate">
        {l.source_page_id ? <Link to={`/pages/${crawlId}/${l.source_page_id}`} title={l.source_url} className="text-brand-700 hover:underline dark:text-brand-300">{shortUrl(l.source_url, base)}</Link>
          : <span title={l.source_url}>{shortUrl(l.source_url, base)}</span>}
      </div>
    ) },
    { key: "target", header: "Ziel", render: (l) => <div className="max-w-[22rem] truncate"><Url href={l.target_url} label={shortUrl(l.target_url, base)} className="!break-normal" /></div> },
    { key: "anchor", header: "Ankertext", render: (l) => <div className="max-w-[14rem] truncate" title={l.anchor ?? undefined}>{l.anchor || <span className="text-slate-400">(leer)</span>}</div> },
    { key: "type", header: "Typ", render: (l) => <span className="inline-flex gap-1"><Badge tone={l.internal ? "blue" : "purple"}>{l.internal ? "intern" : "extern"}</Badge>{l.nofollow && <Badge>nofollow</Badge>}</span> },
    { key: "status", header: "Status", tooltip: "Status des Linkziels. Ein Strich bedeutet: nicht geprüft.", render: (l) => (l.status === null && !l.error ? <span className="text-slate-400">–</span>
      : <span className="inline-flex items-center gap-1.5"><StatusCode code={l.status} error={l.error} />{l.status === null && l.error && <span className="max-w-[10rem] truncate text-xs text-slate-500" title={l.error}>{l.error}</span>}</span>) },
  ];
  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
        <Select value={kind} onChange={(e) => setKind(e.target.value)} className="w-auto" aria-label="Linktyp">
          <option value="broken">Defekte Links</option>
          <option value="internal">Interne Links</option>
          <option value="external">Externe Links</option>
          <option value="redirect">Links auf Weiterleitungen</option>
          <option value="nofollow">Nofollow-Links</option>
        </Select>
        <SearchInput value={q} onChange={setQ} placeholder="URL oder Ankertext suchen…" />
      </div>
      {query.isLoading ? <Spinner /> : query.error ? <div className="p-3"><ErrorBox error={query.error} onRetry={() => query.refetch()} /></div> : (
        <div className={query.isPlaceholderData ? "opacity-60 transition-opacity" : ""}>
          <DataTable columns={columns} rows={query.data.items} rowKey={(_, i) => i} dense
            empty={<EmptyState title={kind === "broken" && !q ? "Keine defekten Links" : "Keine passenden Links"} description={kind === "broken" && !q ? "Alle geprüften Linkziele haben in diesem Crawl erfolgreich geantwortet." : "Linktyp oder Suche ändern."} />} />
          <Pagination page={page} perPage={query.data.per_page} total={query.data.total} onPage={setPage} />
        </div>
      )}
    </Card>
  );
}

function RedirectsTab({ crawlId, base }: { crawlId: number; base: string }) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["crawl-redirects", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/redirects`) });
  useEffect(() => setPage(1), [crawlId, q]);
  const rows: any[] = useMemo(() => {
    const items: any[] = query.data?.items ?? [];
    const needle = q.trim().toLowerCase();
    return needle ? items.filter((r) => r.url.toLowerCase().includes(needle) || r.chain.some((c: string) => c.toLowerCase().includes(needle))) : items;
  }, [query.data, q]);
  if (query.isLoading) return <Card><Spinner /></Card>;
  if (query.error) return <ErrorBox error={query.error} onRetry={() => query.refetch()} />;
  const columns: Column<any>[] = [
    { key: "chain", header: "Weiterleitungskette", render: (r) => (
      <div className="flex max-w-[44rem] flex-wrap items-center gap-x-1.5 gap-y-1 text-xs">
        <Link to={`/pages/${crawlId}/${r.page_id}`} title={r.url} className="max-w-[18rem] truncate font-medium text-brand-700 hover:underline dark:text-brand-300">{shortUrl(r.url, base)}</Link>
        {r.chain.map((c: string, i: number) => (
          <span key={i} className="inline-flex min-w-0 items-center gap-1.5">
            <ArrowRight className="h-3 w-3 shrink-0 text-slate-400" />
            <span className="max-w-[18rem] truncate" title={c}>{shortUrl(c, base)}</span>
          </span>
        ))}
      </div>
    ) },
    { key: "status", header: "Status", render: (r) => <StatusCode code={r.status_code} /> },
    { key: "hops", header: "Schritte", align: "right", render: (r) => (r.hops > 1 ? <Badge tone="amber">{r.hops}</Badge> : r.hops) },
    { key: "loop", header: "Schleife", render: (r) => (r.loop ? <Badge tone="red">Schleife</Badge> : <span className="text-slate-400">–</span>) },
    { key: "final", header: "Endstatus", tooltip: "Status der letzten URL der Kette, sofern gecrawlt", render: (r) => (r.final_status === null || r.final_status === undefined ? <span className="text-slate-400" title="End-URL wurde nicht gecrawlt">–</span> : <StatusCode code={r.final_status} />) },
    { key: "inlinks", header: "Eingehend", align: "right", tooltip: "Interne Links, die noch auf die weiterleitende URL zeigen", render: (r) => fmtInt(r.inlinks) },
  ];
  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
        <SearchInput value={q} onChange={setQ} placeholder="Weiterleitungen suchen…" />
      </div>
      <DataTable columns={columns} rows={rows.slice((page - 1) * 50, page * 50)} rowKey={(r) => r.page_id} dense
        empty={<EmptyState title={q ? "Keine passenden Weiterleitungen" : "Keine Weiterleitungen"} description={q ? "Andere Suche versuchen." : "Keine gecrawlte URL hat weitergeleitet."} />} />
      {rows.length > 0 && <Pagination page={page} perPage={50} total={rows.length} onPage={setPage} />}
    </Card>
  );
}

const DUP_LABEL: Record<string, string> = {
  duplicate_content: "Identischer Inhalt", near_duplicate_content: "Nahezu gleicher Inhalt", title_duplicate: "Doppelte Titles",
  description_duplicate: "Doppelte Meta-Descriptions", h1_duplicate: "Doppelte H1",
};

function DuplicatesTab({ crawlId, base }: { crawlId: number; base: string }) {
  const query = useQuery({ queryKey: ["crawl-duplicates", crawlId], queryFn: () => api.get<Record<string, any[]>>(`/crawls/${crawlId}/duplicates`) });
  const [type, setType] = useState<string | null>(null);
  const [shown, setShown] = useState(20);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  if (query.isLoading) return <Card><Spinner /></Card>;
  if (query.error) return <ErrorBox error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data ?? {};
  const types = Object.keys(data);
  if (!types.some((t) => data[t].length)) return <Card><EmptyState title="Keine Duplikate" description="Keine indexierbaren Seiten teilen sich in diesem Crawl Title, Description, H1 oder Inhalt." /></Card>;
  const current = type && data[type] ? type : types.find((t) => data[t].length) ?? types[0];
  const groups = data[current] ?? [];
  return (
    <Card padded={false}>
      <div className="flex flex-wrap gap-1.5 border-b border-slate-100 p-3 dark:border-slate-800">
        {types.map((t) => (
          <Button key={t} size="sm" variant={t === current ? "primary" : "secondary"} onClick={() => { setType(t); setShown(20); }}>
            {DUP_LABEL[t] ?? titleCase(t)} · {data[t].length}
          </Button>
        ))}
      </div>
      {!groups.length ? <EmptyState title="Nichts in dieser Gruppe" description="Für diese Duplikatart wurden keine Seiten markiert." /> : (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {groups.slice(0, shown).map((g, i) => {
            const key = `${current}-${i}`;
            const expanded = !!open[key];
            const urls: string[] = expanded ? g.urls : g.urls.slice(0, 4);
            return (
              <li key={key} className="p-3">
                <div className="mb-1.5 flex flex-wrap items-center gap-2">
                  <Badge tone="amber">{g.count} pages</Badge>
                  <span className="min-w-0 break-words text-sm font-medium text-slate-800 dark:text-slate-200">
                    {g.value ? `“${g.value}”` : current === "near_duplicate_content" ? "Sehr ähnlicher Text" : "Identischer Text"}
                  </span>
                </div>
                <ul className="space-y-0.5 text-sm">
                  {urls.map((u) => <li key={u} className="truncate"><Url href={u} label={shortUrl(u, base)} /></li>)}
                </ul>
                {g.urls.length > 4 && (
                  <button className="mt-1 text-xs font-medium text-brand-700 hover:underline dark:text-brand-300" onClick={() => setOpen({ ...open, [key]: !expanded })}>
                    {expanded ? "Weniger anzeigen" : `Alle ${g.urls.length} anzeigen`}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {groups.length > shown && (
        <div className="border-t border-slate-100 p-3 text-center dark:border-slate-800">
          <Button size="sm" onClick={() => setShown(shown + 20)}>Show more ({groups.length - shown} remaining)</Button>
        </div>
      )}
    </Card>
  );
}

function StructureTab({ stats }: { stats: Record<string, any> }) {
  if (!stats || !Object.keys(stats).length) return <Card><EmptyState title="Keine Statistik" description="Die Statistik wird nach Abschluss eines Crawls berechnet." /></Card>;
  const depth = toSeries(stats.depth_distribution).sort((a, b) => (a.name === "unreachable" ? 1 : b.name === "unreachable" ? -1 : Number(a.name) - Number(b.name)));
  const byValue = (o: any) => toSeries(o).sort((a, b) => b.value - a.value);
  const links = stats.links ?? {};
  const redirects = stats.redirects ?? {};
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="URLs" value={fmtInt(stats.total_urls)} />
        <Stat label="HTML-Seiten" value={fmtInt(stats.html_pages)} tooltip="HTML-Seiten mit Status 200" />
        <Stat label="Indexierbar" value={fmtInt(stats.indexable_pages)} tone="good" />
        <Stat label="Nicht indexierbar" value={fmtInt(stats.non_indexable_pages)} tone={stats.non_indexable_pages ? "warn" : undefined} />
        <Stat label="Ø Wörter" value={fmtInt(stats.avg_word_count)} tooltip="Durchschnittliche Wortzahl indexierbarer Seiten" />
        <Stat label="Ø Antwortzeit" value={fmtMs(stats.avg_response_ms)} />
        <Stat label="Interne Links" value={fmtInt(links.internal)} />
        <Stat label="Externe Links" value={fmtInt(links.external)} hint={`${fmtInt(links.external_checked)} geprüft`} />
        <Stat label="Defekte Links" value={fmtInt((links.broken_internal ?? 0) + (links.broken_external ?? 0))} tone={(links.broken_internal ?? 0) + (links.broken_external ?? 0) ? "bad" : "good"}
          hint={`${fmtInt(links.broken_internal)} intern · ${fmtInt(links.broken_external)} extern`} />
        <Stat label="Weiterleitungen" value={fmtInt(redirects.total)} hint={`${fmtInt(redirects.chains)} Ketten · ${fmtInt(redirects.loops)} Schleifen`} />
        <Stat label="Mit Schema" value={fmtInt(stats.schema?.pages_with_schema)} tooltip="Seiten mit JSON-LD oder Microdata" />
        <Stat label="Mit hreflang" value={fmtInt(stats.hreflang_pages)} />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Klicktiefe" description="HTML-Seiten nach Klicks ab der Start-URL">
          <DistChart data={depth} color={(name) => (name === "unreachable" ? "#dc2626" : Number(name) > 4 ? "#ca8a04" : chartColors[0])} />
        </Card>
        <Card title="Statusklassen" description="Alle gecrawlten URLs nach HTTP-Statusklasse">
          <DistChart data={toSeries(stats.status_classes).sort((a, b) => a.name.localeCompare(b.name))} color={(name) => STATUS_CLASS_COLOR[name] ?? "#64748b"} />
        </Card>
        <Card title="Inhaltstypen" description="Was der Crawler erhalten hat">
          <DistChart vertical data={byValue(stats.content_types)} color={(_, i) => chartColors[i % chartColors.length]} />
        </Card>
        <Card title="Warum Seiten nicht indexierbar sind" description="Von der Indexierung ausgeschlossene HTML-Seiten nach Grund">
          {Object.keys(stats.non_indexable_reasons ?? {}).length
            ? <DistChart vertical data={byValue(stats.non_indexable_reasons)} color={() => "#ca8a04"} />
            : <EmptyState title="Alles indexierbar" description="Keine HTML-Seite ist von der Indexierung ausgeschlossen." />}
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ page */
type TabId = "pages" | "links" | "redirects" | "duplicates" | "structure" | "relaunch";

export default function Crawler() {
  const { site, loading, refresh } = useSite();
  const qc = useQueryClient();
  const [cfg, setCfg] = useState<CrawlCfg>({});
  const [showOptions, setShowOptions] = useState(false);
  const [inspectId, setInspectId] = useState<number | null>(null);
  const [tab, setTab] = useState<TabId>("pages");
  const [toDelete, setToDelete] = useState<CrawlSummary | null>(null);
  const siteId = site?.id ?? null;
  const activeId = site?.active_crawl?.id ?? null;

  useEffect(() => {
    setCfg({ ...(site?.crawl_config ?? {}) });
    setInspectId(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  const invalidateAll = () => {
    refresh();
    for (const key of ["crawls", "crawl", "dashboard", "overview"]) void qc.invalidateQueries({ queryKey: [key] });
  };

  const start = useMutation({
    mutationFn: () => api.post(`/sites/${siteId}/crawls`, cleanConfig(cfg)),
    onSuccess: invalidateAll,
  });
  const cancel = useMutation({ mutationFn: (id: number) => api.post(`/crawls/${id}/cancel`), onSuccess: invalidateAll });
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/crawls/${id}`),
    onSuccess: () => {
      setToDelete(null);
      invalidateAll();
    },
  });

  // live progress of the running crawl
  const live = useQuery({
    queryKey: ["crawl", activeId, "live"],
    queryFn: () => api.get(`/crawls/${activeId}`),
    enabled: activeId !== null,
    refetchInterval: (q) => (ACTIVE.includes(q.state.data?.status ?? "queued") ? 1500 : false),
  });
  const liveStatus: string | undefined = live.data?.status;
  useEffect(() => {
    if (liveStatus && !ACTIVE.includes(liveStatus)) invalidateAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveStatus, activeId]);
  const prevActive = useRef<number | null>(null);
  useEffect(() => {
    if (prevActive.current !== null && activeId === null) invalidateAll();
    prevActive.current = activeId;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  const history = useQuery<CrawlSummary[]>({ queryKey: ["crawls", siteId], queryFn: () => api.get(`/sites/${siteId}/crawls`), enabled: siteId !== null });
  const crawls = history.data ?? [];
  const inspected = crawls.find((c) => c.id === inspectId && !ACTIVE.includes(c.status)) ?? crawls.find((c) => c.status === "completed") ?? null;
  const inspectedId = inspected?.id ?? null;
  const detail = useQuery({ queryKey: ["crawl", inspectedId], queryFn: () => api.get(`/crawls/${inspectedId}`), enabled: inspectedId !== null });

  if (loading) return <Spinner />;
  if (!site) {
    return (
      <>
        <PageHeader title="Crawler" description="Website crawlen und dabei jede URL, jeden Link, jede Weiterleitung und alle Onpage-Elemente erfassen." />
        <Card><EmptyState title="Zuerst eine Website anlegen" description="Der Crawler arbeitet mit der ausgewählten Website. Lege eine an, um zu starten."
          action={<Link to="/sites" className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">Zu den Websites</Link>} /></Card>
      </>
    );
  }

  const job = live.data?.job;
  const stats: Record<string, any> = detail.data?.stats ?? {};
  const exportPath = `/crawls/${inspectedId}/export`;

  const historyColumns: Column<CrawlSummary>[] = [
    { key: "id", header: "Crawl", render: (c) => <span className="font-medium text-slate-900 dark:text-slate-100">#{c.id}</span> },
    { key: "status", header: "Status", render: (c) => (
      <span className="inline-flex items-center gap-1.5">
        <CrawlStatusBadge status={c.status} />
        {c.error && <span className="max-w-[16rem] truncate text-xs text-red-600 dark:text-red-400" title={c.error}>{c.error}</span>}
      </span>
    ) },
    { key: "score", header: "Score", align: "right", render: (c) => <Score value={c.score} /> },
    { key: "pages", header: "URLs", align: "right", render: (c) => fmtInt(c.pages_crawled) },
    { key: "issues", header: "Kritisch / hoch", align: "right", render: (c) => (c.issues_by_severity ? `${fmtInt(c.issues_by_severity.critical)} / ${fmtInt(c.issues_by_severity.high)}` : "–") },
    { key: "date", header: "Datum", render: (c) => <span title={timeAgo(c.finished_at ?? c.created_at)}>{fmtDateTime(c.finished_at ?? c.started_at ?? c.created_at)}</span> },
    { key: "actions", header: "", align: "right", render: (c) => (
      <span className="inline-flex items-center gap-1">
        {ACTIVE.includes(c.status) ? <Button size="sm" variant="ghost" loading={cancel.isPending && cancel.variables === c.id} onClick={() => cancel.mutate(c.id)}>Abbrechen</Button> : (
          <>
            {c.id === inspectedId ? <Badge tone="blue">angezeigt</Badge>
              : <Button size="sm" disabled={c.pages_crawled === 0} title={c.pages_crawled === 0 ? "Dieser Crawl hat keine URLs gespeichert" : undefined} onClick={() => setInspectId(c.id)}>Anzeigen</Button>}
            <Button size="sm" variant="ghost" aria-label={`Crawl ${c.id} löschen`} onClick={() => { remove.reset(); setToDelete(c); }}><Trash2 className="h-4 w-4" /></Button>
          </>
        )}
      </span>
    ) },
  ];

  return (
    <>
      <PageHeader title="Crawler" description={<><span className="font-medium text-slate-700 dark:text-slate-200">{site.url}</span> crawlen und jede URL, jeden Link, jede Weiterleitung und jedes Duplikat prüfen.</>}
        actions={inspectedId !== null && (
          <ExportMenu formats={[
            { label: "Seiten (CSV)", path: exportPath, query: { dataset: "pages", format: "csv" } },
            { label: "Befunde (CSV)", path: exportPath, query: { dataset: "issues", format: "csv" } },
            { label: "Links (CSV)", path: exportPath, query: { dataset: "links", format: "csv" } },
            { label: "Komplette Arbeitsmappe (Excel)", path: exportPath, query: { dataset: "all", format: "xlsx" } },
            { label: "Seiten + Statistik (JSON)", path: exportPath, query: { dataset: "pages", format: "json" } },
          ]} />
        )} />

      <div className="space-y-4">
        {activeId !== null ? (
          <Card title={`Crawl #${activeId} läuft`} description="Du kannst die Seite verlassen. Der Crawl läuft auf dem Server weiter."
            actions={<Button size="sm" variant="danger" icon={<Square className="h-3.5 w-3.5" />} loading={cancel.isPending} onClick={() => cancel.mutate(activeId)}>Crawl abbrechen</Button>}>
            <ProgressBar value={job?.progress ?? 0} label={job?.message ?? (live.data?.status === "queued" || !live.data ? "Wartet auf Start…" : "Crawlt…")} />
            {live.error && <div className="mt-3"><ErrorBox error={live.error} onRetry={() => live.refetch()} /></div>}
            {cancel.error && <div className="mt-3"><ErrorBox error={cancel.error} /></div>}
          </Card>
        ) : (
          <Card title="Crawl starten" description="Nutzt die gespeicherten Standardwerte der Website, sofern du unten nichts änderst."
            actions={<>
              <Button size="sm" variant="ghost" icon={showOptions ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />} onClick={() => setShowOptions(!showOptions)}>Optionen</Button>
              <Button size="sm" variant="primary" icon={<Play className="h-3.5 w-3.5" />} loading={start.isPending} onClick={() => start.mutate()}>Crawl starten</Button>
            </>}>
            {showOptions ? <CrawlConfigForm value={cfg} onChange={setCfg} /> : (
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Bis zu <b className="font-semibold">{fmtInt(Number(cfg.max_urls) || 0)}</b> URLs</span>
                <span>Tiefe ≤ <b className="font-semibold">{cfg.max_depth ?? "–"}</b></span>
                <span><b className="font-semibold">{cfg.concurrency ?? "–"}</b> parallele Anfragen</span>
                <span>{cfg.respect_robots ? "beachtet robots.txt" : "ignoriert robots.txt"}</span>
                <span>{cfg.render_js ? "JavaScript-Rendering an" : "ohne JavaScript-Rendering"}</span>
              </div>
            )}
            {start.error && <div className="mt-3"><ErrorBox error={start.error} /></div>}
          </Card>
        )}

        <Card title="Crawl-Verlauf" description="Der als „angezeigt“ markierte Crawl füllt die Reiter unten." padded={false}>
          {history.isLoading ? <Spinner /> : history.error ? <div className="p-3"><ErrorBox error={history.error} onRetry={() => history.refetch()} /></div> : (
            <DataTable columns={historyColumns} rows={crawls} rowKey={(c) => c.id} dense
              empty={<EmptyState title="Noch keine Crawls" description="Starte den ersten Crawl, um diese Website zu prüfen." />} />
          )}
        </Card>

        {inspectedId !== null && (
          <section>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Crawl #{inspectedId}</h2>
              {inspected && <CrawlStatusBadge status={inspected.status} />}
              <span className="text-xs text-slate-500 dark:text-slate-400">{fmtInt(inspected?.pages_crawled)} URLs · {fmtDateTime(inspected?.finished_at ?? inspected?.created_at)}</span>
            </div>
            {stats.limit_reached && (
              <div className="mb-3"><Notice tone="warn">Dieser Crawl hat am URL-Limit gestoppt, Teile der Website fehlen. Für vollständige Abdeckung „Max. URLs“ in den Optionen erhöhen.</Notice></div>
            )}
            {inspected && inspected.status !== "completed" && (
              <div className="mb-3"><Notice tone="warn">This crawl did not complete ({inspected.status}). The data below is partial and site-wide analysis may be missing.</Notice></div>
            )}
            <Tabs<TabId> value={tab} onChange={setTab} tabs={[
              { id: "pages", label: "Seiten", count: stats.total_urls ?? null },
              { id: "links", label: "Links" },
              { id: "redirects", label: "Weiterleitungen", count: stats.redirects?.total ?? null },
              { id: "duplicates", label: "Duplikate" },
              { id: "structure", label: "Struktur" },
              { id: "relaunch", label: "Relaunch" },
            ]} />
            {tab === "pages" && <PagesTab crawlId={inspectedId} base={site.url} />}
            {tab === "links" && <LinksTab crawlId={inspectedId} base={site.url} />}
            {tab === "redirects" && <RedirectsTab crawlId={inspectedId} base={site.url} />}
            {tab === "duplicates" && <DuplicatesTab crawlId={inspectedId} base={site.url} />}
            {tab === "relaunch" && siteId !== null && <RelaunchPanel siteId={siteId} crawls={crawls} newestId={inspectedId} />}
            {tab === "structure" && (detail.isLoading ? <Card><Spinner /></Card> : detail.error ? <ErrorBox error={detail.error} onRetry={() => detail.refetch()} /> : <StructureTab stats={stats} />)}
          </section>
        )}
      </div>

      <Modal open={toDelete !== null} onClose={() => setToDelete(null)} title={`Crawl #${toDelete?.id ?? ""} löschen?`}
        footer={<>
          <Button onClick={() => setToDelete(null)}>Crawl behalten</Button>
          <Button variant="danger" loading={remove.isPending} onClick={() => toDelete && remove.mutate(toDelete.id)}>Crawl löschen</Button>
        </>}>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Entfernt die {fmtInt(toDelete?.pages_crawled)} URLs, Links und Befunde dieses Crawls dauerhaft. Der Score-Verlauf dieses Crawls geht verloren. Das lässt sich nicht rückgängig machen.
        </p>
        {remove.error && <div className="mt-3"><ErrorBox error={remove.error} /></div>}
      </Modal>
    </>
  );
}
