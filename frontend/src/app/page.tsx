"use client";

import { useCallback } from "react";
import { useMarketStore } from "@/stores/marketStore";
import { usePortfolioGreeks } from "@/hooks/usePositions";
import { useOHLCV } from "@/hooks/useAnalytics";
import { useTickSocket } from "@/hooks/useWebSocket";
import { GreeksPanel } from "@/components/positions/GreeksPanel";
import { PriceChart } from "@/components/charts/PriceChart";
import { fmt, fmtInr, pnlColor, cn } from "@/lib/utils";
import type { Tick } from "@/stores/marketStore";

const WATCHLIST = ["NIFTY", "BANKNIFTY"];

function TickerCard({ symbol }: { symbol: string }) {
  const ticks = useMarketStore((s) => s.ticks);
  const setTick = useMarketStore((s) => s.setTick);
  const tick = ticks[symbol];

  const onMsg = useCallback(
    (data: unknown) => setTick(data as Tick),
    [setTick]
  );
  useTickSocket(symbol, onMsg);

  const change = tick ? tick.ltp - (tick.bid + tick.ask) / 2 : null;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between">
        <span className="font-semibold text-sm">{symbol}</span>
        <span className={cn("text-xs", pnlColor(change))}>
          {change != null ? (change >= 0 ? "▲" : "▼") + " " + fmt(Math.abs(change)) : "—"}
        </span>
      </div>
      <div className="mt-2 text-2xl font-bold tabular-nums">
        {tick ? fmtInr(tick.ltp) : <span className="text-muted-foreground text-base">Loading…</span>}
      </div>
      {tick && (
        <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
          <span>Bid {fmt(tick.bid)}</span>
          <span>Ask {fmt(tick.ask)}</span>
          <span>OI {(tick.oi / 1000).toFixed(0)}K</span>
        </div>
      )}
    </div>
  );
}

function NiftyChart() {
  const { data, isLoading } = useOHLCV("NIFTY");
  if (isLoading || !data) return <div className="h-80 rounded-lg border border-border flex items-center justify-center text-muted-foreground text-sm">Loading chart…</div>;
  return <PriceChart data={data} symbol="NIFTY 50" />;
}

export default function HomePage() {
  const pnl = useMarketStore((s) => s.pnl);
  const alerts = useMarketStore((s) => s.alerts);
  const dismissAlert = useMarketStore((s) => s.dismissAlert);
  const { data: greeks } = usePortfolioGreeks();

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Market Overview</h1>

      {/* Live alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.slice(0, 3).map((alert) => (
            <div key={alert.id} className="flex items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
              <span>{alert.message}</span>
              <button onClick={() => dismissAlert(alert.id)} className="ml-4 text-xs opacity-60 hover:opacity-100">✕</button>
            </div>
          ))}
        </div>
      )}

      {/* Tickers */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {WATCHLIST.map((sym) => <TickerCard key={sym} symbol={sym} />)}
        {/* Summary cards */}
        <div className="rounded-lg border border-border bg-card p-4">
          <span className="text-xs text-muted-foreground">MTM P&L</span>
          <div className={cn("mt-2 text-2xl font-bold tabular-nums", pnlColor(pnl?.total_pnl))}>
            {pnl ? fmtInr(pnl.total_pnl) : "—"}
          </div>
          {pnl && <div className={cn("text-xs mt-1", pnlColor(pnl.total_pnl_pct))}>{pnl.total_pnl_pct >= 0 ? "+" : ""}{fmt(pnl.total_pnl_pct)}%</div>}
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <span className="text-xs text-muted-foreground">Net Delta</span>
          <div className="mt-2 text-2xl font-bold tabular-nums">{greeks ? fmt(greeks.delta) : "—"}</div>
          {greeks && <div className="text-xs mt-1 text-muted-foreground">θ {fmtInr(greeks.theta)}/day</div>}
        </div>
      </div>

      {/* Chart */}
      <NiftyChart />

      {/* Greeks panel */}
      {greeks && <GreeksPanel greeks={greeks} livePnl={pnl?.total_pnl} />}
    </div>
  );
}
