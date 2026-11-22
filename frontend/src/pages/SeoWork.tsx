import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtDate, fmtInt, fmtNum, shortUrl } from "../lib/format";

type Kind = "content" | "review" | "publication" | "local" | "competitor";
type WorkItem = { id: number; title: string; kind: Kind; status: string; target_url: string | null; source_url: string | null;
  evidence_url: string | null; notes: string; updated_at: string; };
type Snapshot = { id: number; label: string; start_date: string; end_date: string; source: string; clicks: number;
  impressions: number; position: number | null; };
type WorkResult = { items: WorkItem[]; states: Record<Kind, string[]>; note: string };
const labels: Record<Kind, string> = { content: "Inhaltsänderung", review: "Bewertung", publication: "Veröffentlichung",
  local: "Lokale SEO-Maßnahme", competitor: "Wettbewerbsbeobachtung" };
const kinds: Kind[] = ["content", "review", "publication", "local", "competitor"];

function Snapshots({ siteId, item }: { siteId: number; item: WorkItem }) {
  const qc = useQueryClient();
  const path = "/sites/" + siteId + "/seo-work/" + item.id + "/snapshots";
  const data = useQuery<Snapshot[]>({ queryKey: ["work-snapshots", siteId, item.id], queryFn: () => api.get(path) });
  const mutation = useMutation({ mutationFn: (label: string) => api.post(path, { label, days: 28 }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["work-snapshots", siteId, item.id] }) });
  if (item.kind !== "content" || !item.target_url) return null;
  const before = data.data?.find((s) => s.label === "baseline");
  const after = data.data?.filter((s) => s.label === "followup").at(-1);
  return <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
    <div className="flex flex-wrap items-center gap-2">
      <Button size="sm" disabled={!!before || mutation.isPending} onClick={() => mutation.mutate("baseline")}>28-Tage-Baseline messen</Button>
      <Button size="sm" disabled={!before || mutation.isPending} onClick={() => mutation.mutate("followup")}>Folgemessung aufnehmen</Button>
    </div>
    {mutation.error && <ErrorBox error={mutation.error} />}
    {data.error && <ErrorBox error={data.error} />}
    {(data.data ?? []).map((s) => <p key={s.id} className="mt-2 text-xs text-slate-500">
      {s.label === "baseline" ? "Ausgangswert" : "Folgemessung"} · {s.start_date} bis {s.end_date} · {s.source.toUpperCase()}:
      {" "}{fmtInt(s.clicks)} Klicks, {fmtInt(s.impressions)} Impressionen, Ø Pos. {fmtNum(s.position)}
    </p>)}
    {before && after && <p className="mt-2 text-xs font-medium">Klickdifferenz: {fmtInt(after.clicks - before.clicks)}.
      Kein Kausalnachweis: Zeitraum, Saisonalität und weitere Änderungen berücksichtigen.</p>}
  </div>;
}

