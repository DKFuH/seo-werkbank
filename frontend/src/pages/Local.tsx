import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, MapPin, X } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Badge, Card, type Column, DataTable, EmptyState, ErrorBox, FileButton, NeedsCrawl, Notice, PageHeader, Pagination, Spinner, Stat, Url,
} from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtInt, shortUrl } from "../lib/format";

const YesNo = ({ value, yes = "yes", no = "no" }: { value: boolean; yes?: string; no?: string }) =>
  value ? <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400"><Check className="h-3.5 w-3.5" />{yes}</span>
    : <span className="inline-flex items-center gap-1 text-slate-400"><X className="h-3.5 w-3.5" />{no}</span>;

const linkClass = "font-medium text-brand-700 hover:underline dark:text-brand-300";

export default function Local() {
  const { site, crawlId } = useSite();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["local", crawlId], queryFn: () => api.get(`/crawls/${crawlId}/local`), enabled: !!crawlId });
  const [imported, setImported] = useState<number | null>(null);
  const [locPage, setLocPage] = useState(1);
  const importCitations = useMutation({
    mutationFn: (file: File) => api.upload(`/sites/${site!.id}/citations/import`, file),
    onMutate: () => setImported(null),
    onSuccess: (r) => {
      setImported(r.imported);
      void qc.invalidateQueries({ queryKey: ["local"] });
    },
  });

  const header = <PageHeader title="Lokales SEO" description="LocalBusiness-Markup, Einheitlichkeit von Name/Adresse/Telefon (NAP), Standortseiten und erfasste Brancheneinträge." />;
  if (!crawlId) return <>{header}<NeedsCrawl hasSite={!!site} running={!!site?.active_crawl} /></>;
  if (q.isLoading) return <>{header}<Spinner /></>;
  if (q.error) return <>{header}<ErrorBox error={q.error} onRetry={() => q.refetch()} /></>;

  const d = q.data ?? {};
  const nap = d.nap ?? {};
  const ref = nap.reference ?? {};
  const businesses: any[] = d.businesses ?? [];
  const locations: any[] = d.location_pages ?? [];
  const citations: any[] = d.citations ?? [];
  const inconsistent = citations.filter((c) => !c.consistent).length;
  const base = site?.url;
  const open = (r: any) => navigate(`/pages/${crawlId}/${r.page_id}`);
  const perPage = 25;

  const businessColumns: Column<any>[] = [
    { key: "name", header: "Name", render: (b) => <div className="max-w-xs"><div className="font-medium text-slate-900 dark:text-slate-100">{b.name || <span className="italic text-slate-400">kein Name</span>}</div><Url href={b.url} label={shortUrl(b.url, base)} className="text-xs" /></div> },
    { key: "phone", header: "Telefon", render: (b) => b.phone || <span className="text-slate-400">–</span> },
    { key: "address", header: "Adresse", render: (b) => <span className="block max-w-xs break-words">{b.address || <span className="text-slate-400">–</span>}</span> },
    { key: "geo", header: "Geo", render: (b) => <YesNo value={b.has_geo} /> },
    { key: "hours", header: "Öffnungszeiten", render: (b) => <YesNo value={b.has_hours} /> },
    {
      key: "problems", header: "Probleme", render: (b) => b.problems?.length ? (
        <ul className="max-w-sm list-disc space-y-0.5 pl-4 text-xs">{b.problems.map((p: string, i: number) => <li key={i} className="break-words">{p}</li>)}</ul>
      ) : <Badge tone="green">keine</Badge>,
    },
  ];
  const locationColumns: Column<any>[] = [
    { key: "url", header: "Seite", render: (l) => <div className="max-w-sm"><Url href={l.url} label={shortUrl(l.url, base)} />{l.title && <div className="truncate text-xs text-slate-500 dark:text-slate-400">{l.title}</div>}</div> },
    { key: "words", header: "Wörter", align: "right", render: (l) => fmtInt(l.word_count) },
    { key: "schema", header: "Lokales Schema", render: (l) => <YesNo value={l.has_local_schema} /> },
    { key: "map", header: "Einbettung", tooltip: "Auf der Seite wurde ein iframe gefunden (meist eine Karte)", render: (l) => <YesNo value={l.has_map} /> },
    { key: "phones", header: "Telefon im Text", tooltip: "Nur Ziffern, für den Vergleich normalisiert", render: (l) => (l.phones_in_text?.length ? <span className="font-mono text-xs">{l.phones_in_text.join(", ")}</span> : <span className="text-slate-400">–</span>) },
    {
      key: "issues", header: "Befunde", render: (l) => l.issues?.length ? (
        <div className="flex max-w-sm flex-wrap gap-1">{l.issues.map((m: string) => <Badge key={m} tone="amber">{m}</Badge>)}</div>
      ) : <Badge tone="green">keine</Badge>,
    },
  ];
  const mismatchCell = (c: any, field: string, value: string | null) => (
    <span className="block max-w-xs break-words">
      {value || <span className="text-slate-400">–</span>}
      {c.mismatches?.includes(field) && <span className="ml-1.5"><Badge tone="red" title={`Weicht vom Referenzwert (${field}) im Markup deiner Website ab`}>Abweichung</Badge></span>}
    </span>
  );
  const citationColumns: Column<any>[] = [
    { key: "source", header: "Quelle", render: (c) => <div className="font-medium text-slate-900 dark:text-slate-100">{c.source}{c.url && <div className="font-normal"><Url href={c.url} label={shortUrl(c.url)} className="text-xs" /></div>}</div> },
    { key: "name", header: "Name", render: (c) => mismatchCell(c, "name", c.name) },
    { key: "address", header: "Adresse", render: (c) => mismatchCell(c, "address", c.address) },
    { key: "phone", header: "Telefon", render: (c) => mismatchCell(c, "phone", c.phone) },
    { key: "consistent", header: "NAP", render: (c) => (c.consistent ? <Badge tone="green">einheitlich</Badge> : <Badge tone="red">{c.mismatches.length} {c.mismatches.length === 1 ? "Abweichung" : "Abweichungen"}</Badge>) },
  ];
  const variants = (n: number | undefined) => (n === undefined ? "–" : n <= 1 ? <Badge tone="green">{n} {n === 1 ? "Variante" : "Varianten"}</Badge> : <Badge tone="red">{n} Varianten</Badge>);

  return (
    <>
      {header}
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="LocalBusiness-Elemente" value={fmtInt(businesses.length)} tone={businesses.length ? undefined : "warn"} />
        <Stat label="NAP-Einheitlichkeit" value={!businesses.length ? "–" : nap.consistent ? "Einheitlich" : "Uneinheitlich"} tone={!businesses.length ? undefined : nap.consistent ? "good" : "bad"} tooltip="Ob Name, Adresse und Telefon in allen LocalBusiness-Markups der Website identisch sind" />
        <Stat label="Standortseiten" value={fmtInt(locations.length)} hint={`${fmtInt(locations.filter((l) => l.issues?.length).length)} mit Befunden`} />
        <Stat label="Erfasste Einträge" value={fmtInt(citations.length)} hint={citations.length ? `${fmtInt(inconsistent)} mit Abweichungen` : "keine importiert"} tone={inconsistent ? "bad" : undefined} />
      </div>

      {!d.has_local_schema && (
        <div className="mb-4">
          <Notice tone="warn">
            Auf dieser Website wurden keine LocalBusiness-Daten gefunden. Ohne sie gibt es keinen Referenzwert für Name, Adresse und Telefon.{" "}
            <Link to="/schema?tab=generator&type=LocalBusiness" className="font-medium underline">LocalBusiness-Markup im Schema-Generator erstellen</Link>, auf der Kontakt- oder Standortseite einbinden und neu crawlen.
          </Notice>
        </div>
      )}

      <Card title="NAP-Einheitlichkeit" description={nap.reference_source} className="mb-4"
        actions={businesses.length ? (nap.consistent ? <Badge tone="green">einheitlich</Badge> : <Badge tone="red">uneinheitlich</Badge>) : <Badge>keine Daten</Badge>}>
        {!businesses.length ? (
          <EmptyState icon={<MapPin className="h-6 w-6" />} title="Noch keine Referenz-NAP" description="Name, Adresse und Telefon werden aus dem LocalBusiness-Markup deiner Website gelesen. Markup ergänzen, um diese Prüfung zu aktivieren." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-3">
            {([["Name", ref.name, nap.name_variants], ["Telefon", ref.phone, nap.phone_variants], ["Adresse", ref.address, nap.address_variants]] as [string, string | null, number][]).map(([label, value, n]) => (
              <div key={label} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
                  {variants(n)}
                </div>
                <div className="mt-1.5 break-words text-sm font-medium text-slate-900 dark:text-slate-100">{value || <span className="font-normal text-slate-400">nicht im Markup</span>}</div>
              </div>
            ))}
            <p className="text-xs text-slate-500 dark:text-slate-400 sm:col-span-3">
              Reference values are shown in normalised form (lower case, punctuation removed; last 10 digits of phone numbers), which is how variants and citations are compared.
            </p>
          </div>
        )}
      </Card>

      <Card padded={false} title="Unternehmen in strukturierten Daten" description="Eine Zeile je LocalBusiness-Element im JSON-LD" className="mb-4">
        <DataTable columns={businessColumns} rows={businesses} rowKey={(b, i) => `${b.page_id}-${i}`} onRowClick={open}
          empty={<EmptyState title="Kein LocalBusiness-Markup" description="Keine gecrawlte Seite enthält LocalBusiness (oder einen Untertyp wie Restaurant oder Store) im JSON-LD."
            action={<Link to="/schema?tab=generator&type=LocalBusiness" className={`text-sm ${linkClass}`}>Schema-Generator öffnen</Link>} />} />
      </Card>

      <Card padded={false} title="Standortseiten" description="Seiten mit lokalem Markup oder standorttypischer URL (/kontakt, /standort, /store…)" className="mb-4">
        <DataTable columns={locationColumns} rows={locations.slice((locPage - 1) * perPage, locPage * perPage)} rowKey={(l) => l.page_id} onRowClick={open}
          empty={<EmptyState title="Keine Standortseiten gefunden" description="Keine Seite hat LocalBusiness-Markup oder eine URL mit /contact, /location, /store, /branch, /office, /find-us oder /areas." />} />
        {locations.length > 0 && <Pagination page={locPage} perPage={perPage} total={locations.length} onPage={setLocPage} />}
      </Card>

      <Card padded={false} title="Brancheneinträge" description="Einträge in Verzeichnissen und Plattformen, verglichen mit der Referenz-NAP" className="mb-4"
        actions={site ? <FileButton label="Einträge-CSV importieren" accept=".csv,.txt" loading={importCitations.isPending} onFile={(f) => importCitations.mutate(f)} /> : undefined}>
        <div className="space-y-3 border-b border-slate-100 p-4 dark:border-slate-800">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            CSV mit Kopfzeile und den Spalten <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">source</code>,{" "}
            <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">url</code>, <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">name</code>,{" "}
            <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">address</code>, <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">phone</code>.
            Pflicht ist nur <em>source</em> (z. B. „Gelbe Seiten“). Jeder Import ersetzt die bisherige Liste; bis zu 5.000 Zeilen.
          </p>
          {importCitations.error ? <ErrorBox error={importCitations.error} /> : null}
          {imported !== null && (imported > 0
            ? <Notice tone="success">Imported {fmtInt(imported)} citation{imported === 1 ? "" : "s"}.</Notice>
            : <Notice tone="warn">Keine Zeilen importiert, die bisherige Liste wurde geleert. Prüfen, ob die Datei eine Kopfzeile mit Spalte „source“ hat.</Notice>)}
        </div>
        <DataTable columns={citationColumns} rows={citations} rowKey={(c) => c.id}
          empty={<EmptyState title="Keine Einträge importiert" description="CSV deiner Verzeichniseinträge importieren und prüfen, ob überall dieselben Angaben zu Name, Adresse und Telefon stehen wie auf der Website." />} />
      </Card>

      {d.gbp_note && <Notice>{d.gbp_note}</Notice>}
    </>
  );
}
