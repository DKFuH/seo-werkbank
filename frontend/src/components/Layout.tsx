import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import {
  Activity, Bell, FileSearch, FileText, Gauge, Globe2, Languages, LayoutDashboard, Link2, LogOut, MapPin, Menu, Moon, Network,
  PenLine, Search, Settings, Share2, ListTree, Sun, Swords, Braces, Bug, KeyRound, LineChart, X, Sigma, Bot, BarChart3,
  ChevronRight, ClipboardList, Eye, FilePen, History, Microscope, Radar, RefreshCw, ShieldCheck, Target, TrendingUp, BadgeEuro,
  MapPinned, MessageSquareQuote, Sparkles, Lightbulb,
} from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth, useSite, useTheme } from "../lib/context";
import { scoreColor } from "../lib/format";
import { Select } from "./ui";

export interface NavGroup {
  section: string;
  /** One line under the section name, so a group says what question it answers. */
  hint?: string;
  /** Always-open groups have no toggle. */
  fixed?: boolean;
  items: { to: string; label: string; icon: ReactNode }[];
}

const i = (Icon: typeof Bug) => <Icon className="h-4 w-4" />;

/**
 * Grouped by the question a user brings, not by when a feature was built:
 * Analyse (is the site technically sound?), Sichtbarkeit (where are we found?), Content (what do we write?),
 * Conversion (does it pay off?), Maßnahmen (what do we do next?).
 */
export const NAV: NavGroup[] = [
  { section: "Übersicht", fixed: true, items: [
    { to: "/", label: "Dashboard", icon: i(LayoutDashboard) },
    { to: "/sites", label: "Websites", icon: i(Globe2) },
  ] },
  { section: "Analyse", hint: "Technischer Zustand", items: [
    { to: "/audit", label: "Website-Audit", icon: i(Bug) },
    { to: "/crawler", label: "Crawler", icon: i(FileSearch) },
    { to: "/internal-links", label: "Interne Verlinkung", icon: i(Network) },
    { to: "/sitemaps", label: "Sitemaps & Indexierung", icon: i(ListTree) },
    { to: "/schema", label: "Strukturierte Daten", icon: i(Braces) },
    { to: "/pagespeed", label: "PageSpeed", icon: i(Gauge) },
    { to: "/international", label: "Internationales SEO", icon: i(Languages) },
    { to: "/local", label: "Lokales SEO", icon: i(MapPin) },
  ] },
  { section: "Sichtbarkeit", hint: "Google, KI-Antworten, Wettbewerb", items: [
    { to: "/search-console", label: "Search Console", icon: i(LineChart) },
    { to: "/rank-tracking", label: "Ranktracker", icon: i(TrendingUp) },
    { to: "/keywords", label: "Keyword-Recherche", icon: i(KeyRound) },
    { to: "/serp", label: "SERP-Analyse", icon: i(Search) },
    { to: "/ai-visibility", label: "KI-Erwähnungen", icon: i(Eye) },
    { to: "/ai-intelligence", label: "KI-Empfehlungen & Referrals", icon: i(Sparkles) },
    { to: "/geo", label: "GEO-Check", icon: i(Bot) },
    { to: "/research-monitoring", label: "SEO-Verlauf & GEO", icon: i(History) },
    { to: "/competitors", label: "Wettbewerber", icon: i(Swords) },
    { to: "/competitor-radar", label: "Themenradar", icon: i(Radar) },
    { to: "/backlinks", label: "Backlinks", icon: i(Link2) },
  ] },
  { section: "Content", hint: "Recherche, Texte, Qualität", items: [
    { to: "/research", label: "SEO-Research", icon: i(Microscope) },
    { to: "/content", label: "Content-Optimierung", icon: i(PenLine) },
    { to: "/wdf-idf", label: "WDF*IDF", icon: i(Sigma) },
    { to: "/content-refresh", label: "Content-Refresh", icon: i(RefreshCw) },
    { to: "/content-proposals", label: "Content-Entwürfe", icon: i(FilePen) },
    { to: "/content-studio", label: "Content Studio", icon: i(Lightbulb) },
    { to: "/research-quality", label: "Qualität & CRO", icon: i(MessageSquareQuote) },
  ] },
  { section: "Conversion", hint: "Besucher, Vertrauen, Wert", items: [
    { to: "/matomo", label: "Matomo", icon: i(BarChart3) },
    { to: "/conversion-trust", label: "Conversion & Trust", icon: i(ShieldCheck) },
    { to: "/opportunity-value", label: "Wirtschaftliche Chancen", icon: i(BadgeEuro) },
  ] },
  { section: "Maßnahmen", hint: "Aufgaben und Nachweise", items: [
    { to: "/seo-work", label: "SEO-Maßnahmen", icon: i(ClipboardList) },
    { to: "/seo-evidence", label: "Lokale Nachweise", icon: i(MapPinned) },
    { to: "/monitoring", label: "Monitoring", icon: i(Activity) },
    { to: "/reports", label: "Berichte", icon: i(FileText) },
  ] },
  { section: "System", fixed: true, items: [
    { to: "/settings", label: "Einstellungen", icon: i(Settings) },
  ] },
];