export default function SeoWork() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [kind, setKind] = useState<Kind>("content");
  const [title, setTitle] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [filter, setFilter] = useState<Kind | "all">("all");
  const queryKey = ["seo-work", site?.id];
  const list = useQuery<WorkResult>({ queryKey, queryFn: () => api.get("/sites/" + site!.id + "/seo-work"), enabled: !!site });
  const add = useMutation({ mutationFn: () => api.post("/sites/" + site!.id + "/seo-work", {
    kind, status: kind === "competitor" ? "observed" : "planned", title, target_url: targetUrl.trim() || null, source_url: sourceUrl.trim() || null,
    evidence_url: evidenceUrl.trim() || null, notes }),
    onSuccess: () => { setTitle(""); setTargetUrl(""); setSourceUrl(""); setEvidenceUrl(""); setNotes("");
      void qc.invalidateQueries({ queryKey }); } });
  const update = useMutation({ mutationFn: ({ id, status }: { id: number; status: string }) =>
    api.patch("/sites/" + site!.id + "/seo-work/" + id, { status }),
    onSuccess: () => void qc.invalidateQueries({ queryKey }) });
  const remove = useMutation({ mutationFn: (id: number) => api.del("/sites/" + site!.id + "/seo-work/" + id),
    onSuccess: () => void qc.invalidateQueries({ queryKey }) });
  return <div className="space-y-4">
    <PageHeader title="SEO-Maßnahmenverwaltung" description="Inhalte, Bewertungen, Veröffentlichungen, lokale Maßnahmen und Wettbewerbsbeobachtungen nachvollziehbar bearbeiten." />
    <Card title="Neuen Vorgang dokumentieren">
      <form className="grid gap-3 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); add.mutate(); }}>
        <Field label="Vorgangstyp"><Select value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
          {kinds.map((k) => <option key={k} value={k}>{labels[k]}</option>)}
        </Select></Field>
        <Field label="Titel"><Input required maxLength={300} value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label="Ziel-URL (bei Inhalten erforderlich)"><Input type="url" maxLength={2048} required={kind === "content"} value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} /></Field>
        <Field label="Quell-URL / Profil"><Input type="url" maxLength={2048} value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} /></Field>
        <Field label="Nachweis-URL"><Input type="url" maxLength={2048} value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} /></Field>
        <Field label="Notizen"><Textarea rows={2} maxLength={12000} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <div><Button variant="primary" type="submit" loading={add.isPending} disabled={!site}>Vorgang anlegen</Button></div>
      </form>
      {add.error && <ErrorBox error={add.error} />}
      <p className="mt-3 text-xs text-slate-500">Alle Statusangaben sind manuell. Bewertungen müssen authentisch sein; keine selektive Einladung positiver Kunden.
        Es werden weder Beiträge veröffentlicht noch Bewertungen versendet oder Links gesetzt.</p>
    </Card>
    <Card title="Vorgänge">
      <Field label="Filter">
        <Select value={filter} onChange={(e) => setFilter(e.target.value as Kind | "all")}>
          <option value="all">Alle</option>{kinds.map((k) => <option key={k} value={k}>{labels[k]}</option>)}
        </Select>
      </Field>
    </Card>
    {list.isLoading && <Card><Spinner /></Card>}
    {list.error && <ErrorBox error={list.error} onRetry={() => list.refetch()} />}
    {list.data?.items.filter((i) => filter === "all" || i.kind === filter).length === 0 && <Card><EmptyState title="Keine Vorgänge erfasst" /></Card>}
    {list.data?.items.filter((i) => filter === "all" || i.kind === filter).map((item) => <Card key={item.id} title={item.title}
      description={labels[item.kind] + " · aktualisiert " + fmtDate(item.updated_at)}
      actions={<Button size="sm" variant="ghost" disabled={remove.isPending}
        onClick={() => { if (window.confirm("Diesen Vorgang einschließlich Messungen löschen?")) remove.mutate(item.id); }}>Löschen</Button>}>
      <div className="flex flex-wrap items-center gap-3">
        <Badge>{item.status}</Badge>
        <Select aria-label={"Status von " + item.title} value={item.status}
          onChange={(e) => update.mutate({ id: item.id, status: e.target.value })}>
          {(list.data?.states[item.kind] ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
      </div>
      {item.target_url && <p className="mt-2 break-all text-xs">Ziel: {shortUrl(item.target_url)}</p>}
      {item.source_url && <p className="mt-1 break-all text-xs">Quelle: {item.source_url}</p>}
      {item.evidence_url && <p className="mt-1 break-all text-xs">Nachweis: {item.evidence_url}</p>}
      {item.notes && <p className="mt-2 whitespace-pre-wrap text-sm">{item.notes}</p>}
      {site && <Snapshots siteId={site.id} item={item} />}
    </Card>)}
    {update.error && <ErrorBox error={update.error} />}
    {remove.error && <ErrorBox error={remove.error} />}
  </div>;
}
