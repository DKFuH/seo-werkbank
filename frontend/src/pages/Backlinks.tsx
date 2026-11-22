import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip as ChartTooltip } from "recharts";
import {
  Badge, Button, Card, chartColors, type Column, DataBadge, DataTable, EmptyState, ErrorBox, ExportMenu, FileButton, Modal, NeedsCrawl, Notice,
  PageHeader, Pagination, ProgressBar, SearchInput, Select, Spinner, Stat, StatusCode, Tabs, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { type Job, useJob, useSite } from "../lib/context";
import { fmtDate, fmtInt, shortUrl, timeAgo } from "../lib/format";

type Tab = "links" | "domains" | "anchors" | "targets" | "opportunities";
const PER_PAGE = 50;
const STATUS_TONE: Record<string, string> = { live: "green", lost: "red", unverified: "gray", source_error: "orange" };
const FALLBACK_COVERAGE = "Gezeigt werden nur Links aus importierten Datensätzen. Das ist kein vollständiges Bild aller Links auf deine Website.";

function RelBadge({ nofollow }: { nofollow: boolean | null }) {
  return nofollow === null || nofollow === undefined ? <Badge title="Die importierte Datei enthielt keine rel-Angabe und der Link wurde noch nicht geprüft">unbekannt</Badge>
    : nofollow ? <Badge tone="amber">nofollow</Badge> : <Badge tone="green">follow</Badge>;
}

function LinksTab({ siteId, siteUrl }: { siteId: number; siteUrl: string }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [rel, setRel] = useState("");
  const [page, setPage] = useState(1);
  const list = useQuery({
    queryKey: ["backlinks", siteId, "list", q, status, rel, page],
    queryFn: () => api.get(`/sites/${siteId}/backlinks`, { q, status, rel, page, per_page: PER_PAGE }),
    placeholderData: keepPreviousData,
  });
  const columns: Column<any>[] = [
    { key: "source", header: "Verweisende Seite", render: (b) => (
      <div className="max-w-sm">
        <Url href={b.source_url} label={shortUrl(b.source_url)} />
        <div className="text-xs text-slate-500 dark:text-slate-400">{b.source_domain}{String(b.origin).endsWith("domain-level") && " · domain-level row (no page URL in the import)"}</div>
      </div>
    ) },
    { key: "target", header: "Ziel", render: (b) => (b.target_url ? <Url href={b.target_url} label={shortUrl(b.target_url, siteUrl)} className="block max-w-xs" /> : <span className="text-slate-400">–</span>) },
    { key: "anchor", header: "Anker", render: (b) => (b.anchor ? <span className="block max-w-xs break-words">{b.anchor}</span> : <span className="text-slate-400">–</span>) },
    { key: "rel", header: "Rel", render: (b) => <RelBadge nofollow={b.nofollow} /> },
    { key: "status", header: "Status", tooltip: "Aus Links prüfen: live = Link auf der Seite gefunden, verloren = Seite lädt, aber ohne Link, Quellfehler = Seite nicht ladbar",
      render: (b) => <span className="inline-flex items-center gap-1"><Badge tone={STATUS_TONE[b.status] ?? "gray"}>{String(b.status).replace("_", " ")}</Badge>{b.http_status ? <StatusCode code={b.http_status} /> : null}</span> },
    { key: "origin", header: "Herkunft", render: (b) => <Badge tone="blue" title="Datensatz, aus dem diese Zeile stammt">{String(b.origin).split(":")[0]}</Badge> },
    { key: "first", header: "Erstmals gesehen", tooltip: "Wann die Zeile zuerst in dieses Tool importiert wurde", render: (b) => fmtDate(b.first_seen) },
    { key: "checked", header: "Zuletzt geprüft", render: (b) => (b.last_checked ? timeAgo(b.last_checked) : <span className="text-slate-400">nie</span>) },
  ];
  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="URL oder Anker suchen…" />
        <Select className="w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Nach Status filtern">
          <option value="">Alle Status</option>
          <option value="live">Live</option>
          <option value="lost">Verloren</option>
          <option value="unverified">Ungeprüft</option>
          <option value="source_error">Quellfehler</option>
        </Select>
        <Select className="w-auto" value={rel} onChange={(e) => { setRel(e.target.value); setPage(1); }} aria-label="Nach rel filtern">
          <option value="">Follow + nofollow</option>
          <option value="follow">Follow</option>
          <option value="nofollow">Nofollow</option>
        </Select>
      </div>
      {list.isLoading ? <Spinner /> : list.error ? <div className="p-3"><ErrorBox error={list.error} onRetry={() => list.refetch()} /></div> : (
        <>
          <DataTable dense columns={columns} rows={list.data?.items ?? []} rowKey={(b) => b.id}
            empty={<EmptyState title="Keine passenden Links" description="Suche oder Filter ändern." />} />
          <Pagination page={page} perPage={PER_PAGE} total={list.data?.total ?? 0} onPage={setPage} />
        </>
      )}
    </Card>
  );
}

