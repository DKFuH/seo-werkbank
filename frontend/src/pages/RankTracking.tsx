import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, PageHeader, Select, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useSite } from "../lib/context";

type Observation = { id: number; observed_at: string; provider: string; position: number | null;
  search_depth: number; serp_features: string[]; result_url: string | null };
type Target = { id: number; keyword: string; engine: string; country: string; device: string; landing_url: string | null;
  position_delta: number | null; history: Observation[] };
type Result = { items: Target[]; method: string };

export default function RankTracking() {
  const { site } = useSite();
  const qc = useQueryClient();
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("de");
  const [language, setLanguage] = useState("de");
  const [device, setDevice] = useState("desktop");
  const [landingUrl, setLandingUrl] = useState("");
  const [position, setPosition] = useState<Record<number, string>>({});
  const path = "/sites/" + site?.id + "/rank-targets";
  const key = ["rank-targets", site?.id];
  const q = useQuery<Result>({ queryKey: key, queryFn: () => api.get(path), enabled: !!site });
  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  const add = useMutation({ mutationFn: () => api.post(path, { keyword, country, language, device,
    landing_url: landingUrl.trim() || null }), onSuccess: () => { setKeyword(""); refresh(); } });
  const sample = useMutation({ mutationFn: (targetId: number) => api.post(path + "/" + targetId + "/observations",
    { provider: "manual", position: position[targetId] ? Number(position[targetId]) : null, search_depth: 100 }),
    onSuccess: refresh });
  const capture = useMutation({ mutationFn: (targetId: number) => api.post(path + "/" + targetId + "/capture", {}),
    onSuccess: refresh });
  const remove = useMutation({ mutationFn: (targetId: number) => api.del(path + "/" + targetId),
    onSuccess: refresh });
  return <div className="space-y-4">
    <PageHeader title="Keyword-Ranktracker" description="Ausgewählte Keywords und historisierte Positionsbeobachtungen mit eindeutiger Datenquelle." />
    <Card title="Neues Zielkeyword">
      <form className="grid gap-3 md:grid-cols-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Keyword"><Input required maxLength={500} value={keyword} onChange={(e) => setKeyword(e.target.value)} /></Field>
        <Field label="Land (ISO 2)"><Input required maxLength={2} value={country} onChange={(e) => setCountry(e.target.value.toLowerCase())} /></Field>
        <Field label="Sprache (ISO 2)"><Input required maxLength={2} value={language} onChange={(e) => setLanguage(e.target.value.toLowerCase())} /></Field>
        <Field label="Gerät"><Select value={device} onChange={(e) => setDevice(e.target.value)}>
          <option value="desktop">Desktop</option><option value="mobile">Mobil (nur manuell)</option>
        </Select></Field>
        <Field label="Gewünschte Zielseite"><Input type="url" value={landingUrl} onChange={(e) => setLandingUrl(e.target.value)} /></Field>
        <div className="flex items-end"><Button variant="primary" type="submit" loading={add.isPending} disabled={!site}>Keyword hinzufügen</Button></div>
      </form>
      {add.error && <ErrorBox error={add.error} />}
      <p className="mt-3 text-xs text-slate-500">Anbieterabfragen sind Momentaufnahmen der jeweiligen Such-API; sie ersetzen keine unabhängigen Google-Rankings.
        Mobile und Stadtpositionen dürfen nur als manuelle Beobachtungen gespeichert werden.</p>
    </Card>
    {!site && <Card><EmptyState title="Website auswählen" /></Card>}
    {q.isLoading && <Card><Spinner /></Card>}
    {q.error && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
    {q.data?.items.length === 0 && <Card><EmptyState title="Noch keine Zielkeywords" /></Card>}
    {q.data?.items.map((t) => {
      const last = t.history[t.history.length - 1];
      return <Card key={t.id} title={t.keyword} description={t.country.toUpperCase() + " · " + t.device}
        actions={<Button size="sm" variant="ghost" disabled={remove.isPending}
          onClick={() => { if (window.confirm("Zielkeyword und Verlauf löschen?")) remove.mutate(t.id); }}>Löschen</Button>}>
        <div className="flex flex-wrap items-center gap-3">
          <Badge>{last ? "Position " + (last.position ?? "> " + last.search_depth) : "Keine Messung"}</Badge>
          {t.position_delta !== null && <Badge>{t.position_delta > 0 ? "+" : ""}{t.position_delta} Plätze (gleicher Anbieter)</Badge>}
          <Input className="max-w-28" type="number" min={1} max={100} placeholder="Position" aria-label={"Position für " + t.keyword}
            value={position[t.id] ?? ""} onChange={(e) => setPosition((prev) => ({ ...prev, [t.id]: e.target.value }))} />
          <Button size="sm" disabled={!position[t.id] || sample.isPending} onClick={() => sample.mutate(t.id)}>Manuell speichern</Button>
          <Button size="sm" disabled={capture.isPending || t.device !== "desktop"} onClick={() => capture.mutate(t.id)}>SERP-Anbieter abfragen</Button>
        </div>
        <div className="mt-2 space-y-1">
          {t.history.slice(-8).reverse().map((o) => <p key={o.id} className="text-xs text-slate-500">
            {o.observed_at.slice(0, 16)} · {o.provider} · {o.position ?? "nicht gefunden"}
            {o.serp_features.length > 0 ? " · " + o.serp_features.join(", ") : ""}
          </p>)}
        </div>
      </Card>;
    })}
    {sample.error && <ErrorBox error={sample.error} />}
    {capture.error && <ErrorBox error={capture.error} />}
    {remove.error && <ErrorBox error={remove.error} />}
  </div>;
}
