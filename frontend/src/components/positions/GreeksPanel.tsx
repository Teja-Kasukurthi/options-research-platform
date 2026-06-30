"use client";

import { fmt, fmtInr, pnlColor, cn } from "@/lib/utils";

interface Greeks {
  delta: number;
  theta: number;
  gamma: number;
  vega: number;
  total_pnl: number;
}

interface Props {
  greeks: Greeks;
  livePnl?: number | null;
}

function Metric({ label, value, unit = "", className = "" }: { label: string; value: string; unit?: string; className?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn("text-lg font-semibold tabular-nums", className)}>
        {value}
        {unit && <span className="text-xs text-muted-foreground ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export function GreeksPanel({ greeks, livePnl }: Props) {
  const pnl = livePnl ?? greeks.total_pnl;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-muted-foreground mb-3">Portfolio Greeks</h3>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Net Delta" value={fmt(greeks.delta, 2)} />
        <Metric label="Theta / day" value={fmtInr(greeks.theta)} className={greeks.theta >= 0 ? "text-green-400" : "text-red-400"} />
        <Metric label="Gamma" value={fmt(greeks.gamma, 4)} />
        <Metric label="Vega / 1%" value={fmtInr(greeks.vega)} />
      </div>
      <div className="mt-4 pt-4 border-t border-border">
        <Metric label="MTM P&L" value={fmtInr(pnl)} className={pnlColor(pnl)} />
      </div>
    </div>
  );
}
