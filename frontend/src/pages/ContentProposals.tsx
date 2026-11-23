import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Item = { id: number; kind: string; title: string; status: string; target_url: string };
type ItemsResponse = { items: Item[] };
type Proposal = { exists: boolean; work_item_id: number; status?: "draft" | "approved" | "published";
  original_text?: string; proposed_text?: string; rationale?: string; approved_at?: string | null;
  marked_published_at?: string | null; diff?: string[]; diff_truncated?: boolean;
  remote_publication?: false; note?: string; content_type?: string; safe_html?: string | null };

export default function ContentProposals() {
  const { site } = useSite();
  const [params] = useSearchParams();
  const qc = useQueryClient();
  const [selected, setSelected] = useState(0);
  const [original, setOriginal] = useState("");
  const [proposed, setProposed] = useState("");
  const [rationale, setRationale] = useState("");
  const [dirty, setDirty] = useState(false);
  const items = useQuery<ItemsResponse>({
    queryKey: ["proposal-work-items", site?.id],
    queryFn: () => api.get("/sites/" + site!.id + "/seo-work", { kind: "content" }), enabled: !!site,
  });
  const choices = items.data?.items ?? [];
  const requested = Number(params.get("item") ?? 0);
  const id = choices.some((i) => i.id === selected) ? selected :
    choices.some((i) => i.id === requested) ? requested : (choices[0]?.id ?? 0);
  const path = "/sites/" + site?.id + "/seo-work/" + id + "/content-proposal";
  const qKey = ["content-proposal", site?.id, id];
  const proposal = useQuery<Proposal>({ queryKey: qKey, queryFn: () => api.get(path), enabled: !!site && id > 0 });
  useEffect(() => {
    setOriginal(proposal.data?.original_text ?? "");
    setProposed(proposal.data?.proposed_text ?? "");
    setRationale(proposal.data?.rationale ?? "");
    setDirty(false);
  }, [proposal.data, id]);
  const invalidate = () => { void qc.invalidateQueries({ queryKey: qKey });
    void qc.invalidateQueries({ queryKey: ["proposal-work-items", site?.id] });
    void qc.invalidateQueries({ queryKey: ["seo-work", site?.id] }); };
  const save = useMutation({ mutationFn: () => api.put(path, {
    original_text: original, proposed_text: proposed, rationale,
  }), onSuccess: invalidate });
  const action = useMutation({ mutationFn: (operation: string) => api.post(path + "/" + operation),
    onSuccess: invalidate });
  const selectedWork = choices.find((x) => x.id === id);
  const editable = !proposal.data?.exists || proposal.data.status === "draft";

  return <div className="space-y-4">
    <PageHeader title="Redaktionelle Content-Entwürfe" description="Manuell verfasste Änderungsentwürfe dauerhaft speichern, vergleichen und getrennt freigeben – ohne CMS-Veröffentlichung." />
    <Card>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Eine Content-Aufgabe wird unter <Link className="font-medium text-brand-700 underline dark:text-brand-300" to="/seo-work">SEO-Maßnahmen</Link> angelegt.
        Die SEO-Chancen aus <Link className="font-medium text-brand-700 underline dark:text-brand-300" to="/content-refresh">Content-Refresh</Link> können als redaktionelle Grundlage dienen.
        <strong> Keine KI-Autogenerierung und kein Zugriff auf fremde CMS:</strong> beide Texte stammen aus deinen Eingaben.
      </p>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {items.isLoading && <Card><Spinner /></Card>}
    {items.error && <ErrorBox error={items.error} onRetry={() => items.refetch()} />}
    {site && items.data && !choices.length && <Card><EmptyState title="Keine Content-Vorgänge" description="Zuerst unter SEO-Maßnahmen einen Vorgang vom Typ Inhaltsänderung anlegen." /></Card>}
    {!!choices.length && <Card title="Content-Vorgang">
      <Field label="Zu bearbeitender Vorgang">
        <Select value={id} onChange={(e) => { setSelected(Number(e.target.value)); }}>
          {choices.map((i) => <option key={i.id} value={i.id}>{i.title} · {i.target_url}</option>)}
        </Select>
      </Field>
      {selectedWork && <p className="mt-2 break-all text-xs text-slate-500">Ziel: {selectedWork.target_url}</p>}
    </Card>}
    {proposal.isLoading && <Card><Spinner /></Card>}
    {proposal.error && <ErrorBox error={proposal.error} onRetry={() => proposal.refetch()} />}
    {proposal.data && <Card title="Revision" actions={<Badge tone={proposal.data.status === "approved" ? "green" : proposal.data.status === "published" ? "blue" : "gray"}>
      {proposal.data.exists ? proposal.data.status : "noch kein Entwurf"}
    </Badge>}>
      {proposal.data.content_type === "application/ld+json" && <div className="mb-3 space-y-2">
        <p className="text-sm font-medium text-amber-700 dark:text-amber-300">JSON-LD-Schemaentwurf: Der gespeicherte Entwurf ist reines JSON. Nicht unverändert zwischen HTML-Script-Tags kopieren; dafür ausschließlich den sicheren HTML-Block unten verwenden. Freigabe ist keine Veröffentlichung.</p>
        {proposal.data.safe_html && <div>
          <p className="mb-1 text-xs font-semibold">Sicherer HTML-Einbettungsblock (nur bei gespeichertem Entwurf aktuell)</p>
          <pre className="max-h-48 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">{proposal.data.safe_html}</pre>
        </div>}
      </div>}
      <div className="grid gap-3 lg:grid-cols-2">
        <Field label="Ausgangstext (manuell, optional)">
          <Textarea rows={9} maxLength={100000} value={original} disabled={!editable}
            onChange={(e) => { setOriginal(e.target.value); setDirty(true); }} />
        </Field>
        <Field label="Geplanter neuer Text">
          <Textarea rows={9} maxLength={100000} value={proposed} disabled={!editable}
            onChange={(e) => { setProposed(e.target.value); setDirty(true); }} />
        </Field>
      </div>
      <div className="mt-3">
        <Field label="Änderungsgrund und redaktionelle Belege">
          <Textarea rows={3} maxLength={10000} value={rationale} disabled={!editable}
            onChange={(e) => { setRationale(e.target.value); setDirty(true); }} />
        </Field>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {editable && <Button variant="primary" disabled={!proposed.trim() || save.isPending || action.isPending}
          onClick={() => save.mutate()} loading={save.isPending}>Entwurf speichern</Button>}
        {proposal.data.exists && proposal.data.status === "draft" && <Button
          disabled={dirty || save.isPending || action.isPending}
          onClick={() => { if (window.confirm("Den gespeicherten Entwurf separat freigeben?")) action.mutate("approve"); }}>
          Entwurf freigeben
        </Button>}
        {proposal.data.status === "approved" && <>
          <Button disabled={action.isPending} onClick={() => action.mutate("reopen")}>Zurück in Bearbeitung</Button>
          <Button variant="primary" disabled={action.isPending}
            onClick={() => { if (window.confirm("Nur als extern veröffentlicht markieren? Es wird nichts an ein CMS gesendet.")) action.mutate("mark-published"); }}>
            Externe Veröffentlichung dokumentieren
          </Button>
        </>}
      </div>
      {dirty && <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">Ungespeicherte Änderungen: zum Freigeben zuerst speichern.</p>}
      {save.error && <ErrorBox error={save.error} />}
      {action.error && <ErrorBox error={action.error} />}
      {proposal.data.diff && proposal.data.diff.length > 0 && <div className="mt-4">
        <h3 className="mb-2 text-sm font-semibold">Textvergleich des gespeicherten Entwurfs</h3>
        <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{proposal.data.diff.join("\n")}</pre>
        {proposal.data.diff_truncated && <p className="text-xs text-amber-700">Diff auf 350 Zeilen begrenzt.</p>}
      </div>}
      <p className="mt-3 text-xs text-slate-500">Freigabe ist eine interne Workflow-Aktion. Auch der Status „published“ dokumentiert nur eine manuell bestätigte externe Veröffentlichung.</p>
    </Card>}
  </div>;
}
