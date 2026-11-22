import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Bug, ClipboardList, Eye, LineChart, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Site } from "../lib/context";
import { type AiObservation, relativeChange, summarizeAi, summarizeWork, WORK_KIND_LABEL, type WorkItem } from "../lib/dashboardSummary";
import { fmtDate, fmtInt, fmtNum, fmtPct, timeAgo } from "../lib/format";
import { Badge, DataBadge } from "./ui";

/* One card per question: is the site sound, are we found in Google, are we named by AI, what do we do next?
   Each card shows only what its API actually returns and says where the number comes from. */

function AreaCard({ icon, area, title, source, to, linkLabel, children }: {
  icon: ReactNode; area: string; title: string; source: ReactNode; to: string; linkLabel: string; children: ReactNode;
}) {
  return (
    <section className="flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex items-start gap-3 px-4 pt-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{area}</div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
        </div>
        <div className="shrink-0">{source}</div>
      </header>
      <div className="flex-1 px-4 py-3">{children}</div>
      <Link to={to} className="group flex items-center justify-between border-t border-slate-100 px-4 py-2.5 text-sm font-medium text-brand-700 hover:bg-slate-50 dark:border-slate-800 dark:text-brand-300 dark:hover:bg-slate-800/50">
        {linkLabel}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
      </Link>
    </section>
  );
}

function Big({ value, label, tone }: { value: ReactNode; label: ReactNode; tone?: "good" | "warn" | "bad" }) {
  return (
    <div>
      <div className={clsx("text-3xl font-semibold tabular-nums",
        tone === "good" ? "text-emerald-600 dark:text-emerald-400" : tone === "warn" ? "text-amber-600 dark:text-amber-400"
          : tone === "bad" ? "text-red-600 dark:text-red-400" : "text-slate-900 dark:text-slate-50")}>{value}</div>
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
    </div>
  );
}

function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="truncate text-slate-500 dark:text-slate-400">{k}</dt>
          <dd className="font-medium tabular-nums text-slate-800 dark:text-slate-200">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-slate-500 dark:text-slate-400">{children}</p>;
}

function Loading() {
  return <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />Wird geladen…</div>;
}

function Failed() {
  return <p className="text-sm text-red-600 dark:text-red-400">Daten konnten nicht geladen werden.</p>;
}

