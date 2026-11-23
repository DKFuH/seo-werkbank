/* Website Health charts: status strip (one bar per time bucket) and response-time candles.
   One series, one hue for the candles: a higher response time is always worse, so there is no up/down colouring.
   Status colours (up / slow / down) are reserved and always shown with a legend and a tooltip text. */
import { useState } from "react";
import { fmtDateTime, fmtInt } from "../lib/format";

export type Bar = { start: string; status: "up" | "slow" | "down" | "none"; checks: number; down: number };
export type Candle = { start: string; open: number | null; close: number | null; high: number | null; low: number | null; avg: number | null; down: number };

const STATUS: Record<Bar["status"], { cls: string; label: string }> = {
  up: { cls: "bg-emerald-400 dark:bg-emerald-500", label: "erreichbar" },
  slow: { cls: "bg-amber-400 dark:bg-amber-500", label: "hohe Antwortzeit" },
  down: { cls: "bg-red-500 dark:bg-red-500", label: "Ausfall" },
  none: { cls: "bg-slate-200 dark:bg-slate-700", label: "keine Prüfung" },
};

export function StatusStrip({ bars }: { bars: Bar[] }) {
  return (
    <div>
      <div className="flex h-10 items-stretch gap-[2px]" role="img" aria-label="Status je Zeitabschnitt">
        {bars.map((b) => (
          <div key={b.start} className={`min-w-[2px] flex-1 rounded-[3px] ${STATUS[b.status].cls}`}
            title={`${fmtDateTime(b.start)}: ${STATUS[b.status].label}${b.checks ? ` · ${b.checks} Prüfung(en)${b.down ? `, ${b.down} mit Fehler` : ""}` : ""}`} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        {(Object.keys(STATUS) as Bar["status"][]).map((k) => (
          <span key={k} className="inline-flex items-center gap-1.5"><span className={`h-2.5 w-2.5 rounded-sm ${STATUS[k].cls}`} />{STATUS[k].label}</span>
        ))}
      </div>
    </div>
  );
}

const W = 1000;
const H = 280;
const PAD = { top: 12, right: 12, bottom: 28, left: 52 };

function niceMax(v: number): number {
  const steps = [250, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000, 15000, 20000, 30000];
  return steps.find((s) => s >= v) ?? Math.ceil(v / 10000) * 10000;
}

/** Response-time candles per bucket: open/close = first/last check, wick = low..high. Threshold as dashed line,
    buckets with an outage get a small red marker on the baseline. Hover shows the bucket's values. */
export function CandleChart({ candles, threshold }: { candles: Candle[]; threshold: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const filled = candles.filter((c) => c.high !== null);
  const max = niceMax(Math.max(threshold * 1.15, ...filled.map((c) => c.high as number)));
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const slot = plotW / Math.max(1, candles.length);
  const body = Math.max(2, Math.min(14, slot * 0.6));
  const y = (v: number) => PAD.top + plotH - (v / max) * plotH;
  const ticks = [0, max / 4, max / 2, (3 * max) / 4, max];
  const labelEvery = Math.max(1, Math.ceil(candles.length / 6));
  const h = hover !== null ? candles[hover] : null;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Antwortzeit je Zeitabschnitt als Kerzendiagramm">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="stroke-slate-200 dark:stroke-slate-800" strokeWidth={1} />
            <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" className="fill-slate-400 text-[11px]">{fmtInt(t)}</text>
          </g>
        ))}
        <line x1={PAD.left} x2={W - PAD.right} y1={y(threshold)} y2={y(threshold)} className="stroke-amber-500" strokeWidth={1.5} strokeDasharray="6 4" />
        <text x={W - PAD.right} y={y(threshold) - 5} textAnchor="end" className="fill-amber-600 text-[11px] dark:fill-amber-400">Grenzwert {fmtInt(threshold)} ms</text>
        {candles.map((c, i) => {
          const cx = PAD.left + slot * i + slot / 2;
          const active = hover === i;
          return (
            <g key={c.start}>
              {c.high !== null && c.low !== null && c.open !== null && c.close !== null && (
                <>
                  <line x1={cx} x2={cx} y1={y(c.high)} y2={y(c.low)} className="stroke-brand-600 dark:stroke-brand-400" strokeWidth={1.5} />
                  <rect x={cx - body / 2} width={body} y={y(Math.max(c.open, c.close))}
                    height={Math.max(2, Math.abs(y(c.open) - y(c.close)))} rx={2}
                    className={active ? "fill-brand-700 dark:fill-brand-300" : "fill-brand-500 dark:fill-brand-400"} />
                </>
              )}
              {c.down > 0 && <rect x={cx - body / 2} width={body} y={PAD.top + plotH - 4} height={4} rx={1} className="fill-red-500" />}
              {i % labelEvery === 0 && (
                <text x={cx} y={H - 8} textAnchor="middle" className="fill-slate-400 text-[11px]">
                  {new Date(c.start + (c.start.endsWith("Z") ? "" : "Z")).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                </text>
              )}
              <rect x={PAD.left + slot * i} width={slot} y={PAD.top} height={plotH} fill="transparent"
                onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} />
            </g>
          );
        })}
      </svg>
      {h && (
        <div className="pointer-events-none absolute top-2 rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-100 shadow-lg"
          style={{ left: `${Math.min(80, Math.max(2, ((PAD.left + slot * (hover as number)) / W) * 100))}%` }}>
          <div className="font-medium">{fmtDateTime(h.start)}</div>
          {h.high === null ? <div>keine erfolgreiche Prüfung</div> : (
            <div className="tabular-nums">Erste {fmtInt(h.open)} · Letzte {fmtInt(h.close)} ms<br />Min {fmtInt(h.low)} · Max {fmtInt(h.high)} · Ø {fmtInt(h.avg)} ms</div>
          )}
          {h.down > 0 && <div className="text-red-300">{h.down} Prüfung(en) mit Fehler</div>}
        </div>
      )}
    </div>
  );
}
