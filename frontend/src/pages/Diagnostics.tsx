import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Checkbox, EmptyState, ErrorBox, Field, Input, PageHeader, Spinner, Stat } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Render = {
  raw: { words: number; title: string | null; headings: string[]; links: number };
  rendered: { words: number; title: string | null; headings: string[]; links: number };
  changes: { words: number; title_changed: boolean; new_headings: string[] };
  method: string;
};

type Consent = {
  samples: {
    choice: string;
    consent_action: string;
    request_count_capped: number;
    third_party_requests: number;
    tracker_hint_requests: number;
    requests: { elapsed_ms: number; host: string; third_party: boolean; tracker_hint: boolean }[];
  }[];
  method: string;
};

type ImageReport = {
  crawl_id: number | null;
  pages: { url: string; issues: { src: string; position_in_markup: number; warnings: string[]; confirmed_lcp: boolean }[] }[];
  method: string;
};

type TrackingAuditReport = {
  url: string;
  static_inspection: {
    tags: {
      google_analytics_4: string[];
      google_tag_manager: string[];
      universal_analytics_legacy: string[];
      matomo: { active: boolean; site_ids: string[]; tracker_urls: string[] };
      clarity: string[];
      meta_pixel: string[];
    };
    cmps_detected: string[];
    duplicates: string[];
    static_consent_leakage: { src: string; category: string; warning: string }[];
    conversion_targets: {
      tel_count: number;
      tel_untracked_count: number;
      tel_examples: { href: string; text: string; has_event_tracking: boolean }[];
      mailto_count: number;
      mailto_untracked_count: number;
      mailto_examples: { href: string; text: string; has_event_tracking: boolean }[];
      form_count: number;
      forms: { id: string; action: string; method: string; inputs: number; has_event_tracking: boolean }[];
    };
    has_tracking: boolean;
    recommendations: string[];
  };
  browser_trace?: {
    samples: { choice: string; consent_action: string; requests: any[] }[];
    evaluation: {
      verdict: string;
      initial_state_leakage: { has_leakage: boolean; tracking_hosts_fired_before_consent: string[] };
      reject_state_violations: { has_violations: boolean; tracking_hosts_fired_after_reject: string[] };
    };
  } | null;
  playwright_supported: boolean;
  method: string;
};

type TrackingOverview = {
  crawl_id: number | null;
  pages_audited: number;
  conversion_links: {
    tel_count: number;
    tel_examples: { target: string; page: string }[];
    mailto_count: number;
    mailto_examples: { target: string; page: string }[];
  };
  method: string;
};

