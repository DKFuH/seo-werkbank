import { Link } from "react-router-dom";
import { Card, PageHeader } from "../components/ui";

const repo = "https://github.com/DKFuH/seo-werkbank/blob/main/docs/";
const resources = [
  { title: "Erste Website anlegen und crawlen", path: "/sites", guide: "SCHNELLSTART.md", info: "Website, Crawl-Optionen, erste technische Fehler" },
  { title: "Crawls, Rendering und Bilddiagnostik", path: "/diagnostics", guide: "TECHNICAL_DIAGNOSTICS.md", info: "JavaScript und Consent getrennt prüfen; Bildhinweise sind keine LCP-Messung" },
  { title: "Google Search Console und URL Inspection", path: "/search-console", guide: "GSC_URL_INSPECTION.md", info: "OAuth, Indexierungsdaten und die Grenzen des Google-API-Ergebnisses" },
  { title: "Bing Webmaster Tools und IndexNow", path: "/bing", guide: "BING_INDEXNOW.md", info: "Bing-Daten, Schlüsseldatei und URL-Meldungen; keine Indexierungsgarantie" },
  { title: "SERP-Overlap, Relaunch und Schema", path: "/serp", guide: "ADVANCED_SEO.md", info: "Keyword-Paare, gespeicherte Crawls und strukturierte Daten" },
  { title: "Keyword- und SERP-Clustering", path: "/keywords", guide: "KEYWORD_SERP_CLUSTERING.md", info: "Lexikalische Cluster vs. tatsächliche Listenüberschneidungen" },
  { title: "PageSpeed und Monitoring", path: "/pagespeed", guide: "NOTIFICATIONS_PAGESPEED.md", info: "Einzelmessungen, Batches, Quellen und Meldungskanäle" },
  { title: "Content-Entwürfe und Freigaben", path: "/content-proposals", guide: "CONTENT_PROPOSALS.md", info: "Entwürfe werden nicht automatisch veröffentlicht" },
  { title: "GEO und KI-Quellen", path: "/ai-visibility", guide: "AUTHORITY_INTELLIGENCE.md", info: "Manuelle Beobachtungen und wiederholte Quellenstichproben" },
  { title: "Installation, Backups und Secrets", path: "/settings", guide: "SECURE_INTEGRATIONS.md", info: "Master-Key, Zugangsdaten, Verschlüsselung und Sicherheitsgrenzen" },
];

export default function Help() {
  return <div className="space-y-4">
    <PageHeader title="Hilfe und Benutzerhandbuch"
      description="Direkt zur passenden Funktion oder zur Schritt-für-Schritt-Anleitung. Alle Links führen zu öffentlichen Projektdokumenten." />
    <Card title="Hier anfangen">
      <p className="text-sm">Das <a href={repo + "BENUTZERHANDBUCH.md"} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">vollständige Benutzerhandbuch</a>
        {" "}erklärt Voraussetzungen, Klickwege, Datenquellen und Grenzen.
        {" "}Mit dem <a href={repo + "SCHNELLSTART.md"} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">Schnellstart</a>
        {" "}kannst du eine erste Analyse durchführen.</p>
    </Card>
    <div className="grid gap-3 md:grid-cols-2">
      {resources.map(r => <Card key={r.path} title={r.title}>
        <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">{r.info}</p>
        <div className="flex flex-wrap gap-4 text-sm">
          <Link to={r.path} className="text-brand-700 underline">Werkzeug öffnen</Link>
          <a href={repo + r.guide} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">Anleitung lesen</a>
        </div>
      </Card>)}
    </div>
    <Card title="Richtig interpretieren">
      <p className="text-sm">Google-API-Werte sind gemessene/externe Informationen, Keyword-/Crawl-Heuristiken
        sind Hilfen für die redaktionelle Prüfung. KI-Zitationen können manuell eingetragene Stichproben sein.
        Ein Score ist weder eine Google-Rankinggarantie noch ein rechtsverbindlicher Prüfbericht.</p>
    </Card>
  </div>;
}
