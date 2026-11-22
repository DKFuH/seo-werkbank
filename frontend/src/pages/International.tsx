import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Globe } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Badge, Card, chartColors, type Column, DataTable, EmptyState, ErrorBox, NeedsCrawl, Notice, PageHeader, Pagination, SearchInput,
  SeverityBadge, Spinner, Stat, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, shortUrl } from "../lib/format";

/** Horizontal bar list for a {value: count} distribution. */
function Distribution({ data, color, empty, highlight }: { data: Record<string, number>; color: string; empty: string; highlight?: (key: string) => "warn" | undefined }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return <p className="py-6 text-center text-sm text-slate-500 dark:text-slate-400">{empty}</p>;
  const max = Math.max(...entries.map(([, n]) => n));
  return (
    <ul className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
      {entries.map(([key, n]) => (
        <li key={key} className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-2 text-sm">
          <span className="truncate font-mono text-xs text-slate-700 dark:text-slate-300" title={key}>
            {highlight?.(key) === "warn" ? <Badge tone="amber">{key}</Badge> : key}
          </span>
          <span className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <span className="block h-full rounded-full" style={{ width: `${Math.max(2, (n / max) * 100)}%`, background: color }} />
          </span>
          <span className="text-right text-xs tabular-nums text-slate-600 dark:text-slate-300">{fmtInt(n)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function International() {
  const { site, crawlId } = useSite();
  const navigate = useNavigate();
  const q = useQuery({ queryKey: ["hreflang", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/hreflang`), enabled: !!crawlId });
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [search]);
  const perPage = 25;

  const header = <PageHeader title="Internationales SEO" description="hreflang-Angaben, Sprachattribute und Länder-URL-Struktur für Websites mit mehreren Sprachen oder Ländern." />;
  if (!crawlId) return <>{header}<NeedsCrawl hasSite={!!site} running={!!site?.active_crawl} /></>;
  if (q.isLoading) return <>{header}<Spinner /></>;
  if (q.error) return <>{header}<ErrorBox error={q.error} onRetry={() => q.refetch()} /></>;

  const d = q.data ?? {};
  const hreflang: Record<string, number> = d.hreflang_values ?? {};
  const htmlLang: Record<string, number> = d.html_lang_values ?? {};
  const locales: Record<string, number> = d.url_locales ?? {};
  const issues: any[] = d.issues ?? [];
  const pages: any[] = d.pages ?? [];
  const issueTotal = issues.reduce((a, i) => a + i.count, 0);
  const missingLang = htmlLang.missing ?? 0;
  const langCount = Object.keys(htmlLang).filter((k) => k !== "missing").length;
  const needle = search.trim().toLowerCase();
  const rows = needle ? pages.filter((p) => p.url.toLowerCase().includes(needle) || (p.alternates ?? []).some((a: any) => a.lang.toLowerCase().includes(needle))) : pages;
  const toggle = (id: number) => setExpanded((s) => {
    const next = new Set(s);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const issueColumns: Column<any>[] = [
    { key: "severity", header: "Schweregrad", render: (i) => <SeverityBadge severity={i.severity} /> },
    { key: "title", header: "Befund", render: (i) => <div className="max-w-xl"><div className="font-medium text-slate-900 dark:text-slate-100">{i.title}</div><div className="text-xs text-slate-500 dark:text-slate-400">{i.fix}</div></div> },
    { key: "count", header: "Betroffene URLs", align: "right", render: (i) => fmtInt(i.count) },
  ];
  const pageColumns: Column<any>[] = [
    {
      key: "url", header: "Seite", render: (p) => {
        const open = expanded.has(p.page_id);
        const alts: any[] = p.alternates ?? [];
        const selfRef = alts.some((a) => a.href === p.url);
        return (
          <div className="max-w-3xl">
            <div className="flex items-start gap-1.5">
              {open ? <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" /> : <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />}
              <span className="break-all font-medium text-slate-800 dark:text-slate-200">{shortUrl(p.url, site?.url)}</span>
            </div>
            {open && (
              <div className="ml-5 mt-2 rounded-md border border-slate-200 dark:border-slate-800" onClick={(e) => e.stopPropagation()}>
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {alts.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 px-2.5 py-1.5 text-xs">
                      <span className="w-20 shrink-0"><Badge tone={a.lang.toLowerCase() === "x-default" ? "purple" : "blue"}>{a.lang}</Badge></span>
                      <Url href={a.href} className="min-w-0 flex-1" />
                      {a.href === p.url && <Badge tone="green" title="Die Seite nennt sich selbst, wie es sein soll">selbst</Badge>}
                    </li>
                  ))}
                </ul>
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 bg-slate-50 px-2.5 py-1.5 text-xs dark:border-slate-800 dark:bg-slate-900/60">
                  {selfRef ? <span className="text-slate-500 dark:text-slate-400">Enthält einen Selbstverweis.</span> : <span className="text-amber-700 dark:text-amber-300">Kein selbstreferenzierender Eintrag.</span>}
                  <button className="font-medium text-brand-700 hover:underline dark:text-brand-300" onClick={() => navigate(`/pages/${crawlId}/${p.page_id}`)}>Seitendetails öffnen</button>
                </div>
              </div>
            )}
          </div>
        );
      },
    },
    { key: "lang", header: "html lang", render: (p) => (p.html_lang ? <Badge>{p.html_lang}</Badge> : <Badge tone="amber">fehlt</Badge>) },
    { key: "count", header: "Alternativen", align: "right", render: (p) => fmtInt((p.alternates ?? []).length) },
    {
      key: "langs", header: "Sprachen", render: (p) => {
        const langs: string[] = (p.alternates ?? []).map((a: any) => a.lang);
        return (
          <div className="flex max-w-xs flex-wrap gap-1">
            {langs.slice(0, 8).map((l, i) => <Badge key={`${l}-${i}`} tone={l.toLowerCase() === "x-default" ? "purple" : "gray"}>{l}</Badge>)}
            {langs.length > 8 && <span className="text-xs text-slate-500 dark:text-slate-400">+{langs.length - 8}</span>}
          </div>
        );
      },
    },
  ];

  return (
    <>
      {header}
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Seiten mit hreflang" value={fmtInt(d.pages_with_hreflang)} />
        <Stat label="hreflang-Werte" value={fmtInt(Object.keys(hreflang).length)} hint={hreflang["x-default"] ? "mit x-default" : Object.keys(hreflang).length ? "ohne x-default" : undefined} />
        <Stat label="html-lang-Werte" value={fmtInt(langCount)} hint={missingLang ? `${fmtInt(missingLang)} Seiten ohne lang` : "auf jeder Seite gesetzt"} tone={missingLang ? "warn" : undefined} />
        <Stat label="Sprachordner in URLs" value={fmtInt(Object.keys(locales).length)} tooltip="Erste Pfadsegmente, die nach Sprache aussehen, etwa /en/ oder /de-ch/" />
        <Stat label="Internationale Befunde" value={fmtInt(issueTotal)} tone={issueTotal ? "bad" : "good"} hint={`${issues.length} ${issues.length === 1 ? "Befundart" : "Befundarten"}`} />
      </div>

      {!d.is_multilingual && (
        <Card className="mb-4">
          <EmptyState icon={<Globe className="h-6 w-6" />} title="Die Website wirkt einsprachig"
            description={
              <>
                Keine hreflang-Angaben, keine zweite Sprache in den html-lang-Attributen und keine Sprachordner gefunden, es gibt also nichts
                abzugleichen. Für eine Website mit einer Zielgruppe ist das in Ordnung. Kommen später Übersetzungen oder Länderversionen dazu: jeder Version
                eine eigene URL geben (z. B. /en/ und /de/), gegenseitige hreflang-Links samt Selbstverweis und x-default setzen, passendes
                html lang auf jeder Seite und neu crawlen. Die Statistik der Sprachattribute unten gilt trotzdem.
              </>
            } />
        </Card>
      )}

      {(d.is_multilingual || issues.length > 0) && (
        <Card padded={false} title="Befunde" description="Befund anklicken, um die betroffenen URLs zu sehen" className="mb-4">
          <DataTable columns={issueColumns} rows={issues} rowKey={(i) => i.id} onRowClick={(i) => navigate(`/audit/issues/${i.id}`)}
            empty={<EmptyState title="Keine internationalen Befunde" description="hreflang-Angaben und Sprachattribute bestehen alle Prüfungen." />} />
        </Card>
      )}

      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Card title="hreflang-Werte" description="Anzahl der Angaben je Sprach-/Regionscode">
          <Distribution data={hreflang} color={chartColors[0]} empty="Keine hreflang-Angaben gefunden." />
        </Card>
        <Card title="html-lang-Attribut" description="Seiten je angegebener Dokumentsprache">
          <Distribution data={htmlLang} color={chartColors[1]} empty="Keine HTML-Seiten in diesem Crawl." highlight={(k) => (k === "missing" ? "warn" : undefined)} />
        </Card>
        <Card title="Sprachordner in URLs" description="Seiten je Sprach-Pfadsegment">
          <Distribution data={locales} color={chartColors[3]} empty="Keine Sprachordner wie /en/ oder /fr-ca/ in den URLs." />
        </Card>
      </div>

      {missingLang > 0 && (
        <div className="mb-4"><Notice tone="warn">{fmtInt(missingLang)} {missingLang === 1 ? "Seite hat" : "Seiten haben"} kein lang-Attribut am &lt;html&gt;-Element. Screenreader und Übersetzungstools brauchen es. Betroffene URLs im <Link to="/audit" className="font-medium underline">Audit</Link>.</Notice></div>
      )}

      {d.is_multilingual && (
        <Card padded={false} title="Seiten mit hreflang" description="Zeile anklicken, um die Alternativen zu sehen" actions={<SearchInput value={search} onChange={setSearch} placeholder="Nach URL oder Sprache filtern…" />}>
          <DataTable columns={pageColumns} rows={rows.slice((page - 1) * perPage, page * perPage)} rowKey={(p) => p.page_id} onRowClick={(p) => toggle(p.page_id)}
            empty={<EmptyState title={pages.length ? "Keine passenden Seiten" : "Keine hreflang-Angaben im HTML"}
              description={pages.length ? "Suchbegriff ändern." : "Die Website nutzt mehrere Sprachen oder Sprachordner, aber keine Seite nennt hreflang-Alternativen im <head>. Ergänzen, damit Suchmaschinen die richtige Version ausspielen."} />} />
          {rows.length > 0 && <Pagination page={page} perPage={perPage} total={rows.length} onPage={setPage} />}
        </Card>
      )}
      {d.is_multilingual && (
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Bis zu 500 Seiten und 40 Alternativen je Seite. {d.sitemap_checked ? "Für die Website wurden Sitemaps gefunden; hreflang, das nur in Sitemaps steht, fehlt in dieser Tabelle." : "Keine Sitemap gefunden, daher wurde nur hreflang im HTML gelesen."}
        </p>
      )}
    </>
  );
}