export default function Diagnostics() {
  const { site } = useSite();
  const [tab, setTab] = useState<"tracking" | "consent" | "render" | "images">("tracking");
  const [url, setUrl] = useState("");
  const [runBrowser, setRunBrowser] = useState(false);
  const [accept, setAccept] = useState(false);
  const [reject, setReject] = useState(false);
  const [confirm, setConfirm] = useState(false);

  const root = "/sites/" + site?.id + "/diagnostics";

  const trackingAudit = useMutation<TrackingAuditReport>({
    mutationFn: () => api.post(root + "/tracking-audit", { url, run_browser_consent: runBrowser }),
  });

  const trackingOverview = useQuery<TrackingOverview>({
    queryKey: ["tracking-overview", site?.id],
    queryFn: () => api.get(root + "/tracking-overview"),
    enabled: !!site,
  });

  const render = useMutation<Render>({ mutationFn: () => api.post(root + "/render", { url }) });
  const consent = useMutation<Consent>({
    mutationFn: () =>
      api.post(root + "/consent", {
        url,
        choices: ["initial", ...(accept ? ["accept"] : []), ...(reject ? ["reject"] : [])],
      }),
  });
  const images = useQuery<ImageReport>({
    queryKey: ["image-diagnostics", site?.id],
    queryFn: () => api.get(root + "/images"),
    enabled: !!site,
  });

  const auditData = trackingAudit.data;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Tracking, Consent & Diagnosen"
        description="Deterministischer Audit von Tracking-Tags, Consent-Leakage, Interaktionszielen (tel/mailto) und Browser-Rendering."
      />

      <div role="tablist" aria-label="Diagnose-Bereiche" className="flex flex-wrap gap-2">
        {([
          ["tracking", "Tracking- & Consent-Audit"],
          ["consent", "Browser Consent-Trace"],
          ["render", "HTML vs. JavaScript"],
          ["images", "Bilder & LCP"],
        ] as const).map(([key, label]) => (
          <button
            role="tab"
            aria-selected={tab === key}
            key={key}
            onClick={() => setTab(key)}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
              tab === key
                ? "bg-brand-600 text-white"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "tracking" && (
        <div className="space-y-4">
          <Card title="Tracking & Consent Health Check">
            <Field label="Seiten-URL der ausgewählten Website prüfen">
              <Input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={site?.url || "https://example.org/"}
              />
            </Field>

            <div className="mt-3 space-y-2">
              <Checkbox
                checked={runBrowser}
                onChange={setRunBrowser}
                label="Zusätzlich dynamischen Playwright-Netzwerk-Trace ausführen (prüft Requests vor Consent & nach Ablehnung)"
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="primary"
                disabled={!site || !url.trim() || trackingAudit.isPending}
                onClick={() => trackingAudit.mutate()}
              >
                Tracking-Audit starten
              </Button>
            </div>

            {trackingAudit.isPending && <div className="mt-3"><Spinner label="Analysiere Tags, CMPs und Netzwerk-Requests…" /></div>}
            {trackingAudit.error && <div className="mt-3"><ErrorBox error={trackingAudit.error} /></div>}
          </Card>

          {auditData && (
            <>
              {/* Tag Detection Summary */}
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat
                  label="GA4 Measurement IDs"
                  value={auditData.static_inspection.tags.google_analytics_4.length ? auditData.static_inspection.tags.google_analytics_4.join(", ") : "Keine"}
                  tone={auditData.static_inspection.tags.google_analytics_4.length ? "good" : undefined}
                />
                <Stat
                  label="GTM Container"
                  value={auditData.static_inspection.tags.google_tag_manager.length ? auditData.static_inspection.tags.google_tag_manager.join(", ") : "Keiner"}
                />
                <Stat
                  label="Matomo / Piwik"
                  value={auditData.static_inspection.tags.matomo.active ? `Aktiv (ID ${auditData.static_inspection.tags.matomo.site_ids.join(", ") || "?"})` : "Inaktiv"}
                />
                <Stat
                  label="CMP (Consent Banner)"
                  value={auditData.static_inspection.cmps_detected.length ? auditData.static_inspection.cmps_detected.join(", ") : "Nicht erkannt"}
                  tone={auditData.static_inspection.cmps_detected.length ? "good" : "warn"}
                />
              </div>

              {/* Leakage & Warnings */}
              {(auditData.static_inspection.duplicates.length > 0 ||
                auditData.static_inspection.static_consent_leakage.length > 0 ||
                auditData.browser_trace?.evaluation.initial_state_leakage.has_leakage) && (
                <Card title="Sicherheits- & Genauigkeits-Warnungen" className="border-amber-300 dark:border-amber-700">
                  <div className="space-y-2 text-sm">
                    {auditData.browser_trace?.evaluation.initial_state_leakage.has_leakage && (
                      <div className="rounded-lg bg-red-50 p-3 text-red-800 dark:bg-red-950 dark:text-red-200">
                        <strong>Kritisch: Consent Leakage im Browser festgestellt!</strong>
                        <p className="mt-1 text-xs">
                          Folgende Tracker-Hosts wurden vor jeder Nutzerzustimmung kontaktiert:{" "}
                          {auditData.browser_trace.evaluation.initial_state_leakage.tracking_hosts_fired_before_consent.join(", ")}
                        </p>
                      </div>
                    )}
                    {auditData.static_inspection.static_consent_leakage.map((leak, i) => (
                      <div key={i} className="rounded-lg bg-amber-50 p-2 text-amber-800 dark:bg-amber-950 dark:text-amber-200 text-xs">
                        <strong>Unblockiertes Skript:</strong> {leak.src} – {leak.warning}
                      </div>
                    ))}
                    {auditData.static_inspection.duplicates.map((dup, i) => (
                      <div key={i} className="rounded-lg bg-amber-50 p-2 text-amber-800 dark:bg-amber-950 dark:text-amber-200 text-xs">
                        <strong>Doppelung:</strong> {dup}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Conversion Targets (tel, mailto, forms) */}
              <Card title="Interaktions- und Conversion-Ziele auf dieser Seite">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-xs font-semibold text-slate-500 uppercase">Telefon-Links (tel:)</div>
                    <div className="mt-1 text-xl font-bold">{auditData.static_inspection.conversion_targets.tel_count}</div>
                    <p className="mt-1 text-xs text-slate-500">
                      {auditData.static_inspection.conversion_targets.tel_untracked_count > 0 ? (
                        <span className="text-amber-600 font-medium">
                          {auditData.static_inspection.conversion_targets.tel_untracked_count} ohne Klick-Tracking-Handler
                        </span>
                      ) : (
                        <span className="text-emerald-600">Alle mit Event-Attributen</span>
                      )}
                    </p>
                    {auditData.static_inspection.conversion_targets.tel_examples.map((t, idx) => (
                      <p key={idx} className="mt-1 font-mono text-xs text-slate-600 dark:text-slate-300">
                        {t.href} {t.has_event_tracking ? "✓" : "⚠ untracked"}
                      </p>
                    ))}
                  </div>

                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-xs font-semibold text-slate-500 uppercase">E-Mail-Links (mailto:)</div>
                    <div className="mt-1 text-xl font-bold">{auditData.static_inspection.conversion_targets.mailto_count}</div>
                    <p className="mt-1 text-xs text-slate-500">
                      {auditData.static_inspection.conversion_targets.mailto_untracked_count > 0 ? (
                        <span className="text-amber-600 font-medium">
                          {auditData.static_inspection.conversion_targets.mailto_untracked_count} ohne Klick-Tracking
                        </span>
                      ) : (
                        <span className="text-emerald-600">Erfasst</span>
                      )}
                    </p>
                    {auditData.static_inspection.conversion_targets.mailto_examples.map((m, idx) => (
                      <p key={idx} className="mt-1 font-mono text-xs text-slate-600 dark:text-slate-300">
                        {m.href} {m.has_event_tracking ? "✓" : "⚠ untracked"}
                      </p>
                    ))}
                  </div>

                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-xs font-semibold text-slate-500 uppercase">Formulare (form)</div>
                    <div className="mt-1 text-xl font-bold">{auditData.static_inspection.conversion_targets.form_count}</div>
                    <p className="mt-1 text-xs text-slate-500">Formulare für Anfragen oder Kontakt</p>
                    {auditData.static_inspection.conversion_targets.forms.map((f, idx) => (
                      <p key={idx} className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                        ID: {f.id} ({f.method}, {f.inputs} Felder) {f.has_event_tracking ? "✓" : "–"}
                      </p>
                    ))}
                  </div>
                </div>
              </Card>

              {/* Recommendations */}
              {auditData.static_inspection.recommendations.length > 0 && (
                <Card title="Handlungsempfehlungen für das Conversion-Tracking">
                  <ul className="list-inside list-disc space-y-1 text-sm text-slate-700 dark:text-slate-300">
                    {auditData.static_inspection.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </Card>
              )}
            </>
          )}

          {/* Site-wide crawl summary */}
          <Card title="Gecrawlte Conversion-Links (Website-weit aus letztem Crawl)">
            {trackingOverview.isLoading && <Spinner label="Lade Link-Übersicht…" />}
            {trackingOverview.data && (
              <div className="space-y-2 text-sm">
                <p>
                  Geprüfte Seiten: {trackingOverview.data.pages_audited} · Telefon-Links (tel:):{" "}
                  <strong>{trackingOverview.data.conversion_links.tel_count}</strong> · E-Mail-Links (mailto:):{" "}
                  <strong>{trackingOverview.data.conversion_links.mailto_count}</strong>
                </p>
                {trackingOverview.data.conversion_links.tel_examples.length > 0 && (
                  <div className="mt-2 text-xs text-slate-500">
                    <strong>Gefundene Telefonnummern:</strong>{" "}
                    {trackingOverview.data.conversion_links.tel_examples.map((x) => x.target).join(", ")}
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      )}

      {tab === "consent" && (
        <Card title="Consent- und Tracking-Zeitfolge">
          <Field label="URL für Consent-Trace"><Input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder={site?.url || "https://example.org/"} /></Field>
          <p className="my-3 text-sm text-slate-500">
            Erfasst nur Anfrage-Zeitpunkte, Hostnamen, Ressourcentypen und grobe Tracker-Hinweise. Keine Cookies, vollständigen Request-URLs oder Tracking-Payloads.
          </p>
          <div className="space-y-2">
            <Checkbox checked={accept} onChange={setAccept} label="Zusätzlich frische Sitzung mit Klick auf eindeutig beschrifteten „Alle akzeptieren“-Button testen" />
            <Checkbox checked={reject} onChange={setReject} label="Zusätzlich frische Sitzung mit Klick auf eindeutig beschrifteten „Alle ablehnen“-Button testen" />
            <Checkbox checked={confirm} onChange={setConfirm} label="Ich darf die angegebene Website mit Browserinteraktionen testen." />
          </div>
          <div className="mt-3">
            <Button disabled={!site || !url.trim() || !confirm || consent.isPending} onClick={() => consent.mutate()}>
              Consent-Diagnose ausdrücklich starten
            </Button>
          </div>
          {consent.isPending && <Spinner />}
          {consent.error && <ErrorBox error={consent.error} />}
          {consent.data?.samples.map((sample) => (
            <div key={sample.choice} className="mt-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
              <strong>{sample.choice} · {sample.consent_action}</strong>
              <p>
                Anfragen (max. 120): {sample.request_count_capped} · Fremdhosts: {sample.third_party_requests} · mögliche Tracking-Anfragen: {sample.tracker_hint_requests}
              </p>
              {sample.requests
                .filter((x) => x.third_party)
                .slice(0, 25)
                .map((x, i) => (
                  <p className="text-xs text-slate-500" key={i}>
                    {x.elapsed_ms} ms · {x.host} · {x.tracker_hint ? "Tracker-Hinweis" : "anderer Fremdhost"}
                  </p>
                ))}
            </div>
          ))}
        </Card>
      )}

      {tab === "render" && (
        <Card title="Roh-HTML und JavaScript vergleichen">
          <Field label="Seiten-URL"><Input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder={site?.url || "https://example.org/"} /></Field>
          <div className="mt-3">
            <Button disabled={!site || !url.trim() || render.isPending} onClick={() => render.mutate()}>
              Vergleich ausführen
            </Button>
          </div>
          {render.isPending && <Spinner />}
          {render.error && <ErrorBox error={render.error} />}
          {render.data && (
            <div className="mt-3 space-y-2 text-sm">
              <p>
                Wörter: Roh-HTML {render.data.raw.words} · Gerendert {render.data.rendered.words} · Differenz{" "}
                {render.data.changes.words > 0 ? "+" : ""}
                {render.data.changes.words}
              </p>
              <p>
                Seitentitel geändert: {render.data.changes.title_changed ? "ja" : "nein"} · Links: {render.data.raw.links} → {render.data.rendered.links}
              </p>
              <p>Neue Überschriften: {render.data.changes.new_headings.join("; ") || "keine im Vergleich"}</p>
            </div>
          )}
        </Card>
      )}

      {tab === "images" && (
        <Card title="Bild- und mögliche LCP-Risiken (letzter Crawl)">
          {images.isLoading && <Spinner />}
          {images.error && <ErrorBox error={images.error} onRetry={() => images.refetch()} />}
          {images.data?.crawl_id === null && <EmptyState title="Zuerst Website crawlen" />}
          {images.data?.pages.length === 0 && images.data.crawl_id !== null && <EmptyState title="Keine auffälligen Bildattribute im geprüften Ausschnitt" />}
          {images.data?.pages.slice(0, 60).map((p) => (
            <div key={p.url} className="mb-3">
              <strong className="break-all text-xs">{p.url}</strong>
              {p.issues.map((x, i) => (
                <p key={i} className="break-all text-xs text-slate-500">
                  Bild {x.position_in_markup}: {x.src} – {x.warnings.join("; ")}
                </p>
              ))}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
