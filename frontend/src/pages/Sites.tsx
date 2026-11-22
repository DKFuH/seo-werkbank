import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, type Column, DataTable, EmptyState, ErrorBox, Field, Input, Modal, PageHeader, Spinner, Url } from "../components/ui";
import { api } from "../lib/api";
import { type Site, useSite } from "../lib/context";
import { fmtInt, fmtNum, scoreColor, timeAgo } from "../lib/format";
import { cleanConfig, type CrawlCfg, CrawlConfigForm } from "./Crawler";

function AddSiteModal({ onClose, onCreated }: { onClose: () => void; onCreated: (s: Site) => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const create = useMutation({ mutationFn: () => api.post<Site>("/sites", { name: name.trim(), url: url.trim() }), onSuccess: onCreated });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <Modal open onClose={onClose} title="Website hinzufügen"
      footer={<>
        <Button onClick={onClose}>Abbrechen</Button>
        <Button variant="primary" type="submit" form="add-site" loading={create.isPending} disabled={!name.trim() || url.trim().length < 3}>Website hinzufügen</Button>
      </>}>
      <form id="add-site" onSubmit={submit} className="space-y-4">
        <Field label="Name" hint="So erscheint die Website in der App.">
          <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={255} placeholder="Meine Website" autoFocus required />
        </Field>
        <Field label="URL" hint="Start-URL für Crawls, meist die Startseite. Private und lokale Adressen kann der Server sperren.">
          <Input value={url} onChange={(e) => setUrl(e.target.value)} maxLength={2048} placeholder="https://example.de" inputMode="url" required />
        </Field>
        {create.error && <ErrorBox error={create.error} />}
      </form>
    </Modal>
  );
}

function EditSiteModal({ site, onClose, onSaved }: { site: Site; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(site.name);
  const [cfg, setCfg] = useState<CrawlCfg>({ ...site.crawl_config });
  const save = useMutation({ mutationFn: () => api.patch(`/sites/${site.id}`, { name: name.trim(), crawl_config: cleanConfig(cfg) }), onSuccess: onSaved });
  return (
    <Modal open wide onClose={onClose} title={`${site.name} bearbeiten`}
      footer={<>
        <Button onClick={onClose}>Abbrechen</Button>
        <Button variant="primary" loading={save.isPending} disabled={!name.trim()} onClick={() => save.mutate()}>Änderungen speichern</Button>
      </>}>
      <div className="space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} maxLength={255} /></Field>
          <Field label="URL" hint="Die URL lässt sich nicht ändern. Lege stattdessen eine neue Website an."><Input value={site.url} disabled readOnly /></Field>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Standard-Crawleinstellungen</h3>
          <p className="mb-3 mt-0.5 text-xs text-slate-500 dark:text-slate-400">Gilt für jeden neuen Crawl dieser Website. Pro Crawl lässt sie sich auf der Crawler-Seite überschreiben.</p>
          <CrawlConfigForm value={cfg} onChange={setCfg} advanced />
        </div>
        {save.error && <ErrorBox error={save.error} />}
      </div>
    </Modal>
  );
}

export default function Sites() {
  const { sites, site: selected, loading, setSiteId, refresh } = useSite();
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Site | null>(null);
  const [deleting, setDeleting] = useState<Site | null>(null);

  const afterChange = () => {
    refresh();
    for (const key of ["dashboard", "overview"]) void qc.invalidateQueries({ queryKey: [key] });
  };
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/sites/${id}`),
    onSuccess: () => {
      setDeleting(null);
      afterChange();
    },
  });

  const columns: Column<Site>[] = [
    { key: "name", header: "Website", render: (s) => (
      <div className="flex items-center gap-2">
        <span className="font-medium text-slate-900 dark:text-slate-100">{s.name}</span>
        {selected?.id === s.id && <Badge tone="blue">ausgewählt</Badge>}
        {s.active_crawl && <Link to="/crawler" onClick={() => setSiteId(s.id)}><Badge tone="purple">crawlt…</Badge></Link>}
      </div>
    ) },
    { key: "url", header: "URL", render: (s) => <div className="max-w-[22rem] truncate"><Url href={s.url} /></div> },
    { key: "score", header: "Score", align: "right", render: (s) => (s.last_crawl?.score === null || s.last_crawl?.score === undefined ? <span className="text-slate-400">–</span>
      : <span className="font-semibold" style={{ color: scoreColor(s.last_crawl.score) }}>{fmtNum(s.last_crawl.score, 0)}</span>) },
    { key: "pages", header: "URLs", align: "right", render: (s) => (s.last_crawl ? fmtInt(s.last_crawl.pages_crawled) : "–") },
    { key: "crawl", header: "Letzter Crawl", render: (s) => (s.last_crawl ? timeAgo(s.last_crawl.finished_at) : <span className="text-slate-400">nie</span>) },
    { key: "actions", header: "", align: "right", render: (s) => (
      <span className="inline-flex items-center gap-1">
        <Button size="sm" disabled={selected?.id === s.id} onClick={() => setSiteId(s.id)}>{selected?.id === s.id ? "Ausgewählt" : "Auswählen"}</Button>
        <Button size="sm" variant="ghost" aria-label={`${s.name} bearbeiten`} onClick={() => setEditing(s)}><Pencil className="h-4 w-4" /></Button>
        <Button size="sm" variant="ghost" aria-label={`${s.name} löschen`} onClick={() => { remove.reset(); setDeleting(s); }}><Trash2 className="h-4 w-4" /></Button>
      </span>
    ) },
  ];

  return (
    <>
      <PageHeader title="Websites" description="Die Websites, die du prüfst. Die ausgewählte Website bestimmt alle anderen Ansichten."
        actions={<Button variant="primary" icon={<Plus className="h-4 w-4" />} onClick={() => setAdding(true)}>Website hinzufügen</Button>} />
      <Card padded={false}>
        {loading ? <Spinner /> : (
          <DataTable columns={columns} rows={sites} rowKey={(s) => s.id}
            empty={<EmptyState icon={<Globe className="h-6 w-6" />} title="Noch keine Websites" description="Lege deine erste Website an und starte einen Crawl für das technische SEO-Audit."
              action={<Button variant="primary" icon={<Plus className="h-4 w-4" />} onClick={() => setAdding(true)}>Website hinzufügen</Button>} />} />
        )}
      </Card>

      {adding && <AddSiteModal onClose={() => setAdding(false)} onCreated={(s) => { setAdding(false); setSiteId(s.id); afterChange(); }} />}
      {editing && <EditSiteModal key={editing.id} site={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); afterChange(); }} />}

      <Modal open={deleting !== null} onClose={() => setDeleting(null)} title={`${deleting?.name ?? "Website"} löschen?`}
        footer={<>
          <Button onClick={() => setDeleting(null)}>Website behalten</Button>
          <Button variant="danger" loading={remove.isPending} onClick={() => deleting && remove.mutate(deleting.id)}>Website und Daten löschen</Button>
        </>}>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          This permanently deletes <span className="font-medium text-slate-900 dark:text-slate-100">{deleting?.url}</span> together with all of its crawl data:
          every crawl, page, issue and link, plus its keywords, backlinks, competitors, monitors and alerts. Any running crawl is cancelled. This cannot be undone.
        </p>
        {remove.error && <div className="mt-3"><ErrorBox error={remove.error} /></div>}
      </Modal>
    </>
  );
}
