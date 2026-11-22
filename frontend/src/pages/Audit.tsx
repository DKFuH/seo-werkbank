import { useQuery } from "@tanstack/react-query";
import { FileDown, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import {
  Badge, Button, Card, chartColors, type Column, DataTable, EmptyState, ErrorBox, ExportMenu, NeedsCrawl, PageHeader, ScoreRing, SearchInput, Select,
  SeverityBadge, Spinner, Stat,
} from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { type CrawlSummary, useSite } from "../lib/context";
import { fmtDateTime, fmtInt, fmtNum, SEVERITIES, titleCase } from "../lib/format";

const tooltipStyle = { background: "#0f172a", border: "none", borderRadius: 8, color: "#f1f5f9", fontSize: 12 };
const axisTick = { fontSize: 11, fill: "#94a3b8" };

function Change({ value, goodWhenUp }: { value: number; goodWhenUp?: boolean }) {
  if (!value) return <span className="inline-flex items-center gap-1 text-slate-500"><Minus className="h-3.5 w-3.5" />0</span>;
  const good = goodWhenUp ? value > 0 : value < 0;
  const Icon = value > 0 ? TrendingUp : TrendingDown;
  return (
    <span className={`inline-flex items-center gap-1 font-medium tabular-nums ${good ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
      <Icon className="h-3.5 w-3.5" />{value > 0 ? "+" : ""}{fmtNum(value, 1)}
    </span>
  );
}

function Compare({ siteId, crawlId }: { siteId: number; crawlId: number }) {
  const navigate = useNavigate();
  const crawls = useQuery<CrawlSummary[]>({ queryKey: ["crawls", siteId], queryFn: () => api.get(`/sites/${siteId}/crawls`) });
  const others = (crawls.data ?? []).filter((c) => c.status === "completed" && c.id !== crawlId);
  const [chosen, setChosen] = useState<number | null>(null);
  const previousId = others.find((c) => c.id === chosen)?.id ?? others.find((c) => c.id < crawlId)?.id ?? others[0]?.id ?? null;
  const cmp = useQuery({ queryKey: ["compare", crawlId, previousId], queryFn: () => api.get(`/crawls/${crawlId}/compare/${previousId}`), enabled: previousId !== null });

  if (crawls.isLoading) return null;
  if (crawls.error) return <ErrorBox error={crawls.error} onRetry={() => crawls.refetch()} />;
  if (previousId === null) return null; // fewer than two completed crawls

  const changed: any[] = (cmp.data?.issues ?? []).filter((i: any) => i.change !== 0);
  const columns: Column<any>[] = [
    { key: "severity", header: "Schweregrad", render: (i) => <SeverityBadge severity={i.severity} /> },
    { key: "title", header: "Befund", render: (i) => <div className="max-w-[26rem] whitespace-normal font-medium text-slate-900 dark:text-slate-100">{i.title}</div> },
    { key: "previous", header: "Vorher", align: "right", render: (i) => fmtInt(i.previous) },
    { key: "current", header: "Jetzt", align: "right", render: (i) => fmtInt(i.current) },
    { key: "change", header: "Änderung", align: "right", render: (i) => <Change value={i.change} /> },
  ];
  return (
    <Card title="Mit früherem Crawl vergleichen" description={`Crawl #${crawlId} gegen einen früheren abgeschlossenen Crawl`} padded={false}
      actions={
        <Select value={previousId} onChange={(e) => setChosen(Number(e.target.value))} className="w-auto" aria-label="Vergleichs-Crawl">
          {others.map((c) => <option key={c.id} value={c.id}>#{c.id} · {fmtDateTime(c.finished_at)}</option>)}
        </Select>
      }>
      {cmp.isLoading ? <Spinner /> : cmp.error ? <div className="p-3"><ErrorBox error={cmp.error} onRetry={() => cmp.refetch()} /></div> : (
        <>
          <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-3">
            <Stat label="Score-Änderung" value={cmp.data.score_change === null ? "–" : <Change value={cmp.data.score_change} goodWhenUp />}
              hint={`${fmtNum(cmp.data.previous.score, 0)} → ${fmtNum(cmp.data.current.score, 0)}`} />
            <Stat label="Neue URLs" value={fmtInt(cmp.data.added_count)} hint="Jetzt gefunden, im früheren Crawl nicht vorhanden" />
            <Stat label="Entfallene URLs" value={fmtInt(cmp.data.removed_count)} hint="Im früheren Crawl vorhanden, jetzt nicht gefunden" />
          </div>
          <div className="border-t border-slate-100 dark:border-slate-800">
            <DataTable columns={columns} rows={changed} rowKey={(i) => i.id} dense onRowClick={(i) => navigate(`/audit/issues/${i.id}`)}
              empty={<EmptyState title="Keine Änderung bei den Befunden" description="Jede Regel betrifft in beiden Crawls gleich viele URLs." />} />
          </div>
        </>
      )}
    </Card>
  );
}

export default function Audit() {
  const { site, crawlId, loading } = useSite();
  const navigate = useNavigate();
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["issues", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/issues`), enabled: crawlId !== null });

  const groups: any[] = q.data?.groups ?? [];
  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return groups.filter((g) => (!severity || g.severity === severity) && (!category || g.category === category)
      && (!needle || g.title.toLowerCase().includes(needle) || g.description.toLowerCase().includes(needle)));
  }, [groups, severity, category, search]);

  if (loading) return <Spinner />;
  if (!site || crawlId === null) {
    return <><PageHeader title="Website-Audit" description="Technische SEO-Befunde des letzten Crawls, nach Schweregrad sortiert." /><NeedsCrawl hasSite={!!site} running={!!site?.active_crawl} /></>;
  }

  const downloadPdf = async () => {
    setPdfBusy(true);
    setPdfError(null);
    try {
      await api.download(`/crawls/${crawlId}/report.pdf`, undefined, "seo-audit.pdf");
    } catch (e) {
      setPdfError(errorMessage(e));
    } finally {
      setPdfBusy(false);
    }
  };

  const header = (
    <PageHeader title="Website-Audit" description={<>Technische SEO-Befunde für <span className="font-medium text-slate-700 dark:text-slate-200">{site.name}</span>, nach Schweregrad sortiert.</>}
      actions={<>
        <Button icon={<FileDown className="h-4 w-4" />} loading={pdfBusy} onClick={downloadPdf}>PDF-Bericht</Button>
        <ExportMenu label="Befunde exportieren" formats={[
          { label: "Befunde (CSV)", path: `/crawls/${crawlId}/export`, query: { dataset: "issues", format: "csv" } },
          { label: "Befunde (Excel)", path: `/crawls/${crawlId}/export`, query: { dataset: "issues", format: "xlsx" } },
        ]} />
      </>} />
  );
  if (q.isLoading) return <>{header}<Spinner /></>;
  if (q.error) return <>{header}<ErrorBox error={q.error} onRetry={() => q.refetch()} /></>;

  const crawl = q.data.crawl;
  const bySeverity: Record<string, number> = q.data.by_severity ?? {};
  const categoryData = Object.entries(q.data.by_category ?? {}).map(([name, value]) => ({ name: titleCase(name), value: Number(value) })).sort((a, b) => b.value - a.value);
  const tones = { critical: "bad", high: "warn", medium: undefined, low: undefined } as const;

  const columns: Column<any>[] = [
    { key: "severity", header: "Schweregrad", render: (g) => <SeverityBadge severity={g.severity} /> },
    { key: "title", header: "Befund", render: (g) => (
      <div className="max-w-[34rem] whitespace-normal">
        <div className="font-medium text-slate-900 dark:text-slate-100">{g.title}</div>
        <div className="line-clamp-2 text-xs text-slate-500 dark:text-slate-400">{g.description}</div>
      </div>
    ) },
    { key: "category", header: "Kategorie", render: (g) => <Badge>{titleCase(g.category)}</Badge> },
    { key: "count", header: "Betroffen", align: "right", tooltip: "Betroffene URLs. Websiteweite Prüfungen zählen einmal.", render: (g) => <span className="font-semibold text-slate-900 dark:text-slate-100">{fmtInt(g.count)}</span> },
  ];

  return (
    <>
      {header}
      <div className="space-y-4">
        {pdfError && <ErrorBox error={pdfError} onRetry={downloadPdf} />}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <div className="flex items-center gap-4">
              <ScoreRing score={crawl.score} size={104} />
              <div className="min-w-0 text-sm text-slate-600 dark:text-slate-300">
                <div className="font-semibold text-slate-900 dark:text-slate-100">Crawl #{crawl.id}</div>
                <div>{fmtInt(crawl.pages_crawled)} URLs · {fmtDateTime(crawl.finished_at)}</div>
                <div className="mt-1">{fmtInt(groups.length)} issue types found</div>
              </div>
            </div>
            <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <span className="font-medium text-slate-700 dark:text-slate-300">So wird der Score berechnet: </span>{q.data.scoring}
            </p>
          </Card>
          <div className="grid grid-cols-2 gap-4 lg:col-span-2 lg:grid-cols-4">
            {SEVERITIES.map((s) => (
              <button key={s} onClick={() => setSeverity(severity === s ? "" : s)} aria-pressed={severity === s} title={`Nach ${titleCase(s)} filtern`}
                className={`rounded-xl text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${severity === s ? "ring-2 ring-brand-500" : ""}`}>
                <Stat label={titleCase(s)} value={fmtInt(bySeverity[s] ?? 0)} tone={bySeverity[s] ? tones[s] : undefined} hint={`${groups.filter((g) => g.severity === s).length} Befundarten`} />
              </button>
            ))}
            <div className="col-span-2 lg:col-span-4">
              <Card title="Befunde nach Kategorie">
                {!categoryData.length ? <EmptyState title="Keine Befunde" description="Nichts darzustellen." /> : (
                  <ResponsiveContainer width="100%" height={Math.max(150, categoryData.length * 26 + 30)}>
                    <BarChart data={categoryData} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" horizontal={false} />
                      <XAxis type="number" allowDecimals={false} tick={axisTick} />
                      <YAxis type="category" dataKey="name" width={120} tick={axisTick} />
                      <ChartTooltip contentStyle={tooltipStyle} cursor={{ fill: "#94a3b81a" }} />
                      <Bar dataKey="value" name="Befunde" radius={[0, 4, 4, 0]}>{categoryData.map((d, i) => <Cell key={d.name} fill={chartColors[i % chartColors.length]} />)}</Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </div>
          </div>
        </div>

        <Card title="Befunde" description="Befund anklicken, um betroffene URLs und die Lösung zu sehen." padded={false}>
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
            <SearchInput value={search} onChange={setSearch} placeholder="Befunde suchen…" />
            <Select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-auto" aria-label="Schweregrad-Filter">
              <option value="">Alle Schweregrade</option>
              {SEVERITIES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
            </Select>
            <Select value={category} onChange={(e) => setCategory(e.target.value)} className="w-auto" aria-label="Kategorie-Filter">
              <option value="">Alle Kategorien</option>
              {Object.keys(q.data.by_category ?? {}).map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
            </Select>
            <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">{rows.length} of {groups.length}</span>
          </div>
          <DataTable columns={columns} rows={rows} rowKey={(g) => g.id} onRowClick={(g) => navigate(`/audit/issues/${g.id}`)}
            empty={groups.length ? <EmptyState title="Keine passenden Befunde" description="Suche oder Filter zurücksetzen, um alle Befunde zu sehen." />
              : <EmptyState title="Keine Befunde" description="Der letzte Crawl hat keine Audit-Regel ausgelöst." />} />
        </Card>

        <Compare siteId={site.id} crawlId={crawlId} />
      </div>
    </>
  );
}
