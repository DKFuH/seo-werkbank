import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, PlugZap, XCircle } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, ErrorBox, Field, Input, KeyValue, Notice, PageHeader, Select, Spinner } from "../components/ui";
import { api, tokenStore } from "../lib/api";
import { useAuth } from "../lib/context";

const MASK = "********";
type Section = "serp" | "pagespeed" | "ai" | "gsc" | "matomo" | "notifications";
type Values = Record<string, string>;

/** Local form state for one settings section; resets whenever the server copy changes. */
function useSection(section: Section, server: Values | undefined) {
  const qc = useQueryClient();
  const [values, setValues] = useState<Values>(server ?? {});
  const [saved, setSaved] = useState(false);
  const serverKey = JSON.stringify(server ?? {});
  useEffect(() => {
    setValues(JSON.parse(serverKey));
  }, [serverKey]);
  const save = useMutation({
    mutationFn: (v: Values) => api.put("/settings", { [section]: v }),
    onSuccess: (data) => {
      qc.setQueryData(["settings"], data);
      setSaved(true);
      // other pages cache provider/status information derived from these settings
      void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "settings" });
    },
  });
  const set = (key: string, value: string) => {
    setSaved(false);
    setValues((v) => ({ ...v, [key]: value }));
  };
  const dirty = JSON.stringify(values) !== serverKey;
  return { values, set, save, dirty, saved: saved && !dirty };
}

function SecretInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <Input type="password" autoComplete="off" value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)}
      onFocus={(e) => value === MASK && e.target.select()} />
  );
}
const secretHint = (value: string | undefined) => (value === MASK ? "Ein Wert ist gespeichert. So lassen, um ihn zu behalten, oder neuen eingeben, um ihn zu ersetzen." : "Wird in der Anwendungsdatenbank gespeichert und danach nie wieder angezeigt.");

function SaveBar({ s, children }: { s: ReturnType<typeof useSection>; children?: ReactNode }) {
  return (
    <div className="space-y-3">
      {s.save.error ? <ErrorBox error={s.save.error} /> : null}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" variant="primary" loading={s.save.isPending} disabled={!s.dirty}>Speichern</Button>
        {children}
        {s.saved && <span className="inline-flex items-center gap-1 text-xs text-emerald-700 dark:text-emerald-400"><CheckCircle2 className="h-3.5 w-3.5" /> Gespeichert</span>}
        {s.dirty && <span className="text-xs text-slate-500 dark:text-slate-400">Ungespeicherte Änderungen</span>}
      </div>
    </div>
  );
}

const ext = (href: string, label: string) => <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-brand-700 hover:underline dark:text-brand-300">{label}</a>;

