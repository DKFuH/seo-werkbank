import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fmtPos, Movement, PositionChart, type TrendPoint } from "../components/RankCharts";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";
import { fmtDate, fmtInt } from "../lib/format";

type Detail = {
  has_data: boolean; granularity?: "day" | "week"; period?: { start: string; end: string };
  keyword: { id: number; keyword: string; label: string | null; target_url: string | null; measurement: string; priority: number;
    position: number | null; movement: number | null; impressions: number; clicks: number; best_url: string | null; url_mismatch: boolean };
  trend: TrendPoint[]; notes: { id: number; date: string; title: string; details: string }[];
};
const MEASUREMENT: Record<string, string> = { national: "National", lokal: "Lokal", marke: "Marke" };

export default function RankKeyword() {
  const { id } = useParams();
  const { site } = useSite();
  const qc = useQueryClient();
  const [days, setDays] = useState(90);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const root = `/sites/${site?.id}/rank-gsc/keywords/${id}`;
  const q = useQuery<Detail>({ queryKey: ["rank-keyword", site?.id, id, days], queryFn: () => api.get(root, { days }), enabled: !!site });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["rank-keyword", site?.id, id] });
  const addNote = useMutation({ mutationFn: () => api.post(`${root}/notes`, { event_date: date, title, details }), onSuccess: () => { setTitle(""); setDetails(""); refresh(); } });
  const delNote = useMutation({ mutationFn: (noteId: number) => api.del(`${root}/notes/${noteId}`), onSuccess: refresh });
  const untrack = useMutation({ mutationFn: () => api.patch(root, { tracked: false }), onSuccess: () => { void qc.invalidateQueries({ queryKey: ["rank-portfolio"] }); refresh(); } });

  const back = <Link to="/rank-tracking" className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">← Zurück zum Ranktracker</Link>;
  if (!site) return null;
  if (q.isLoading) return <Spinner />;
  if (q.error) return <><PageHeader title="Keyword" />{back}<ErrorBox error={q.error} /></>;
  const d = q.data!;
  const k = d.keyword;
  return (
    <>
      <PageHeader title={k.keyword} description={d.period ? `${fmtDate(d.period.start)} – ${fmtDate(d.period.end)}` : undefined}
        actions={<div className="w-36"><Select aria-label="Zeitraum" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[[28, "28 Tage"], [90, "3 Monate"], [180, "6 Monate"], [365, "12 Monate"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select></div>} />
      <div className="space-y-4">
        {back}
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <div className="flex flex-wrap gap-1"><Badge tone="gray">P{k.priority}</Badge>{k.label && <Badge tone="blue">{k.label}</Badge>}<Badge tone="gray">{MEASUREMENT[k.measurement] ?? k.measurement}</Badge></div>
            <dl className="mt-3 space-y-1 text-sm">
              <div><dt className="inline text-slate-500">Zielseite: </dt><dd className="inline">{k.target_url || "nicht festgelegt"}</dd></div>
              <div><dt className="inline text-slate-500">Ranking-URL: </dt><dd className="inline break-all">{k.best_url || "nicht beobachtet"}</dd></div>
              {k.url_mismatch && <div className="text-xs text-amber-600 dark:text-amber-400">Google zeigt eine andere Seite als die Zielseite.</div>}
            </dl>
            {untrack.isSuccess ? <p className="mt-3 text-xs text-slate-500">Aus dem Portfolio entfernt.</p>
              : <Button size="sm" variant="ghost" className="mt-3" loading={untrack.isPending} onClick={() => untrack.mutate()}>Aus dem Portfolio entfernen</Button>}
          </Card>
          <Card>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Ø Position</div>
            <div className="mt-1 text-3xl font-semibold tabular-nums">{fmtPos(k.position)}</div>
            <div className="text-sm"><Movement value={k.movement} /> zum Vorzeitraum</div>
          </Card>
          <Card>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Nachfrage im Zeitraum</div>
            <div className="mt-1 text-3xl font-semibold tabular-nums">{fmtInt(k.impressions)}</div>
            <div className="text-sm text-slate-500">Impressionen · {fmtInt(k.clicks)} Klicks</div>
          </Card>
        </div>
        <Card title="Positionsverlauf" description="Aus der Search Console, nach Impressionen gewichtet. Orange Linien markieren Einträge im Änderungsjournal.">
          {d.has_data ? <PositionChart points={d.trend} notes={d.notes} granularity={d.granularity ?? "day"} />
            : <EmptyState title="Noch keine Search-Console-Daten" />}
        </Card>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="SEO-Maßnahme notieren" description="Was wurde wann geändert? Erscheint als Markierung im Verlauf.">
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); addNote.mutate(); }}>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Datum"><Input type="date" required value={date} onChange={(e) => setDate(e.target.value)} /></Field>
                <Field label="Änderung" className="sm:col-span-2"><Input required maxLength={160} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title und Einstieg überarbeitet" /></Field>
              </div>
              <Field label="Notiz"><Textarea rows={3} maxLength={2000} value={details} onChange={(e) => setDetails(e.target.value)} /></Field>
              <Button type="submit" variant="primary" loading={addNote.isPending}>Änderung speichern</Button>
              {addNote.error && <ErrorBox error={addNote.error} />}
            </form>
          </Card>
          <Card title="Änderungsjournal" padded={false}>
            {!d.notes.length ? <EmptyState title="Noch keine Änderungen dokumentiert" /> : (
              <ol className="divide-y divide-slate-100 dark:divide-slate-800">
                {d.notes.map((n) => (
                  <li key={n.id} className="flex gap-3 px-4 py-3">
                    <time className="w-24 shrink-0 text-sm tabular-nums text-slate-500">{fmtDate(n.date)}</time>
                    <div className="min-w-0 flex-1">
                      <div className="font-medium">{n.title}</div>
                      {n.details && <p className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">{n.details}</p>}
                    </div>
                    <button type="button" aria-label="Eintrag löschen" className="text-slate-400 hover:text-red-600" onClick={() => delNote.mutate(n.id)}><Trash2 className="h-4 w-4" /></button>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
