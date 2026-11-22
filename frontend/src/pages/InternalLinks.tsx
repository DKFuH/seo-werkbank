import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Maximize2, Minus, Plus } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, chartColors, type Column, DataTable, EmptyState, ErrorBox, NeedsCrawl, Notice, PageHeader, Pagination,
  Spinner, Stat, StatusCode, Tabs, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, fmtNum, shortUrl } from "../lib/format";

type TabId = "overview" | "top" | "weak" | "orphans" | "anchors" | "opportunities" | "graph";

const INLINK_ORDER = ["0", "1", "2-5", "6-20", "21+"];
const tooltipStyle = { background: "#0f172a", border: "none", borderRadius: 8, color: "#f8fafc", fontSize: 12 } as const;
const axisTick = { fontSize: 12, fill: "#94a3b8" } as const;

function DistributionChart({ data, color, xLabel }: { data: { name: string; pages: number }[]; color: string; xLabel: string }) {
  if (!data.length || data.every((d) => !d.pages)) return <EmptyState title="Keine Daten" description="Der Crawl hat diese Verteilung nicht erfasst." />;
  return (
    <div className="h-64" role="img" aria-label={`Verteilung: ${xLabel}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" vertical={false} />
          <XAxis dataKey="name" tick={axisTick} tickLine={false} axisLine={{ stroke: "#94a3b855" }}
            label={{ value: xLabel, position: "insideBottom", offset: -8, fontSize: 11, fill: "#94a3b8" }} />
          <YAxis allowDecimals={false} tick={axisTick} tickLine={false} axisLine={false} width={44} />
          <ChartTooltip cursor={{ fill: "#94a3b822" }} contentStyle={tooltipStyle} labelStyle={{ color: "#f8fafc" }} itemStyle={{ color: "#f8fafc" }} />
          <Bar dataKey="pages" name="Seiten" fill={color} radius={[4, 4, 0, 0]} maxBarSize={56} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function PagesTable({ rows, crawlId, base, empty }: { rows: any[]; crawlId: number; base?: string; empty: { title: string; description: string } }) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const perPage = 25;
  const columns: Column<any>[] = [
    {
      key: "url", header: "URL", render: (r) => (
        <div className="max-w-xl">
          <Url href={r.url} label={shortUrl(r.url, base)} />
          {r.title && <div className="truncate text-xs text-slate-500 dark:text-slate-400">{r.title}</div>}
        </div>
      ),
    },
    { key: "status", header: "Status", render: (r) => <StatusCode code={r.status_code} error={r.error} /> },
    { key: "pagerank", header: "PageRank", align: "right", tooltip: "Interner PageRank; Durchschnittsseite = 1,0", render: (r) => fmtNum(r.pagerank, 2) },
    { key: "inlinks", header: "Eingehend", align: "right", render: (r) => fmtInt(r.inlinks) },
    { key: "depth", header: "Tiefe", align: "right", tooltip: "Klicks ab der Start-URL", render: (r) => (r.depth === null || r.depth === undefined ? "–" : r.depth) },
    { key: "indexable", header: "Indexierbar", render: (r) => (r.indexable ? <Badge tone="green">ja</Badge> : <Badge tone="amber" title={r.indexability_reason ?? undefined}>nein</Badge>) },
  ];
  return (
    <>
      <DataTable columns={columns} rows={rows.slice((page - 1) * perPage, page * perPage)} rowKey={(r) => r.id}
        onRowClick={(r) => navigate(`/pages/${crawlId}/${r.id}`)} empty={<EmptyState title={empty.title} description={empty.description} />} />
      {rows.length > 0 && <Pagination page={page} perPage={perPage} total={rows.length} onPage={setPage} />}
    </>
  );
}

/* ------------------------------------------------------------------ link graph */
interface GraphNode { id: number; url: string; path: string; title: string | null; depth: number | null; pagerank: number | null; inlinks: number | null; status: number | null; indexable: boolean | null }
interface GraphEdge { source: number; target: number }
interface Placed extends GraphNode { x: number; y: number; r: number; color: string }

const NODE_KINDS = [
  { id: "indexable", label: "200, indexierbar", color: "#16a34a" },
  { id: "nonindexable", label: "200, nicht indexierbar", color: "#ca8a04" },
  { id: "redirect", label: "Weiterleitung (3xx)", color: "#3866f5" },
  { id: "error", label: "Fehler (4xx/5xx)", color: "#dc2626" },
  { id: "unknown", label: "Keine Antwort", color: "#64748b" },
] as const;

function nodeColor(n: GraphNode): string {
  if (n.status === null || n.status === undefined) return NODE_KINDS[4].color;
  if (n.status >= 400) return NODE_KINDS[3].color;
  if (n.status >= 300) return NODE_KINDS[2].color;
  return n.indexable ? NODE_KINDS[0].color : NODE_KINDS[1].color;
}

const EXTENT = 420; // half-size of the drawing area in SVG units
const RING_MAX = 370;

/** Radial layout: one ring per crawl depth; nodes on a ring are ordered by the mean angle of their already placed neighbours. */
function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]) {
  const levels = Array.from(new Set(nodes.map((n) => (n.depth === null || n.depth === undefined ? Infinity : n.depth)))).sort((a, b) => a - b);
  const neighbours = new Map<number, number[]>();
  for (const e of edges) {
    (neighbours.get(e.source) ?? neighbours.set(e.source, []).get(e.source)!).push(e.target);
    (neighbours.get(e.target) ?? neighbours.set(e.target, []).get(e.target)!).push(e.source);
  }
  const maxPr = Math.max(1e-9, ...nodes.map((n) => n.pagerank ?? 0));
  const angleOf = new Map<number, number>();
  const placed: Placed[] = [];
  const centreIsSingle = levels[0] === 0 && nodes.filter((n) => n.depth === 0).length === 1;
  const ringCount = levels.length - (centreIsSingle ? 1 : 0);
  const gap = ringCount > 0 ? RING_MAX / ringCount : 0;
  const rings: { radius: number; label: string }[] = [];
  levels.forEach((level, li) => {
    const group = nodes.filter((n) => (n.depth === null || n.depth === undefined ? Infinity : n.depth) === level);
    const ringIndex = centreIsSingle ? li : li + 1;
    const radius = centreIsSingle && li === 0 ? 0 : ringIndex * gap;
    if (radius > 0) rings.push({ radius, label: level === Infinity ? "nicht erreichbar" : `Tiefe ${level}` });
    const keyed = group.map((n, i) => {
      let sx = 0, sy = 0, c = 0;
      for (const other of neighbours.get(n.id) ?? []) {
        const a = angleOf.get(other);
        if (a !== undefined) { sx += Math.cos(a); sy += Math.sin(a); c++; }
      }
      const mean = c ? Math.atan2(sy, sx) : NaN;
      return { n, key: Number.isNaN(mean) ? Math.PI * 2 + i : (mean + Math.PI * 2.5) % (Math.PI * 2) };
    }).sort((a, b) => a.key - b.key);
    keyed.forEach(({ n }, i) => {
      const angle = -Math.PI / 2 + (i / keyed.length) * Math.PI * 2 + (li % 2 ? Math.PI / Math.max(keyed.length, 1) : 0);
      angleOf.set(n.id, angle);
      placed.push({ ...n, x: radius * Math.cos(angle), y: radius * Math.sin(angle), r: 3 + 9 * Math.sqrt(Math.max(0, n.pagerank ?? 0) / maxPr), color: nodeColor(n) });
    });
  });
  return { placed, rings };
}

const EdgeLayer = memo(function EdgeLayer({ edges, pos }: { edges: GraphEdge[]; pos: Map<number, Placed> }) {
  return (
    <g className="stroke-slate-400 dark:stroke-slate-500" strokeWidth={0.5}>
      {edges.map((e, i) => {
        const a = pos.get(e.source), b = pos.get(e.target);
        return a && b ? <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} vectorEffect="non-scaling-stroke" /> : null;
      })}
    </g>
  );
});

interface View { x: number; y: number; w: number; h: number }
const FULL_VIEW: View = { x: -EXTENT, y: -EXTENT, w: EXTENT * 2, h: EXTENT * 2 };

function LinkGraph({ crawlId }: { crawlId: number }) {
  const navigate = useNavigate();
  const q = useQuery({ queryKey: ["graph", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/graph`, { limit: 150 }) });
  const nodes: GraphNode[] = q.data?.nodes ?? [];
  const edges: GraphEdge[] = q.data?.edges ?? [];
  const { placed, rings } = useMemo(() => layoutGraph(nodes, edges), [nodes, edges]);
  const pos = useMemo(() => new Map(placed.map((p) => [p.id, p])), [placed]);

  const [view, setView] = useState<View>(FULL_VIEW);
  const [hover, setHover] = useState<number | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ px: number; py: number; view: View; moved: boolean } | null>(null);

  const zoomAt = useCallback((factor: number, cx = 0.5, cy = 0.5) => {
    setView((v) => {
      const w = Math.min(EXTENT * 4, Math.max(60, v.w * factor));
      const h = w; // square viewBox
      return { x: v.x + (v.w - w) * cx, y: v.y + (v.h - h) * cy, w, h };
    });
  }, []);

  // React registers wheel listeners as passive, so preventDefault needs a native listener.
  const hasGraph = placed.length > 0;
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = svg.getBoundingClientRect();
      zoomAt(e.deltaY > 0 ? 1.15 : 1 / 1.15, (e.clientX - rect.left) / rect.width, (e.clientY - rect.top) / rect.height);
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [zoomAt, hasGraph]);

  if (q.isLoading) return <Spinner label="Linkgraph wird aufgebaut…" />;
  if (q.error) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  if (!placed.length) return <EmptyState title="Keine Seiten zum Zeichnen" description="Der Crawl enthält keine HTML-Seiten, daher gibt es keinen Linkgraphen." />;

  const hovered = hover !== null ? pos.get(hover) : undefined;
  const hoverEdges = hover !== null ? edges.filter((e) => e.source === hover || e.target === hover) : [];
  const linked = new Set<number>(hoverEdges.flatMap((e) => [e.source, e.target]));
  const outCount = hoverEdges.filter((e) => e.source === hover).length;

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    drag.current = { px: e.clientX, py: e.clientY, view, moved: false };
  };
  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const wrap = wrapRef.current?.getBoundingClientRect();
    if (wrap) setTip({ x: e.clientX - wrap.left, y: e.clientY - wrap.top });
    const d = drag.current;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!d || !rect) return;
    const dx = e.clientX - d.px, dy = e.clientY - d.py;
    if (!d.moved && Math.hypot(dx, dy) < 4) return;
    if (!d.moved) {
      d.moved = true;
      svgRef.current?.setPointerCapture(e.pointerId);
    }
    const scale = d.view.w / Math.min(rect.width, rect.height);
    setView({ ...d.view, x: d.view.x - dx * scale, y: d.view.y - dy * scale });
  };
  const endDrag = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (d?.moved && svgRef.current?.hasPointerCapture(e.pointerId)) svgRef.current.releasePointerCapture(e.pointerId);
    // keep the "moved" flag until the click event that follows pointerup has been handled
    setTimeout(() => { drag.current = null; }, 0);
  };
  const open = (n: Placed) => {
    if (drag.current?.moved) return;
    navigate(`/pages/${crawlId}/${n.id}`);
  };

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Showing <span className="font-semibold tabular-nums">{fmtInt(q.data.shown)}</span> of{" "}
          <span className="font-semibold tabular-nums">{fmtInt(q.data.total_pages)}</span> pages (highest internal PageRank first) and{" "}
          <span className="tabular-nums">{fmtInt(edges.length)}</span> links between them.
        </p>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" aria-label="Vergrößern" onClick={() => zoomAt(1 / 1.3)}><Plus className="h-4 w-4" /></Button>
          <Button size="sm" variant="ghost" aria-label="Verkleinern" onClick={() => zoomAt(1.3)}><Minus className="h-4 w-4" /></Button>
          <Button size="sm" variant="ghost" icon={<Maximize2 className="h-3.5 w-3.5" />} onClick={() => setView(FULL_VIEW)}>Zurücksetzen</Button>
        </div>
      </div>
      <div ref={wrapRef} className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
        <svg ref={svgRef} viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`} preserveAspectRatio="xMidYMid meet"
          className="block h-[560px] w-full cursor-grab touch-none select-none active:cursor-grabbing sm:h-[640px]"
          role="img" aria-label={`Interner Linkgraph aus ${placed.length} Seiten, nach Crawltiefe angeordnet`}
          onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={endDrag} onPointerCancel={endDrag}
          onPointerLeave={() => { setHover(null); setTip(null); }}>
          {rings.map((ring) => (
            <g key={ring.label}>
              <circle cx={0} cy={0} r={ring.radius} fill="none" strokeDasharray="3 5" strokeWidth={1} vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-slate-700" />
              <text x={0} y={-ring.radius - 4} textAnchor="middle" fontSize={10} className="fill-slate-400 dark:fill-slate-500">{ring.label}</text>
            </g>
          ))}
          <g opacity={hover === null ? 0.22 : 0.05}><EdgeLayer edges={edges} pos={pos} /></g>
          {hovered && (
            <g strokeWidth={1.2} pointerEvents="none">
              {hoverEdges.map((e, i) => {
                const a = pos.get(e.source), b = pos.get(e.target);
                return a && b ? <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={e.source === hover ? "#3866f5" : "#9333ea"} opacity={0.85} vectorEffect="non-scaling-stroke" /> : null;
              })}
            </g>
          )}
          {placed.map((n) => (
            <circle key={n.id} cx={n.x} cy={n.y} r={n.r} fill={n.color}
              opacity={hover === null || hover === n.id || linked.has(n.id) ? 1 : 0.2}
              strokeWidth={hover === n.id ? 2.5 : 1} vectorEffect="non-scaling-stroke"
              className={hover === n.id ? "cursor-pointer stroke-slate-900 dark:stroke-white" : "cursor-pointer stroke-white dark:stroke-slate-950"}
              onPointerEnter={() => setHover(n.id)} onPointerLeave={() => setHover((h) => (h === n.id ? null : h))} onClick={() => open(n)} />
          ))}
        </svg>
        {hovered && tip && (
          <div className="pointer-events-none absolute z-10 w-64 rounded-lg bg-slate-900 p-2.5 text-xs text-white shadow-lg dark:bg-slate-700"
            style={{ left: Math.max(4, Math.min(tip.x + 14, (wrapRef.current?.clientWidth ?? 600) - 264)), top: tip.y + 14 }}>
            <div className="break-all font-medium">{hovered.path}</div>
            {hovered.title && <div className="mt-0.5 line-clamp-2 text-slate-300">{hovered.title}</div>}
            <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 tabular-nums text-slate-200">
              <span>Inlinks: {fmtInt(hovered.inlinks)}</span>
              <span>PageRank: {fmtNum(hovered.pagerank, 2)}</span>
              <span>Depth: {hovered.depth ?? "unreachable"}</span>
              <span>Status: {hovered.status ?? "–"}</span>
            </div>
            <div className="mt-1.5 text-slate-400">
              In this view: <span className="text-violet-300">{hoverEdges.length - outCount} in</span>, <span className="text-brand-200">{outCount} out</span>. Click to open.
            </div>
          </div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600 dark:text-slate-300">
        {NODE_KINDS.map((k) => (
          <span key={k.id} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: k.color }} />{k.label}</span>
        ))}
        <span className="text-slate-500 dark:text-slate-400">Kreisgröße = interner PageRank. Ringe = Klicks ab der Start-URL. Scrollen zum Zoomen, ziehen zum Verschieben.</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ opportunities */
function Opportunities({ crawlId, base }: { crawlId: number; base?: string }) {
  const q = useQuery({ queryKey: ["link-opportunities", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/link-opportunities`, { limit: 200 }) });
  const [page, setPage] = useState(1);
  const perPage = 25;
  if (q.isLoading) return <Spinner label="Suche nach Linkchancen…" />;
  if (q.error) return <div className="p-4"><ErrorBox error={q.error} onRetry={() => q.refetch()} /></div>;
  const items: any[] = q.data?.items ?? [];
  const columns: Column<any>[] = [
    {
      key: "source", header: "Link setzen auf", render: (r) => (
        <div className="max-w-sm">
          <Url href={r.source_url} label={shortUrl(r.source_url, base)} />
          {r.source_title && <div className="truncate text-xs text-slate-500 dark:text-slate-400">{r.source_title}</div>}
        </div>
      ),
    },
    { key: "arrow", header: "", render: () => <ArrowRight className="mt-0.5 h-4 w-4 text-slate-400" aria-label="verlinkt auf" /> },
    {
      key: "target", header: "Ziel", render: (r) => (
        <div className="max-w-sm">
          <Url href={r.target_url} label={shortUrl(r.target_url, base)} />
          {r.target_title && <div className="truncate text-xs text-slate-500 dark:text-slate-400">{r.target_title}</div>}
        </div>
      ),
    },
    { key: "terms", header: "Treffer", tooltip: "Wörter aus H1/Title des Ziels, die alle im Text der Quellseite vorkommen", render: (r) => <div className="flex max-w-xs flex-wrap gap-1">{(r.matched_terms ?? []).map((t: string) => <Badge key={t} tone="blue">{t}</Badge>)}</div> },
    { key: "inlinks", header: "Eingehend (Ziel)", align: "right", tooltip: "Ziele mit den wenigsten internen Links profitieren am meisten", render: (r) => fmtInt(r.target_inlinks) },
  ];
  return (
    <>
      {q.data?.method && <div className="border-b border-slate-100 p-4 dark:border-slate-800"><Notice>{q.data.method}</Notice></div>}
      <DataTable columns={columns} rows={items.slice((page - 1) * perPage, page * perPage)} rowKey={(r, i) => `${r.source_url}|${r.target_url}|${i}`}
        empty={<EmptyState title="Keine Linkchancen gefunden" description="Keine indexierbare Seite erwähnt das Thema einer anderen, ohne sie schon zu verlinken." />} />
      {items.length > 0 && (
        <div className="flex flex-wrap items-center justify-between">
          <Pagination page={page} perPage={perPage} total={items.length} onPage={setPage} />
          {q.data.total > items.length && <span className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">Top {fmtInt(items.length)} von {fmtInt(q.data.total)} Vorschlägen</span>}
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ page */
export default function InternalLinks() {
  const { site, crawlId } = useSite();
  const [tab, setTab] = useState<TabId>("overview");
  const q = useQuery({ queryKey: ["internal-links", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/internal-links`), enabled: !!crawlId });

  const header = <PageHeader title="Interne Verlinkung" description="Wie Linkkraft durch die Website fließt: welche Seiten gut verlinkt, welche vergraben oder verwaist sind und wo ein Link fehlt." />;
  if (!crawlId) return <>{header}<NeedsCrawl hasSite={!!site} running={!!site?.active_crawl} /></>;
  if (q.isLoading) return <>{header}<Spinner /></>;
  if (q.error) return <>{header}<ErrorBox error={q.error} onRetry={() => q.refetch()} /></>;

  const d = q.data ?? {};
  const inDist: Record<string, number> = d.inlink_distribution ?? {};
  const depthDist: Record<string, number> = d.depth_distribution ?? {};
  const inlinkData = INLINK_ORDER.map((name) => ({ name, pages: inDist[name] ?? 0 }));
  const depthKeys = Object.keys(depthDist).sort((a, b) => (a === "unreachable" ? 1 : b === "unreachable" ? -1 : Number(a) - Number(b)));
  const depthData = depthKeys.map((name) => ({ name, pages: depthDist[name] }));
  const totalPages = Object.values(inDist).reduce((a, b) => a + b, 0);
  const numericDepths = depthKeys.filter((k) => k !== "unreachable").map(Number);
  const maxDepth = numericDepths.length ? Math.max(...numericDepths) : null;
  const deepPages = depthKeys.filter((k) => k !== "unreachable" && Number(k) > 3).reduce((a, k) => a + depthDist[k], 0);
  const anchors: any[] = d.anchors ?? [];
  const genericAnchors = anchors.filter((a) => a.generic).length;
  const base = site?.url;

  const anchorColumns: Column<any>[] = [
    { key: "anchor", header: "Ankertext", render: (a) => <span className="block max-w-md break-words">{a.anchor || <span className="italic text-slate-400">(leer)</span>}</span> },
    { key: "links", header: "Links", align: "right", render: (a) => fmtInt(a.links) },
    { key: "targets", header: "Verschiedene Ziele", align: "right", tooltip: "Anzahl unterschiedlicher URLs mit genau diesem Ankertext", render: (a) => fmtInt(a.targets) },
    {
      key: "flags", header: "Hinweise", render: (a) => (
        <div className="flex gap-1">
          {a.generic && <Badge tone="amber" title="Allgemeine Ankertexte sagen Nutzern und Suchmaschinen nichts über das Ziel">allgemein</Badge>}
          {a.ambiguous && <Badge tone="purple" title="Derselbe Ankertext zeigt auf mehr als drei verschiedene Seiten">mehrdeutig</Badge>}
          {!a.generic && !a.ambiguous && <span className="text-slate-400">–</span>}
        </div>
      ),
    },
  ];

  return (
    <>
      {header}
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="HTML-Seiten (200)" value={fmtInt(totalPages)} />
        <Stat label="Ohne eingehende Links" value={fmtInt(inDist["0"] ?? 0)} tone={(inDist["0"] ?? 0) > 0 ? "warn" : "good"} tooltip="Seiten, auf die keine gecrawlte Seite verlinkt" />
        <Stat label="Verwaiste Seiten" value={fmtInt((d.orphans ?? []).length)} tone={(d.orphans ?? []).length ? "bad" : "good"} tooltip="Nur über die Sitemap gefunden, nicht über interne Links" />
        <Stat label="Max. Tiefe" value={maxDepth ?? "–"} hint={deepPages ? `${fmtInt(deepPages)} Seiten tiefer als 3 Klicks` : undefined} tone={maxDepth !== null && maxDepth > 5 ? "warn" : undefined} />
        <Stat label="Allgemeine Ankertexte" value={fmtInt(genericAnchors)} hint={`unter den Top ${anchors.length} Ankertexten`} tone={genericAnchors ? "warn" : "good"} />
      </div>

      <Tabs<TabId> value={tab} onChange={setTab} tabs={[
        { id: "overview", label: "Überblick" },
        { id: "top", label: "Top-Seiten", count: (d.top_pages ?? []).length },
        { id: "weak", label: "Schwache Seiten", count: (d.weak_pages ?? []).length },
        { id: "orphans", label: "Verwaist", count: (d.orphans ?? []).length },
        { id: "anchors", label: "Ankertexte", count: anchors.length },
        { id: "opportunities", label: "Linkchancen" },
        { id: "graph", label: "Linkgraph" },
      ]} />

      {tab === "overview" && (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Verteilung eingehender Links" description="Seiten nach Anzahl interner Links, die auf sie zeigen">
              <DistributionChart data={inlinkData} color={chartColors[0]} xLabel="Interne eingehende Links" />
            </Card>
            <Card title="Tiefenverteilung" description="Seiten nach Klicks ab der Start-URL">
              <DistributionChart data={depthData} color={chartColors[3]} xLabel="Crawltiefe" />
            </Card>
          </div>
          {d.pagerank_note && <Notice>{d.pagerank_note}</Notice>}
        </div>
      )}
      {tab === "top" && (
        <Card padded={false} title="Top-Seiten nach internem PageRank" description="Die Seiten, die deine eigene Verlinkung am wichtigsten nimmt. Passt das zu deinen Prioritäten?">
          <PagesTable rows={d.top_pages ?? []} crawlId={crawlId} base={base} empty={{ title: "Keine Seiten", description: "Der Crawl hat keine HTML-Seiten mit Status 200 gefunden." }} />
        </Card>
      )}
      {tab === "weak" && (
        <Card padded={false} title="Schwach verlinkte indexierbare Seiten" description="Indexierbare Seiten mit den wenigsten internen Links. Die wichtigen von verwandten, starken Seiten aus verlinken.">
          <PagesTable rows={d.weak_pages ?? []} crawlId={crawlId} base={base} empty={{ title: "Keine schwachen Seiten", description: "Keine indexierbaren Seiten gefunden." }} />
        </Card>
      )}
      {tab === "orphans" && (
        <Card padded={false} title="Verwaiste Seiten" description="Seiten aus der Sitemap, auf die keine gecrawlte Seite verlinkt. Verlinken oder aus der Sitemap nehmen.">
          <PagesTable rows={d.orphans ?? []} crawlId={crawlId} base={base} empty={{ title: "Keine verwaisten Seiten", description: "Jede Seite im Crawl ist über interne Links erreichbar." }} />
        </Card>
      )}
      {tab === "anchors" && (
        <Card padded={false} title="Interne Ankertexte" description="Die 100 häufigsten Ankertexte interner Links">
          <DataTable columns={anchorColumns} rows={anchors} rowKey={(a, i) => `${a.anchor}-${i}`} dense
            empty={<EmptyState title="Keine Ankertexte erfasst" description="Der Crawl hat keine internen Links mit Ankertext gefunden." />} />
        </Card>
      )}
      {tab === "opportunities" && (
        <Card padded={false} title="Linkchancen" description="Seiten, die das Thema einer anderen Seite erwähnen, ohne sie zu verlinken">
          <Opportunities crawlId={crawlId} base={base} />
        </Card>
      )}
      {tab === "graph" && (
        <Card title="Linkgraph" description="Radiale Ansicht nach Crawltiefe: Startseite in der Mitte, jeder Ring einen Klick weiter entfernt">
          <LinkGraph crawlId={crawlId} />
        </Card>
      )}
    </>
  );
}