/* ------------------------------------------------------------------ account */
function Account() {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const change = useMutation({
    mutationFn: () => api.post("/auth/password", { current_password: current, new_password: next }),
    onSuccess: (r: { access_token?: string }) => {
      if (r?.access_token) tokenStore.set(r.access_token); // tokens issued before the change no longer work
      setCurrent(""); setNext(""); setConfirm("");
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    change.reset();
    if (next !== confirm) return setMismatch(true);
    setMismatch(false);
    change.mutate();
  };
  return (
    <Card title="Konto">
      <div className="grid gap-6 lg:grid-cols-2">
        <KeyValue items={[
          ["E-Mail", user?.email],
          ["Rolle", user?.is_admin ? <Badge tone="blue">Administrator</Badge> : <Badge>Mitglied</Badge>],
        ]} />
        <form onSubmit={submit} className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Passwort ändern</h3>
          {change.error ? <ErrorBox error={change.error} /> : null}
          {mismatch && <ErrorBox error="Neues Passwort und Bestätigung stimmen nicht überein." />}
          {change.isSuccess && <Notice tone="success">Passwort geändert.</Notice>}
          <Field label="Aktuelles Passwort">
            <Input type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Neues Passwort" hint="Mindestens 8 Zeichen.">
              <Input type="password" autoComplete="new-password" required minLength={8} maxLength={200} value={next} onChange={(e) => setNext(e.target.value)} />
            </Field>
            <Field label="Neues Passwort bestätigen">
              <Input type="password" autoComplete="new-password" required minLength={8} maxLength={200} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </Field>
          </div>
          <Button type="submit" variant="primary" loading={change.isPending}>Passwort ändern</Button>
        </form>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ integrations */
const SERP_NOTES: Record<string, ReactNode> = {
  none: "SERP-Analyse ist aus. Alle anderen Funktionen arbeiten ohne Anbieter.",
  searxng: <>Selbst betriebene Metasuche, kostenlos und ohne eigenes Kontingent. JSON-Ausgabe in der settings.yml der Instanz aktivieren (<code>search.formats: [html, json]</code>). Die angefragten Suchmaschinen können eine viel genutzte Instanz bremsen.</>,
  google_cse: <>Google Programmable Search JSON API: 100 Abfragen pro Tag kostenlos, danach kostenpflichtig, bis zu 10 Ergebnisse je Abfrage. Braucht API-Schlüssel und Suchmaschinen-ID (cx) mit Suche im ganzen Web. Ergebnisse können von google.de abweichen.</>,
  brave: <>Brave Search API: eigener, unabhängiger Index, nicht der von Google. Der kostenlose Tarif erlaubt etwa eine Anfrage pro Sekunde und ein Monatskontingent; Details im Brave-Dashboard.</>,
};

function SerpSettings({ server }: { server: Values }) {
  const s = useSection("serp", server);
  const p = s.values.provider ?? "none";
  return (
    <Card title="SERP-Anbieter" description="Liefert SERP-Analyse und Content-Briefings live Suchergebnisse">
      <form onSubmit={(e) => { e.preventDefault(); s.save.mutate(s.values); }} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Anbieter">
            <Select value={p} onChange={(e) => s.set("provider", e.target.value)}>
              <option value="none">Keiner</option>
              <option value="searxng">SearXNG (selbst betrieben)</option>
              <option value="google_cse">Google Programmable Search</option>
              <option value="brave">Brave Search API</option>
            </Select>
          </Field>
          {p === "searxng" && (
            <Field label="SearXNG URL" hint="Basis-URL deiner Instanz inklusive http:// oder https://">
              <Input type="url" required value={s.values.searxng_url ?? ""} onChange={(e) => s.set("searxng_url", e.target.value)} placeholder="http://localhost:8080" />
            </Field>
          )}
          {p === "google_cse" && (
            <>
              <Field label="API-Schlüssel" hint={secretHint(s.values.google_cse_key)}>
                <SecretInput value={s.values.google_cse_key ?? ""} onChange={(v) => s.set("google_cse_key", v)} />
              </Field>
              <Field label="Suchmaschinen-ID (cx)">
                <Input required value={s.values.google_cse_cx ?? ""} onChange={(e) => s.set("google_cse_cx", e.target.value)} />
              </Field>
            </>
          )}
          {p === "brave" && (
            <Field label="Abo-Token" hint={secretHint(s.values.brave_key)}>
              <SecretInput value={s.values.brave_key ?? ""} onChange={(v) => s.set("brave_key", v)} />
            </Field>
          )}
        </div>
        <Notice>{SERP_NOTES[p] ?? SERP_NOTES.none}</Notice>
        <SaveBar s={s} />
      </form>
    </Card>
  );
}

function PageSpeedSettings({ server }: { server: Values }) {
  const s = useSection("pagespeed", server);
  return (
    <Card title="PageSpeed Insights" description="Lighthouse- und Core-Web-Vitals-Daten aus Googles öffentlicher API">
      <form onSubmit={(e) => { e.preventDefault(); s.save.mutate(s.values); }} className="space-y-4">
        <Field label="API-Schlüssel" className="max-w-md" hint={secretHint(s.values.api_key)}>
          <SecretInput value={s.values.api_key ?? ""} onChange={(v) => s.set("api_key", v)} placeholder="Optional" />
        </Field>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Die API ist kostenlos. Ohne Schlüssel teilen sich Anfragen ein kleines anonymes Kontingent und können mit HTTP 429 abgelehnt werden. Schlüssel in der{" "}
          {ext("https://developers.google.com/speed/docs/insights/v5/get-started", "Google Cloud Console")} anlegen („PageSpeed Insights API“ aktivieren). Feld leeren und speichern, um einen gespeicherten Schlüssel zu entfernen.
        </p>
        <SaveBar s={s} />
      </form>
    </Card>
  );
}

function MatomoSettings({ server }: { server: Values }) {
  const s = useSection("matomo", server);
  return (
    <Card title="Matomo" description="Besuche, Kanäle, Einstiegsseiten und Ziele aus deiner Matomo-Instanz">
      <form onSubmit={(e) => { e.preventDefault(); s.save.mutate(s.values); }} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Matomo-URL" hint="z. B. https://statistik.example.de/">
            <Input type="url" value={s.values.url ?? ""} onChange={(e) => s.set("url", e.target.value)} placeholder="https://…" />
          </Field>
          <Field label="token_auth" hint={secretHint(s.values.token_auth)}>
            <SecretInput value={s.values.token_auth ?? ""} onChange={(v) => s.set("token_auth", v)} placeholder="Persönlicher API-Token" />
          </Field>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Token in Matomo unter Persönlich → Sicherheit → Auth-Token anlegen; Leserechte genügen. Der Token wird nur im Formular-Body an Matomo gesendet und hier ausgeblendet gespeichert.
        </p>
        <SaveBar s={s} />
      </form>
    </Card>
  );
}

function AiSettings({ server }: { server: Values }) {
  const s = useSection("ai", server);
  const p = s.values.provider ?? "none";
  const test = useMutation({
    mutationFn: async () => {
      if (s.dirty) await s.save.mutateAsync(s.values);
      return api.get("/ai/status");
    },
  });
  const st = test.data;
  return (
    <Card title="KI-Anbieter" description="Optional. Für KI-Zusammenfassungen, Briefings und Umformulierungen; sonst hängt nichts davon ab.">
      <form onSubmit={(e) => { e.preventDefault(); test.reset(); s.save.mutate(s.values); }} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Anbieter">
            <Select value={p} onChange={(e) => s.set("provider", e.target.value)}>
              <option value="none">Keiner</option>
              <option value="ollama">Ollama (lokale Modelle)</option>
              <option value="openai_compatible">OpenAI-kompatible API</option>
            </Select>
          </Field>
          {p !== "none" && (
            <>
              <Field label="Basis-URL" hint={p === "ollama" ? "Standard: http://localhost:11434" : "API-Wurzel mit /models und /chat/completions, z. B. https://api.openai.com/v1"}>
                <Input type="url" required value={s.values.base_url ?? ""} onChange={(e) => s.set("base_url", e.target.value)} />
              </Field>
              <Field label="Modell" hint={p === "ollama" ? "Ein geladenes Modell, z. B. llama3.1" : "Modellkennung, wie die API sie erwartet"}>
                <Input required value={s.values.model ?? ""} onChange={(e) => s.set("model", e.target.value)} />
              </Field>
              {p === "openai_compatible" && (
                <Field label="API-Schlüssel" hint={secretHint(s.values.api_key)}>
                  <SecretInput value={s.values.api_key ?? ""} onChange={(v) => s.set("api_key", v)} />
                </Field>
              )}
            </>
          )}
        </div>
        <Notice>
          {p === "none" ? "Kein KI-Anbieter eingerichtet. Crawlen, Audit und Berichte funktionieren auch ohne."
            : p === "ollama" ? "Ollama betreibt Modelle auf deiner eigenen Hardware: kostenlos, privat und begrenzt durch Speicher und Tempo des Rechners. Seiteninhalte bleiben auf diesem Rechner."
            : "Prompts samt Auszügen aus Seiteninhalten gehen an die eingerichtete API. Die Nutzung rechnet der Anbieter über deinen Schlüssel ab."}
        </Notice>
        <SaveBar s={s}>
          <Button type="button" icon={<PlugZap className="h-4 w-4" />} loading={test.isPending} onClick={() => test.mutate()}>{s.dirty ? "Speichern & Verbindung testen" : "Verbindung testen"}</Button>
        </SaveBar>
        {test.error ? <ErrorBox error={test.error} /> : null}
        {st && !test.isPending && (
          <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
            <div className={`flex items-center gap-2 font-medium ${st.available ? "text-emerald-700 dark:text-emerald-400" : st.provider === "none" ? "text-slate-600 dark:text-slate-300" : "text-red-700 dark:text-red-400"}`}>
              {st.available ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />} {st.message}
            </div>
            {Array.isArray(st.models) && (
              <div className="mt-2">
                <div className="mb-1 text-xs text-slate-500 dark:text-slate-400">{st.models.length ? "In Ollama verfügbare Modelle (anklicken zum Übernehmen):" : "Ollama hat noch keine Modelle. Eines laden mit: ollama pull llama3.1"}</div>
                <div className="flex flex-wrap gap-1">
                  {st.models.map((m: string) => (
                    <button key={m} type="button" onClick={() => s.set("model", m)} aria-pressed={s.values.model === m}
                      className={`rounded-md px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset ${s.values.model === m
                        ? "bg-brand-600 text-white ring-brand-600" : "bg-slate-100 text-slate-700 ring-slate-200 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700 dark:hover:bg-slate-700"}`}>
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </form>
    </Card>
  );
}

function GscSettings({ server }: { server: Values }) {
  const s = useSection("gsc", server);
  const status = useQuery({ queryKey: ["gsc", "status"], queryFn: () => api.get("/gsc/status") });
  return (
    <Card title="Google Search Console" description="OAuth-Client zum Lesen deiner eigenen Search-Console-Daten"
      actions={status.data ? (
        <>
          {status.data.client_configured ? <Badge tone="green">Client eingerichtet</Badge> : <Badge tone="amber">Client nicht eingerichtet</Badge>}
          {status.data.connected ? <Badge tone="green">Konto verbunden</Badge> : <Badge>nicht verbunden</Badge>}
        </>
      ) : undefined}>
      <form onSubmit={(e) => { e.preventDefault(); s.save.mutate(s.values); }} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="OAuth-Client-ID">
            <Input value={s.values.client_id ?? ""} onChange={(e) => s.set("client_id", e.target.value)} placeholder="….apps.googleusercontent.com" autoComplete="off" />
          </Field>
          <Field label="OAuth-Client-Secret" hint={secretHint(s.values.client_secret)}>
            <SecretInput value={s.values.client_secret ?? ""} onChange={(v) => s.set("client_secret", v)} />
          </Field>
        </div>
        <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Autorisierte Weiterleitungs-URI</div>
          {status.isLoading ? <span className="text-slate-500 dark:text-slate-400">Wird geladen…</span> : status.error ? <ErrorBox error={status.error} onRetry={() => status.refetch()} />
            : <code className="break-all text-slate-800 dark:text-slate-200">{status.data.redirect_uri}</code>}
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-xs text-slate-600 dark:text-slate-400">
            <li>In der {ext("https://console.cloud.google.com/apis/library/searchconsole.googleapis.com", "Google Cloud Console")} ein Projekt anlegen und die „Google Search Console API“ aktivieren.</li>
            <li>OAuth-Zustimmungsbildschirm einrichten und dein Google-Konto als Testnutzer eintragen.</li>
            <li>OAuth-Client-ID vom Typ „Webanwendung“ anlegen und die Weiterleitungs-URI oben exakt eintragen.</li>
            <li>Client-ID und Secret hier einfügen und speichern.</li>
            <li><Link to="/search-console" className="font-medium text-brand-700 hover:underline dark:text-brand-300">Search Console</Link> öffnen und Verbinden wählen.</li>
          </ol>
        </div>
        <SaveBar s={s} />
      </form>
    </Card>
  );
}


function NotificationSettings({ server }: { server: Values }) {
  const s = useSection("notifications", server);
  return <Card title="Monitor-Benachrichtigungen" description="Optional: ein zusammengefasster Hinweis je Prüfdurchlauf über SMTP (STARTTLS) und/oder HTTPS-Webhook. Standard: deaktiviert.">
    <div className="space-y-3">
      <Field label="Benachrichtigung aktiv"><Select value={s.values.enabled || "false"} onChange={e => s.set("enabled", e.target.value)}>
        <option value="false">Aus</option><option value="true">Ein</option></Select></Field>
      <Field label="Mindestens Schweregrad"><Select value={s.values.min_severity || "high"} onChange={e => s.set("min_severity", e.target.value)}>
        {["low", "medium", "high", "critical"].map(x => <option key={x} value={x}>{x}</option>)}</Select></Field>
      <div className="grid gap-3 md:grid-cols-2">
        {([["smtp_host", "SMTP-Server"], ["smtp_port", "SMTP-Port (STARTTLS)"],
          ["smtp_user", "SMTP-Benutzer"], ["from_email", "Absenderadresse"],
          ["to_email", "Empfängeradresse"], ["webhook_url", "Webhook (HTTPS, Port 443)"]] as const).map(([key, label]) =>
          <Field key={key} label={label}>{key === "webhook_url"
            ? <SecretInput value={s.values[key] || ""} onChange={v => s.set(key, v)} />
            : <Input value={s.values[key] || ""} onChange={e => s.set(key, e.target.value)} />}</Field>)}
      </div>
      <Field label="SMTP-Passwort"><SecretInput value={s.values.smtp_password || ""} onChange={v => s.set("smtp_password", v)} /></Field>
      <Notice>Die Meldung enthält Website-Namen und Befundtext; nur Ziele eintragen, die diese Angaben empfangen dürfen. Fehlende SMTP- oder Webhook-Konfiguration verhindert den Versand.</Notice>
      <SaveBar s={s} />
    </div>
  </Card>;
}

function Integrations() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api.get("/settings"), enabled: isAdmin });
  if (!isAdmin) {
    return (
      <Card title="Integrationen">
        <Notice tone="warn">Integrationen (SERP-Anbieter, PageSpeed-Schlüssel, KI-Anbieter, Search-Console-Client, Matomo) gelten für die ganze Installation und können nur von Administratoren geändert werden.</Notice>
      </Card>
    );
  }
  if (q.isLoading) return <Card title="Integrationen"><Spinner /></Card>;
  if (q.error) return <Card title="Integrationen"><ErrorBox error={q.error} onRetry={() => q.refetch()} /></Card>;
  const d = q.data ?? {};
  return (
    <>
      <SerpSettings server={d.serp ?? {}} />
      <PageSpeedSettings server={d.pagespeed ?? {}} />
      <MatomoSettings server={d.matomo ?? {}} />
      <AiSettings server={d.ai ?? {}} />
      <GscSettings server={d.gsc ?? {}} />
      <NotificationSettings server={d.notifications ?? {}} />
    </>
  );
}

/* ------------------------------------------------------------------ about */
function About() {
  const status = useQuery({ queryKey: ["auth-status"], queryFn: () => api.get("/auth/status") });
  const health = useQuery({ queryKey: ["health"], queryFn: () => api.get("/health"), retry: false });
  return (
    <Card title="Über">
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          {status.isLoading ? <Spinner /> : status.error ? <ErrorBox error={status.error} onRetry={() => status.refetch()} /> : (
            <KeyValue items={[
              ["Anwendung", status.data.app],
              ["Version", status.data.version],
              ["Backend-Status", health.isLoading ? "Wird geprüft…" : health.error ? <Badge tone="red" title={health.error instanceof Error ? health.error.message : undefined}>nicht erreichbar</Badge>
                : <Badge tone={health.data?.status === "ok" ? "green" : "amber"}>{health.data?.status ?? "unknown"}</Badge>],
              ["Private Netze", status.data.private_networks_allowed
                ? <><Badge tone="amber">erlaubt</Badge><span className="ml-2 text-xs text-slate-500 dark:text-slate-400">Crawls und Abrufe dürfen localhost und private IP-Bereiche erreichen.</span></>
                : <><Badge tone="green">gesperrt</Badge><span className="ml-2 text-xs text-slate-500 dark:text-slate-400">Anfragen an localhost und private IP-Bereiche werden abgelehnt (SSRF-Schutz).</span></>],
              ["Registrierung", status.data.registration_open ? <Badge tone="amber">offen</Badge> : <Badge tone="green">geschlossen</Badge>],
            ]} />
          )}
        </div>
        <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Datenquellen und Grenzen</h3>
          <p>Alles Angezeigte stammt aus dem eigenen Crawler und der Analyse dieses Tools, aus kostenlosen Google-APIs (PageSpeed Insights, deine Search-Console-Property), aus Matomo oder aus Dateien, die du importierst.</p>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Kein Suchvolumen.</strong> Keyword-Volumen und Schwierigkeitswerte brauchen Fremddaten; sie erscheinen nur nach Import.</li>
            <li><strong>Kein eigener Backlink-Index.</strong> Backlinks beschränken sich auf Importe (z. B. den Links-Export der Search Console) und lassen sich durch Abrufen der verweisenden Seiten prüfen.</li>
            <li><strong>Rankings</strong> kommen aus der Search Console (nur eigene Website) oder vom eingerichteten SERP-Anbieter mit dessen Grenzen.</li>
            <li><strong>Indexierungsstatus</strong> lässt sich nur in der Search Console bestätigen; der Crawler meldet, ob eine Seite <em>indexierbar</em> ist.</li>
          </ul>
        </div>
      </div>
    </Card>
  );
}

export default function Settings() {
  return (
    <>
      <PageHeader title="Einstellungen" description="Dein Konto, die Integrationen dieser Installation und Informationen zur Instanz." />
      <div className="space-y-4">
        <Account />
        <Integrations />
        <About />
      </div>
    </>
  );
}
