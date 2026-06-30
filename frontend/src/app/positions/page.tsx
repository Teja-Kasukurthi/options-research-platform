"use client";

import { useCallback } from "react";
import { usePositions, usePortfolioGreeks, useClosePosition } from "@/hooks/usePositions";
import { useOptionsChain } from "@/hooks/useAnalytics";
import { useMarketStore } from "@/stores/marketStore";
import { GreeksPanel } from "@/components/positions/GreeksPanel";
import { OptionsChainTable } from "@/components/options-chain/OptionsChainTable";
import { fmt, fmtInr, pnlColor, cn } from "@/lib/utils";
import { X } from "lucide-react";

function PositionRow({ pos, onClose }: { pos: ReturnType<typeof usePositions>["data"] extends (infer T)[] | undefined ? T : never; onClose: (id: string) => void }) {
  if (!pos) return null;
  return (
    <tr className="border-b border-border/50 hover:bg-muted/20 transition-colors">
      <td className="py-3 px-4 font-medium">{pos.symbol}</td>
      <td className="py-3 px-4 text-muted-foreground text-xs">{pos.expiry}</td>
      <td className="py-3 px-4 tabular-nums">{pos.quantity}</td>
      <td className="py-3 px-4 tabular-nums">{fmtInr(pos.avg_price)}</td>
      <td className="py-3 px-4 tabular-nums">{fmtInr(pos.ltp)}</td>
      <td className={cn("py-3 px-4 tabular-nums font-medium", pnlColor(pos.pnl))}>{fmtInr(pos.pnl)}</td>
      <td className="py-3 px-4 tabular-nums text-xs text-muted-foreground">
        Δ {fmt(pos.delta, 3)} θ {fmt(pos.theta, 2)}
      </td>
      <td className="py-3 px-4">
        <button
          onClick={() => onClose(pos.id)}
          className="p-1 rounded hover:bg-red-400/20 text-red-400 transition-colors"
          title="Close position"
        >
          <X size={14} />
        </button>
      </td>
    </tr>
  );
}

function ChainPanel() {
  const { data: chain, isLoading } = useOptionsChain("NIFTY");
  if (isLoading || !chain) return <div className="text-muted-foreground text-sm">Loading chain…</div>;
  const { strikes = [], spot_price = 0, atm_strike = 0 } = chain;
  return <OptionsChainTable strikes={strikes} atm={atm_strike} spot={spot_price} />;
}

export default function PositionsPage() {
  const { data: positions, isLoading } = usePositions();
  const { data: greeks } = usePortfolioGreeks();
  const pnl = useMarketStore((s) => s.pnl);
  const close = useClosePosition();

  const onClose = useCallback((id: string) => { if (confirm("Close position?")) close.mutate(id); }, [close]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Positions</h1>

      {greeks && <GreeksPanel greeks={greeks} livePnl={pnl?.total_pnl} />}

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground">
              <th className="py-3 px-4 text-left">Symbol</th>
              <th className="py-3 px-4 text-left">Expiry</th>
              <th className="py-3 px-4 text-left">Qty</th>
              <th className="py-3 px-4 text-left">Avg</th>
              <th className="py-3 px-4 text-left">LTP</th>
              <th className="py-3 px-4 text-left">P&L</th>
              <th className="py-3 px-4 text-left">Greeks</th>
              <th className="py-3 px-4" />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={8} className="py-6 text-center text-muted-foreground text-sm">Loading…</td></tr>
            )}
            {!isLoading && !positions?.length && (
              <tr><td colSpan={8} className="py-6 text-center text-muted-foreground text-sm">No open positions</td></tr>
            )}
            {positions?.map((pos) => (
              <PositionRow key={pos.id} pos={pos} onClose={onClose} />
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <h2 className="text-base font-semibold mb-3">NIFTY Options Chain</h2>
        <div className="rounded-lg border border-border overflow-hidden">
          <ChainPanel />
        </div>
      </div>
    </div>
  );
}
