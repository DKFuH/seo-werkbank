import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, Checkbox, EmptyState, ErrorBox, Field, Input, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Render = { raw: { words: number; title: string | null; headings: string[]; links: number };
  rendered: { words: number; title: string | null; headings: string[]; links: number };
  changes: { words: number; title_changed: boolean; new_headings: string[] }; method: string };
type Consent = { samples: { choice: string; consent_action: string; request_count_capped: number;
  third_party_requests: number; tracker_hint_requests: number;
  requests: { elapsed_ms: number; host: string; third_party: boolean; tracker_hint: boolean }[] }[]; method: string };
type ImageReport = { crawl_id: number | null; pages: { url: string; issues: { src: string;
  position_in_markup: number; warnings: string[]; confirmed_lcp: boolean }[] }[]; method: string };

export default function Diagnostics() {
  const { site } = useSite();
  const [url, setUrl] = useState("");
  const [accept, setAccept] = useState(false);
  const [reject, setReject] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const root = "/sites/" + site?.id + "/diagnostics";
  const render = useMutation<Render>({ mutationFn: () => api.post(root + "/render", { url }) });
  const consent = useMutation<Consent>({ mutationFn: () => api.post(root + "/consent", {
    url, choices: ["initial", ...(accept ? ["accept"] : []), ...(reject ? ["reject"] : [])],
  }) });
  const images = useQuery<ImageReport>({ queryKey: ["image-diagnostics", site?.id],
    queryFn: () => api.get(root + "/images"), enabled: !!site });
  return <div className="space-y-4">
    <PageHeader title="Tracking, Rendering & Bilder" description="Gezielt ausgelöste Browserdiagnosen und Hinweise aus dem letzten Crawl – keine automatische Rechts- oder Google-Bewertung." />
    <Card title="URL prüfen">
      <Field label="Seiten-URL der ausgewählten Website"><Input type="url" required value={url}
        onChange={(e) => setUrl(e.target.value)} placeholder={site?.url || "https://example.org/"} /></Field>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button disabled={!site || !url.trim() || render.isPending} onClick={() => render.mutate()}>
          Roh-HTML und JavaScript vergleichen</Button>
      </div>
      {render.isPending && <Spinner />}
      {render.error && <ErrorBox error={render.error} />}
      {render.data && <div className="mt-3 space-y-2 text-sm">
        <p>Wörter: Roh-HTML {render.data.raw.words} · Gerendert {render.data.rendered.words}
          {" · "}Differenz {render.data.changes.words > 0 ? "+" : ""}{render.data.changes.words}</p>
        <p>Seitentitel geändert: {render.data.changes.title_changed ? "ja" : "nein"} · Links: {render.data.raw.links} → {render.data.rendered.links}</p>
        <p>Neue Überschriften: {render.data.changes.new_headings.join("; ") || "keine im Vergleich"}</p>
        <p className="text-xs text-slate-500">{render.data.method}</p>
      </div>}
    </Card>
    <Card title="Consent- und Tracking-Zeitfolge">
      <p className="mb-3 text-sm text-slate-500">Erfasst nur Anfrage-Zeitpunkte, Hostnamen, Ressourcentypen und grobe Tracker-Hinweise.
        Keine Cookies, vollständigen Request-URLs oder Tracking-Payloads. Zustimmung/Ablehnung werden ausschließlich auf ausdrücklichen Wunsch getestet.</p>
      <div className="space-y-2">
        <Checkbox checked={accept} onChange={setAccept} label="Zusätzlich frische Sitzung mit Klick auf eindeutig beschrifteten „Alle akzeptieren“-Button testen" />
        <Checkbox checked={reject} onChange={setReject} label="Zusätzlich frische Sitzung mit Klick auf eindeutig beschrifteten „Alle ablehnen“-Button testen" />
        <Checkbox checked={confirm} onChange={setConfirm} label="Ich darf die angegebene Website mit Browserinteraktionen testen." />
      </div>
      <div className="mt-3"><Button disabled={!site || !url.trim() || !confirm || consent.isPending}
        onClick={() => consent.mutate()}>Consent-Diagnose ausdrücklich starten</Button></div>
      {consent.isPending && <Spinner />}
      {consent.error && <ErrorBox error={consent.error} />}
      {consent.data?.samples.map((sample) => <div key={sample.choice} className="mt-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
        <strong>{sample.choice} · {sample.consent_action}</strong>
        <p>Anfragen (max. 120): {sample.request_count_capped} · Fremdhosts: {sample.third_party_requests}
          {" · "}mögliche Tracking-Anfragen: {sample.tracker_hint_requests}</p>
        {sample.requests.filter(x => x.third_party).slice(0,25).map((x, i) => <p className="text-xs text-slate-500" key={i}>
          {x.elapsed_ms} ms · {x.host} · {x.tracker_hint ? "Tracker-Hinweis" : "anderer Fremdhost"}</p>)}
      </div>)}
      <p className="mt-2 text-xs text-slate-500">Ein Buttonklick belegt keine gültige Einwilligung. Eine beobachtete Anfrage allein sagt nichts über die Rechtmäßigkeit aus.</p>
    </Card>
    <Card title="Bild- und mögliche LCP-Risiken (letzter Crawl)">
      {images.isLoading && <Spinner />}
      {images.error && <ErrorBox error={images.error} onRetry={() => images.refetch()} />}
      {images.data?.crawl_id === null && <EmptyState title="Zuerst Website crawlen" />}
      {images.data?.pages.length === 0 && images.data.crawl_id !== null && <EmptyState title="Keine auffälligen Bildattribute im geprüften Ausschnitt" />}
      {images.data?.pages.slice(0, 60).map((p) => <div key={p.url} className="mb-3">
        <strong className="break-all text-xs">{p.url}</strong>
        {p.issues.map((x, i) => <p key={i} className="break-all text-xs text-slate-500">
          Bild {x.position_in_markup}: {x.src} – {x.warnings.join("; ")}</p>)}
      </div>)}
      <p className="text-xs text-slate-500">{images.data?.method}</p>
    </Card>
  </div>;
}