function Change({ value, invert }: { value: number | null; invert?: boolean }) {
  if (value === null) return <span className="text-slate-400">kein Vergleich</span>;
  const up = value > 0;
  const good = invert ? !up : up;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={clsx("inline-flex items-center gap-0.5", value === 0 ? "text-slate-500" : good ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400")}>
      {value !== 0 && <Icon className="h-3.5 w-3.5" />}{(up ? "+" : "") + fmtPct(value)}
    </span>
  );
}

function TechnicalCard({ site }: { site: Site }) {
  const c = site.last_crawl;
  const sev = c?.issues_by_severity ?? {};
  const score = c?.score ?? null;
  return (
    <AreaCard icon={<Bug className="h-4 w-4" />} area="Analyse" title="Technisches SEO" source={c ? <DataBadge kind="measured" /> : null}
      to={c ? "/audit" : "/crawler"} linkLabel={c ? "Audit öffnen" : "Crawl starten"}>
      {!c ? <Empty>{site.active_crawl ? "Der erste Crawl läuft gerade." : "Noch kein abgeschlossener Crawl."}</Empty> : (
        <>
          <Big value={score === null ? "–" : fmtNum(score, 0)} label="SEO-Score des letzten Crawls"
            tone={score === null ? undefined : score >= 85 ? "good" : score >= 65 ? "warn" : "bad"} />
          <Facts items={[
            ["Kritisch", fmtInt(sev.critical ?? 0)],
            ["Hoch", fmtInt(sev.high ?? 0)],
            ["Gecrawlte Seiten", fmtInt(c.pages_crawled)],
            ["Stand", timeAgo(c.finished_at)],
          ]} />
        </>
      )}
    </AreaCard>
  );
}

function SearchCard({ site }: { site: Site }) {
  const q = useQuery({ queryKey: ["dashboard-area", "gsc", site.id], queryFn: () => api.get(`/sites/${site.id}/gsc/performance`) });
  const d = q.data;
  const t = d?.totals ?? {};
  const p = d?.dated ? d.previous : null;
  const hasPrev = !!p && (p.impressions > 0 || p.clicks > 0);
  return (
    <AreaCard icon={<LineChart className="h-4 w-4" />} area="Sichtbarkeit" title="Google-Suche"
      source={d?.has_data ? <DataBadge kind="measured" /> : null} to="/search-console" linkLabel={d?.has_data ? "Search Console öffnen" : "Search Console einrichten"}>
      {q.isLoading ? <Loading /> : q.error ? <Failed /> : !d?.has_data ? (
        <Empty>Noch keine Search-Console-Daten. Verbinden oder eine Leistungs-CSV importieren.</Empty>
      ) : (
        <>
          <Big value={fmtInt(t.clicks)} label={<>Klicks {d.dated ? `${fmtDate(d.range?.start)} – ${fmtDate(d.range?.end)}` : "(ohne Datum)"}</>} />
          <Facts items={[
            ["Impressionen", fmtInt(t.impressions)],
            ["Ø Position", t.position === null || t.position === undefined ? "–" : fmtNum(t.position)],
            ["Klicks ggü. Vorzeitraum", <Change value={hasPrev ? relativeChange(t.clicks, p.clicks) : null} />],
            ["Impressionen ggü. Vorzeitraum", <Change value={hasPrev ? relativeChange(t.impressions, p.impressions) : null} />],
          ]} />
        </>
      )}
    </AreaCard>
  );
}

function AiCard({ site }: { site: Site }) {
  const q = useQuery({ queryKey: ["dashboard-area", "ai", site.id],
    queryFn: () => api.get(`/sites/${site.id}/ai-visibility/observations`, { limit: 1000 }) });
  const s = q.data ? summarizeAi(q.data.items as AiObservation[], site.url) : null;
  return (
    <AreaCard icon={<Eye className="h-4 w-4" />} area="Sichtbarkeit" title="KI-Erwähnungen"
      source={s?.samples ? <Badge tone="gray" title="Von Hand erfasste Stichproben, nicht repräsentativ">manuell</Badge> : null}
      to="/ai-visibility" linkLabel={s?.samples ? "Beobachtungen öffnen" : "Erste Beobachtung erfassen"}>
      {q.isLoading ? <Loading /> : q.error ? <Failed /> : !s?.samples ? (
        <Empty>Noch keine Stichproben. Antworten von ChatGPT, Perplexity &amp; Co. lassen sich von Hand erfassen.</Empty>
      ) : (
        <>
          <Big value={`${fmtInt(s.mentioned)} / ${fmtInt(s.samples)}`} label="Stichproben mit Markennennung" />
          <Facts items={[
            ["Anteil", fmtPct(s.mentionShare)],
            ["Eigene URL zitiert", fmtInt(s.ownCitations)],
            ["Letzte Stichprobe", s.latest ? fmtDate(s.latest) : "–"],
          ]} />
        </>
      )}
    </AreaCard>
  );
}

function WorkCard({ site }: { site: Site }) {
  const q = useQuery({ queryKey: ["dashboard-area", "work", site.id], queryFn: () => api.get(`/sites/${site.id}/seo-work`) });
  const s = q.data ? summarizeWork(q.data.items as WorkItem[]) : null;
  return (
    <AreaCard icon={<ClipboardList className="h-4 w-4" />} area="Maßnahmen" title="Optimierungen" source={null}
      to="/seo-work" linkLabel={s?.total ? "Alle Maßnahmen" : "Erste Maßnahme anlegen"}>
      {q.isLoading ? <Loading /> : q.error ? <Failed /> : !s?.total ? (
        <Empty>Noch keine Maßnahmen. Chancen aus Content-Refresh oder Audit hier als Aufgabe festhalten.</Empty>
      ) : (
        <>
          <Big value={fmtInt(s.open)} label={`offen · ${fmtInt(s.done)} erledigt`} />
          {s.open > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {Object.entries(s.byKind).map(([kind, n]) => <Badge key={kind} tone="blue">{WORK_KIND_LABEL[kind] ?? kind} {n}</Badge>)}
            </div>
          )}
          {s.next.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs">
              {s.next.map((x) => (
                <li key={x.id} className="flex items-baseline gap-2">
                  <span className="h-1.5 w-1.5 shrink-0 translate-y-[-1px] rounded-full bg-brand-500" />
                  <span className="min-w-0 flex-1 truncate text-slate-700 dark:text-slate-300" title={x.title}>{x.title}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </AreaCard>
  );
}

export default function AreaCards({ site }: { site: Site }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <TechnicalCard site={site} />
      <SearchCard site={site} />
      <AiCard site={site} />
      <WorkCard site={site} />
    </div>
  );
}
