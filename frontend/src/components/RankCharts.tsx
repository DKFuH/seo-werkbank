/* Position over time from Search Console. One series; the y axis is reversed because a smaller position is better.
   Journal entries are drawn as vertical markers with their title in the tooltip. */
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtDate, fmtInt } from "../lib/format";
import { chartColors, EmptyState } from "./ui";

export type TrendPoint = { date: string; position: number | null; impressions: number; clicks: number };
export type Note = { id: number; date: string; title: string };

const axisTick = { fontSize: 11, fill: "#94a3b8" };

export function PositionChart({ points, notes = [], granularity }: { points: TrendPoint[]; notes?: Note[]; granularity: "day" | "week" }) {
  const valid = points.filter((p) => p.position !== null);
  if (valid.length < 2) {
    return <EmptyState title="Noch keine belastbare Zeitreihe" description="Für die Kurve werden mindestens zwei Messpunkte aus der Search Console gebraucht." />;
  }
  const positions = valid.map((p) => p.position as number);
  const lo = Math.max(1, Math.floor(Math.min(...positions)) - 1);
  const hi = Math.ceil(Math.max(...positions)) + 1;
  const data = points.map((p) => ({ ...p, label: fmtDate(p.date) }));
  const inRange = notes.filter((n) => n.date >= points[0].date && n.date <= points[points.length - 1].date);
  // A note belongs to the point on or before its date (weekly points start on Monday).
  const noteAt = (d: string) => [...data].reverse().find((p) => p.date <= d)?.label;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: -8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" vertical={false} />
        <XAxis dataKey="label" tick={axisTick} minTickGap={28} />
        <YAxis reversed domain={[lo, hi]} allowDecimals={false} tick={axisTick} tickFormatter={(v) => `#${v}`} width={44} />
        <Tooltip contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8, color: "#f1f5f9", fontSize: 12 }}
          formatter={(value: number, name: string) => name === "position" ? [`#${value.toLocaleString("de-DE")}`, "Ø Position"] : [fmtInt(value), name]}
          labelFormatter={(l) => (granularity === "week" ? `Woche ab ${l}` : l)} />
        {inRange.map((n) => (
          <ReferenceLine key={n.id} x={noteAt(n.date)} stroke="#f59e0b" strokeDasharray="4 3"
            label={{ value: "●", position: "top", fill: "#f59e0b", fontSize: 10 }} />
        ))}
        <Line type="monotone" dataKey="position" name="position" stroke={chartColors[0]} strokeWidth={2} dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** "▲ 2,3" for improvements (position number went down), "▼ 1,0" for losses. */
export function Movement({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-slate-400">—</span>;
  if (Math.abs(value) < 0.05) return <span className="text-slate-500">±0,0</span>;
  const up = value > 0;
  return (
    <span className={up ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}>
      {up ? "▲" : "▼"} {Math.abs(value).toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
    </span>
  );
}

export const fmtPos = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : v.toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