/** Section that holds the current route; a nested route such as /audit/issues/x belongs to /audit. */
export function sectionFor(pathname: string): string | undefined {
  let best: { section: string; len: number } | undefined;
  for (const g of NAV) {
    for (const item of g.items) {
      const hit = item.to === "/" ? pathname === "/" : pathname === item.to || pathname.startsWith(item.to + "/");
      if (hit && (!best || item.to.length > best.len)) best = { section: g.section, len: item.to.length };
    }
  }
  return best?.section;
}

const NAV_KEY = "seo-werkbank:nav-open";

function readOpen(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(NAV_KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function NavGroupBlock({ group, active, open, onToggle }: { group: NavGroup; active: boolean; open: boolean; onToggle: () => void }) {
  const expanded = group.fixed || open || active;
  const id = "nav-" + group.section.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return (
    <div>
      {group.fixed ? (
        <div className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">{group.section}</div>
      ) : (
        <button type="button" onClick={onToggle} aria-expanded={expanded} aria-controls={id} disabled={active}
          title={active ? "Enthält die geöffnete Seite" : undefined}
          className={clsx("group flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-left transition",
            !active && "hover:bg-slate-100 dark:hover:bg-slate-800")}>
          <ChevronRight className={clsx("h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform", expanded && "rotate-90")} />
          <span className="min-w-0 flex-1">
            <span className={clsx("block text-[11px] font-semibold uppercase tracking-wider",
              active ? "text-brand-700 dark:text-brand-300" : "text-slate-500 dark:text-slate-400")}>{group.section}</span>
            {group.hint && !expanded && <span className="block truncate text-[11px] text-slate-400 dark:text-slate-500">{group.hint}</span>}
          </span>
          {!expanded && <span className="text-[11px] tabular-nums text-slate-400 dark:text-slate-500">{group.items.length}</span>}
        </button>
      )}
      {expanded && (
        <ul id={id} className={clsx("space-y-0.5", !group.fixed && "mt-0.5")}>
          {group.items.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.to === "/"}
                className={({ isActive }) => clsx("flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition",
                  isActive ? "bg-brand-50 font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-200"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-50")}>
                {item.icon}{item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2 px-1">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white"><Share2 className="h-4 w-4" /></span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold text-slate-900 dark:text-slate-50">SEO-Werkbank</span>
        <span className="block text-[11px] text-slate-500 dark:text-slate-400">Sichtbarkeit &amp; Content</span>
      </span>
    </Link>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { sites, site, setSiteId } = useSite();
  const [dark, toggleTheme] = useTheme();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  const { data: alerts } = useQuery({ queryKey: ["alerts", "unread"], queryFn: () => api.get("/alerts", { unread: true, per_page: 1 }), refetchInterval: 60_000 });
  const unread = alerts?.unread ?? 0;
  const activeSection = sectionFor(location.pathname);
  const [openGroups, setOpenGroups] = useState<string[]>(readOpen);
  const toggleGroup = (section: string) => setOpenGroups((prev) => {
    const next = prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section];
    try { localStorage.setItem(NAV_KEY, JSON.stringify(next)); } catch { /* storage unavailable: keep in memory only */ }
    return next;
  });

  const sidebar = (
    <nav className="flex h-full flex-col gap-3 overflow-y-auto px-3 py-4" aria-label="Hauptnavigation">
      <Brand />
      {NAV.map((group) => (
        <NavGroupBlock key={group.section} group={group} active={group.section === activeSection}
          open={openGroups.includes(group.section)} onToggle={() => toggleGroup(group.section)} />
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <button className="absolute right-2 top-3 rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => setOpen(false)} aria-label="Menü schließen"><X className="h-5 w-5" /></button>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
          <button className="rounded p-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden" onClick={() => setOpen(true)} aria-label="Menü öffnen"><Menu className="h-5 w-5" /></button>
          {sites.length > 0 ? (
            <div className="flex min-w-0 items-center gap-2">
              <Select aria-label="Ausgewählte Website" value={site?.id ?? ""} onChange={(e) => setSiteId(Number(e.target.value))} className="max-w-[16rem]">
                {sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
              {site?.last_crawl?.score !== null && site?.last_crawl?.score !== undefined && (
                <span className="hidden items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 sm:flex" title="SEO-Score des letzten abgeschlossenen Crawls">
                  <span className="h-2 w-2 rounded-full" style={{ background: scoreColor(site.last_crawl.score) }} />
                  score {Math.round(site.last_crawl.score)}
                </span>
              )}
              {site?.active_crawl && <span className="hidden rounded-md bg-brand-50 px-1.5 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-200 sm:inline">crawlt…</span>}
            </div>
          ) : (
            <Link to="/sites" className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">Erste Website anlegen</Link>
          )}
          <div className="ml-auto flex items-center gap-1">
            <Link to="/monitoring?tab=alerts" className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" aria-label={`Meldungen (${unread} ungelesen)`}>
              <Bell className="h-4 w-4" />
              {unread > 0 && <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">{unread > 99 ? "99+" : unread}</span>}
            </Link>
            <button onClick={toggleTheme} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" aria-label={dark ? "Helles Design" : "Dunkles Design"}>
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <span className="mx-1 hidden text-xs text-slate-500 dark:text-slate-400 md:inline">{user?.email}</span>
            <button onClick={logout} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" aria-label="Abmelden"><LogOut className="h-4 w-4" /></button>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
