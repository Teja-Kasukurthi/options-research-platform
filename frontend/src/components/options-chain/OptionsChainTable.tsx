"use client";

import { fmt, cn } from "@/lib/utils";

interface Strike {
  strike: number;
  ce?: { ltp: number; oi: number; iv: number; delta: number; bid: number; ask: number };
  pe?: { ltp: number; oi: number; iv: number; delta: number; bid: number; ask: number };
}

interface Props {
  strikes: Strike[];
  atm: number;
  spot: number;
}

function OiBar({ value, max }: { value: number; max: number }) {
  const pct = max ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function OptionsChainTable({ strikes, atm, spot }: Props) {
  const maxOi = Math.max(...strikes.flatMap((s) => [s.ce?.oi ?? 0, s.pe?.oi ?? 0]));

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-muted-foreground text-xs">
            <th className="py-2 px-3 text-right">OI</th>
            <th className="py-2 px-3 text-right">IV%</th>
            <th className="py-2 px-3 text-right">Δ</th>
            <th className="py-2 px-3 text-right">LTP</th>
            <th className="py-2 px-3 text-center bg-muted/20 font-semibold text-foreground">STRIKE</th>
            <th className="py-2 px-3 text-left">LTP</th>
            <th className="py-2 px-3 text-left">Δ</th>
            <th className="py-2 px-3 text-left">IV%</th>
            <th className="py-2 px-3 text-left">OI</th>
          </tr>
          <tr className="border-b border-border text-xs text-muted-foreground">
            <td colSpan={4} className="py-1 px-3 text-right text-green-400 font-medium">CALL</td>
            <td className="py-1 px-3 text-center text-xs">Spot: {fmt(spot)}</td>
            <td colSpan={4} className="py-1 px-3 text-left text-red-400 font-medium">PUT</td>
          </tr>
        </thead>
        <tbody>
          {strikes.map((s) => {
            const isAtm = s.strike === atm;
            const itm_ce = spot > s.strike;
            const itm_pe = spot < s.strike;
            return (
              <tr
                key={s.strike}
                className={cn(
                  "border-b border-border/50 hover:bg-muted/20 transition-colors",
                  isAtm && "ring-1 ring-yellow-500/40 bg-yellow-500/5"
                )}
              >
                {/* CALL side */}
                <td className={cn("py-2 px-3 text-right tabular-nums", itm_ce && "bg-green-500/5")}>
                  <div className="text-xs">{s.ce?.oi ? (s.ce.oi / 1000).toFixed(0) + "K" : "—"}</div>
                  <OiBar value={s.ce?.oi ?? 0} max={maxOi} />
                </td>
                <td className={cn("py-2 px-3 text-right tabular-nums text-xs", itm_ce && "bg-green-500/5")}>
                  {s.ce?.iv ? fmt(s.ce.iv * 100, 1) : "—"}
                </td>
                <td className={cn("py-2 px-3 text-right tabular-nums text-xs text-green-400", itm_ce && "bg-green-500/5")}>
                  {s.ce?.delta ? fmt(s.ce.delta, 3) : "—"}
                </td>
                <td className={cn("py-2 px-3 text-right tabular-nums font-medium", itm_ce && "bg-green-500/5")}>
                  {fmt(s.ce?.ltp)}
                </td>

                {/* Strike */}
                <td className={cn("py-2 px-3 text-center font-semibold tabular-nums bg-muted/20", isAtm && "text-yellow-400")}>
                  {s.strike}
                </td>

                {/* PUT side */}
                <td className={cn("py-2 px-3 text-left tabular-nums font-medium", itm_pe && "bg-red-500/5")}>
                  {fmt(s.pe?.ltp)}
                </td>
                <td className={cn("py-2 px-3 text-left tabular-nums text-xs text-red-400", itm_pe && "bg-red-500/5")}>
                  {s.pe?.delta ? fmt(s.pe.delta, 3) : "—"}
                </td>
                <td className={cn("py-2 px-3 text-left tabular-nums text-xs", itm_pe && "bg-red-500/5")}>
                  {s.pe?.iv ? fmt(s.pe.iv * 100, 1) : "—"}
                </td>
                <td className={cn("py-2 px-3 text-left tabular-nums", itm_pe && "bg-red-500/5")}>
                  <div className="text-xs">{s.pe?.oi ? (s.pe.oi / 1000).toFixed(0) + "K" : "—"}</div>
                  <OiBar value={s.pe?.oi ?? 0} max={maxOi} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