export default function Backlinks() {
  const { site } = useSite();
  const qc = useQueryClient();
  const siteId = site?.id;
  const [tab, setTab] = useState<Tab>("links");
  const [origin, setOrigin] = useState("import");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [jobId, setJobId] = useState<number | null>(null);
  const [verifyResult, setVerifyResult] = useState<Job | null>(null);

  const summary = useQuery({ queryKey: ["backlinks", siteId, "summary"], queryFn: () => api.get(`/sites/${siteId}/backlinks/summary`), enabled: !!siteId });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["backlinks", siteId] });
  const importCsv = useMutation({ mutationFn: (file: File) => api.upload(`/sites/${siteId}/backlinks/import`, file, { origin }), onSuccess: refresh });
  const verify = useMutation({
    mutationFn: () => api.post(`/sites/${siteId}/backlinks/verify`),
    onSuccess: (r) => { setVerifyResult(null); setJobId(r.job_id); },
  });
  const clear = useMutation({
    mutationFn: () => api.del(`/sites/${siteId}/backlinks`),
    onSuccess: () => { setConfirmDelete(false); importCsv.reset(); setVerifyResult(null); refresh(); },
  });
  const job = useJob(jobId, (j) => { setJobId(null); setVerifyResult(j); refresh(); });

  if (!site) return <NeedsCrawl hasSite={false} />;

  const s = summary.data;
  const total: number = s?.total ?? 0;
  const statuses = (s?.statuses ?? {}) as Record<string, number>;
  const anchorTypes = Object.entries((s?.anchor_types ?? {}) as Record<string, number>).map(([name, value]) => ({ name, value }));
  const verifying = verify.isPending || !!jobId;

  const domainColumns: Column<any>[] = [
    { key: "domain", header: "Verweisende Domain", render: (d) => <Url href={`https://${d.domain}`} label={d.domain} /> },
    { key: "n", header: "Backlinks", align: "right", render: (d) => fmtInt(d.backlinks) },
    { key: "first", header: "Erstmals gesehen", tooltip: "Frühestes Importdatum dieser Domain", render: (d) => fmtDate(d.first_seen) },
  ];
  const anchorColumns: Column<any>[] = [
    { key: "anchor", header: "Ankertext", render: (a) => <span className="block max-w-md break-words">{a.anchor}</span> },
    { key: "n", header: "Links", align: "right", render: (a) => fmtInt(a.count) },
    { key: "share", header: "Anteil", align: "right", render: (a) => (total ? `${((a.count / total) * 100).toFixed(1)}%` : "–") },
  ];
  const targetColumns: Column<any>[] = [
    { key: "url", header: "Verlinkte Seite bei dir", render: (t) => <Url href={t.url} label={shortUrl(t.url, site.url)} className="block max-w-lg" /> },
    { key: "n", header: "Backlinks", align: "right", render: (t) => fmtInt(t.backlinks) },
    { key: "status", header: "Status im letzten Crawl", render: (t) => !t.in_crawl ? <Badge title="Der letzte Crawl hat diese URL nicht erreicht">nicht im Crawl</Badge>
      : <span className="inline-flex items-center gap-1.5"><StatusCode code={t.status} error="keine Antwort" />{(t.status === null || t.status >= 400) && <Badge tone="red">defekt</Badge>}</span> },
  ];
  const oppColumns: Column<any>[] = [
    { key: "type", header: "Typ", render: (o) => <Badge tone="orange">{o.type}</Badge> },
    { key: "url", header: "Seite", render: (o) => <Url href={o.url} label={shortUrl(o.url, site.url)} className="block max-w-sm" /> },
    { key: "n", header: "Backlinks", align: "right", render: (o) => fmtInt(o.backlinks) },
    { key: "action", header: "Empfohlene Maßnahme", render: (o) => <span className="block max-w-md whitespace-normal">{o.action}</span> },
  ];

  return (
    <div>
      <PageHeader title="Backlinks"
        description="Vorhandene Backlink-Daten analysieren und prüfen. Dieses Tool hat keinen eigenen Linkindex, hier wird also nichts geschätzt."
        actions={<>
          <Select className="w-auto" value={origin} onChange={(e) => setOrigin(e.target.value)} aria-label="Herkunft der Importdatei" title="Kennzeichnung, die mit den Zeilen gespeichert wird">
            <option value="import">Herkunft: allgemeiner Import</option>
            <option value="gsc">Herkunft: Search Console</option>
            <option value="other">Herkunft: anderes Tool</option>
          </Select>
          <FileButton label="CSV importieren" loading={importCsv.isPending} onFile={(f) => importCsv.mutate(f)} />
          <Button icon={<ShieldCheck className="h-4 w-4" />} loading={verifying} disabled={!total} onClick={() => verify.mutate()}>Links prüfen</Button>
          <ExportMenu formats={[
            { label: "CSV", path: `/sites/${site.id}/backlinks/export`, query: { format: "csv" } },
            { label: "Excel (XLSX)", path: `/sites/${site.id}/backlinks/export`, query: { format: "xlsx" } },
          ]} />
          <Button variant="ghost" icon={<Trash2 className="h-4 w-4" />} disabled={!total} onClick={() => setConfirmDelete(true)}>Alle löschen</Button>
        </>} />

      <div className="space-y-4">
        <Notice tone="warn">
          <p className="font-medium">{s?.coverage_note ?? FALLBACK_COVERAGE}</p>
          <p className="mt-1">Daten stammen nur aus deinen Importen: Links-Export der Search Console, Exporte anderer Backlink-Tools oder eine CSV mit Quelle, Ziel und Anker. Importierte Zeilen sind <DataBadge kind="imported" />; Status, Anker und rel werden <DataBadge kind="measured" />, sobald du Links prüfen ausführst.</p>
        </Notice>

        {importCsv.error && <ErrorBox error={importCsv.error} />}
        {importCsv.data && <Notice tone="success">Import finished: {fmtInt(importCsv.data.added)} links added, {fmtInt(importCsv.data.skipped)} skipped (duplicates or invalid URLs). Columns detected: {(importCsv.data.columns_detected ?? []).join(", ") || "none"}.</Notice>}
        {verify.error && <ErrorBox error={verify.error} onRetry={() => verify.mutate()} />}
        {jobId && <Card><ProgressBar value={job?.progress ?? 0} label={job?.message ?? "Prüfung startet…"} /></Card>}
        {verifyResult && (verifyResult.status === "completed" ? (
          <Notice tone="success">Verification finished: {fmtInt(verifyResult.result?.checked ?? 0)} linking pages checked, {fmtInt(verifyResult.result?.live ?? 0)} live, {fmtInt(verifyResult.result?.lost ?? 0)} lost, {fmtInt(verifyResult.result?.source_error ?? 0)} could not be loaded. Each run checks up to 300 links, least recently checked first.</Notice>
        ) : <ErrorBox error={verifyResult.error ?? `Verification ${verifyResult.status}.`} />)}

        {summary.isLoading ? <Card><Spinner /></Card> : summary.error ? <ErrorBox error={summary.error} onRetry={() => summary.refetch()} /> : !total ? (
          <Card>
            <EmptyState icon={<Link2 className="h-6 w-6" />} title="Noch keine Backlink-Daten importiert"
              description="Linkdatei importieren, um verweisende Domains, Anker und Linkziele auszuwerten und zu prüfen, welche Links noch live sind."
              action={<FileButton label="CSV importieren" loading={importCsv.isPending} onFile={(f) => importCsv.mutate(f)} />} />
            <div className="mx-auto max-w-2xl border-t border-slate-100 px-2 pb-4 pt-4 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">So bekommst du den Links-Export aus der Google Search Console</h3>
              <ol className="mt-2 list-decimal space-y-1 pl-5">
                <li>Search Console öffnen und die Property wählen.</li>
                <li>Links im Menü <span className="font-medium">Links</span> öffnen.</li>
                <li>Oben rechts <span className="font-medium">Externe Links exportieren</span> und <span className="font-medium">Weitere Beispiel-Links</span> oder <span className="font-medium">Neueste Links</span> wählen, als CSV herunterladen.</li>
                <li>Oben „Herkunft: Search Console“ wählen und die Datei hier importieren.</li>
              </ol>
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                Jede CSV funktioniert, die eine Quellspalte hat (z. B. „Verweisende Seite“, „Linking page“, „Source URL“) oder eine Spalte „Website“/„Site“. Optional: Ziel („Ziel-URL“, „Target URL“), Anker („Ankertext“) und rel („Nofollow“, „Link type“). Deutsche und englische Exporte werden erkannt. Dateien, die nur verlinkende Websites nennen, werden als Domain-Zeilen gespeichert und lassen sich nicht prüfen.
              </p>
            </div>
          </Card>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Stat label="Backlinks" value={fmtInt(total)} hint={<span className="inline-flex flex-wrap items-center gap-1"><DataBadge kind="imported" />{Object.entries((s.origins ?? {}) as Record<string, number>).map(([o, c]) => `${o}: ${fmtInt(c)}`).join(" · ")}</span>} />
              <Stat label="Verweisende Domains" value={fmtInt(s.referring_domains)} />
              <Stat label="Follow / nofollow" value={<>{fmtInt(s.follow)} <span className="text-slate-400">/</span> {fmtInt(s.nofollow)}</>} hint={`${fmtInt(s.rel_unknown)} mit unbekanntem rel`} />
              <Stat label="Neu, letzte 30 Tage" value={fmtInt(s.new_last_30_days)} tooltip="In den letzten 30 Tagen erstmals importierte Zeilen. Das ist das Importdatum, nicht das Entstehungsdatum des Links." />
              <Stat label="Live / verloren" value={<><span className="text-emerald-600 dark:text-emerald-400">{fmtInt(statuses.live ?? 0)}</span> <span className="text-slate-400">/</span> <span className={statuses.lost ? "text-red-600 dark:text-red-400" : ""}>{fmtInt(statuses.lost ?? 0)}</span></>}
                hint={<span className="inline-flex items-center gap-1"><DataBadge kind="measured" />{statuses.source_error ? `${fmtInt(statuses.source_error)} Quellfehler` : "über Links prüfen"}</span>} />
              <Stat label="Ungeprüft" value={fmtInt(statuses.unverified ?? 0)} hint="Noch nicht geprüft" />
            </div>

            <Tabs<Tab> value={tab} onChange={setTab} tabs={[
              { id: "links", label: "Links", count: total },
              { id: "domains", label: "Verweisende Domains", count: s.referring_domains },
              { id: "anchors", label: "Anker" },
              { id: "targets", label: "Linkziele", count: (s.broken_targets ?? []).length ? (s.top_targets ?? []).length : undefined },
              { id: "opportunities", label: "Chancen", count: (s.opportunities ?? []).length },
            ]} />

            {tab === "links" && <LinksTab siteId={site.id} siteUrl={site.url} />}

            {tab === "domains" && (
              <Card padded={false} title="Verweisende Domains" description="Top 100 Domains nach Anzahl importierter Links">
                <DataTable dense columns={domainColumns} rows={s.top_domains ?? []} rowKey={(d) => d.domain} />
              </Card>
            )}

            {tab === "anchors" && (
              <div className="grid gap-4 lg:grid-cols-3">
                <Card title={<span className="inline-flex items-center gap-2">Ankertypen <DataBadge kind="estimated" /></span>} description="Mit einfachen Regeln aus Ankertext und Domainname eingeordnet">
                  {anchorTypes.length ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie data={anchorTypes} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2} stroke="none">
                          {anchorTypes.map((_, i) => <Cell key={i} fill={chartColors[i % chartColors.length]} />)}
                        </Pie>
                        <ChartTooltip contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8, fontSize: 12 }} itemStyle={{ color: "#f8fafc" }} />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <EmptyState title="Keine Ankertexte" description="Die importierten Dateien enthalten keine Anker. Links prüfen ausführen, um sie von den verweisenden Seiten zu lesen." />}
                </Card>
                <Card padded={false} className="lg:col-span-2" title="Ankertexte" description="Top 100 Anker">
                  <div className="max-h-[32rem] overflow-y-auto">
                    <DataTable dense columns={anchorColumns} rows={s.top_anchors ?? []} rowKey={(a) => a.anchor}
                      empty={<EmptyState title="Keine Ankertexte" description="Die importierten Dateien enthalten keine Anker. Links prüfen ausführen, um sie von den verweisenden Seiten zu lesen." />} />
                  </div>
                </Card>
              </div>
            )}

            {tab === "targets" && (
              <div className="space-y-3">
                {s.crawl_used_for_targets ? (
                  (s.broken_targets ?? []).length > 0 && <Notice tone="warn">{s.broken_targets.length} linked page{s.broken_targets.length === 1 ? " is" : "s are"} broken in your latest crawl. Links pointing to them pass no value until the pages are restored or redirected.</Notice>
                ) : <Notice>Noch kein abgeschlossener Crawl, der Status der verlinkten Seiten ist daher unbekannt. <Link to="/crawler" className="font-medium underline">Crawl starten</Link>, um defekte Linkziele zu finden.</Notice>}
                <Card padded={false} title="Linkziele" description="Seiten deiner Website mit importierten Backlinks (Top 100)">
                  <DataTable dense columns={targetColumns} rows={s.top_targets ?? []} rowKey={(t) => t.url}
                    empty={<EmptyState title="Keine Ziel-URLs" description="Die Dateien sagen nicht, auf welche deiner Seiten die Links zeigen. Links prüfen ausführen, um die Ziele zu erkennen." />} />
                </Card>
              </div>
            )}

            {tab === "opportunities" && (
              <Card padded={false} title="Chancen" description="Links zurückgewinnen: Backlinks auf Seiten, die im letzten Crawl defekt sind">
                <DataTable columns={oppColumns} rows={s.opportunities ?? []} rowKey={(o) => o.url}
                  empty={<EmptyState title="Keine Chancen gefunden" description={s.crawl_used_for_targets ? "Keine der verlinkten Seiten ist im letzten Crawl defekt." : "Website crawlen, damit defekte Linkziele erkannt werden."} />} />
              </Card>
            )}
          </>
        )}
      </div>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Alle Backlinks löschen?"
        footer={<>
          <Button onClick={() => setConfirmDelete(false)}>Abbrechen</Button>
          <Button variant="danger" loading={clear.isPending} onClick={() => clear.mutate()}>Delete {fmtInt(total)} backlinks</Button>
        </>}>
        <p className="text-sm text-slate-600 dark:text-slate-300">This permanently removes every imported backlink and all verification results for {site.name}. You can import the files again afterwards.</p>
        {clear.error && <div className="mt-3"><ErrorBox error={clear.error} /></div>}
      </Modal>
    </div>
  );
}
