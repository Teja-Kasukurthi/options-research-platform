"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { runBacktest, getBacktestHistory } from "@/lib/api";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { PayoffDiagram } from "@/components/charts/PayoffDiagram";
import { fmt, fmtInr, fmtPct, pnlColor, cn } from "@/lib/utils";
import type { BacktestResult } from "@/lib/api";
import { Play } from "lucide-react";

const STRATEGIES = [
  { value: "long_straddle", label: "Long Straddle" },
  { value: "bull_call_spread", label: "Bull Call Spread" },
  { value: "iron_condor", label: "Iron Condor" },
  { value: "protective_put", label: "Protective Put" },
];

function StatBox({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className={cn("text-lg font-bold tabular-nums", className)}>{value}</div>
    </div>
  );
}

function ResultPanel({ result }: { result: BacktestResult }) {
  const ret = result.final_capital - result.initial_capital;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBox label="Total Return" value={fmtPct(result.total_return_pct)} className={pnlColor(result.total_return_pct)} />
        <StatBox label="Sharpe" value={fmt(result.sharpe_ratio)} />
        <StatBox label="Max Drawdown" value={fmtPct(-result.max_drawdown_pct)} className="text-red-400" />
        <StatBox label="Win Rate" value={fmtPct(result.win_rate)} />
        <StatBox label="Final Capital" value={fmtInr(result.final_capital)} className={pnlColor(ret)} />
        <StatBox label="P&L" value={fmtInr(ret)} className={pnlColor(ret)} />
        <StatBox label="Trades" value={String(result.total_trades)} />
        <StatBox label="Sortino" value={fmt(result.sortino_ratio)} />
      </div>

      {result.equity_curve?.length > 0 && (
        <EquityCurve
          equity={result.equity_curve}
          initialCapital={result.initial_capital}
          fromDate={result.from_date}
          toDate={result.to_date}
        />
      )}
    </div>
  );
}

export default function BacktestPage() {
  const [strategy, setStrategy] = useState("long_straddle");
  const [fromDate, setFromDate] = useState("2024-01-01");
  const [toDate, setToDate] = useState("2024-12-31");
  const [capital, setCapital] = useState("500000");
  const [lotSize, setLotSize] = useState("75");
  const [selected, setSelected] = useState<BacktestResult | null>(null);

  const { data: history, refetch } = useQuery({
    queryKey: ["backtest-history"],
    queryFn: () => getBacktestHistory(20),
  });

  const run = useMutation({
    mutationFn: () => runBacktest({
      strategy_name: strategy,
      parameters: { lot_size: Number(lotSize) },
      from_date: fromDate,
      to_date: toDate,
      initial_capital: Number(capital),
    }),
    onSuccess: (result) => {
      setSelected(result);
      void refetch();
    },
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Backtest</h1>

      {/* Config form */}
      <div className="rounded-lg border border-border bg-card p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full text-sm rounded-md border border-border bg-background px-3 py-1.5"
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">From</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
              className="w-full text-sm rounded-md border border-border bg-background px-3 py-1.5" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">To</label>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
              className="w-full text-sm rounded-md border border-border bg-background px-3 py-1.5" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Capital (₹)</label>
            <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)}
              className="w-full text-sm rounded-md border border-border bg-background px-3 py-1.5" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Lot Size</label>
            <input type="number" value={lotSize} onChange={(e) => setLotSize(e.target.value)}
              className="w-full text-sm rounded-md border border-border bg-background px-3 py-1.5" />
          </div>
        </div>
        <button
          onClick={() => run.mutate()}
          disabled={run.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          <Play size={14} />
          {run.isPending ? "Running…" : "Run Backtest"}
        </button>
      </div>

      {/* Result */}
      {run.isError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
          Error: {String(run.error)}
        </div>
      )}
      {selected && <ResultPanel result={selected} />}

      {/* History */}
      {history && history.length > 0 && (
        <div>
          <h2 className="text-base font-semibold mb-3">History</h2>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-muted-foreground">
                  <th className="py-2 px-4 text-left">Strategy</th>
                  <th className="py-2 px-4 text-left">Period</th>
                  <th className="py-2 px-4 text-left">Return</th>
                  <th className="py-2 px-4 text-left">Sharpe</th>
                  <th className="py-2 px-4 text-left">MDD</th>
                  <th className="py-2 px-4 text-left">Trades</th>
                  <th className="py-2 px-4 text-left">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => setSelected(r)}
                    className={cn("border-b border-border/50 hover:bg-muted/20 cursor-pointer transition-colors", selected?.id === r.id && "bg-muted/30")}
                  >
                    <td className="py-2 px-4 font-medium">{r.strategy_name.replace(/_/g, " ")}</td>
                    <td className="py-2 px-4 text-xs text-muted-foreground">{r.from_date} → {r.to_date}</td>
                    <td className={cn("py-2 px-4 tabular-nums", pnlColor(r.total_return_pct))}>{fmtPct(r.total_return_pct)}</td>
                    <td className="py-2 px-4 tabular-nums">{fmt(r.sharpe_ratio)}</td>
                    <td className="py-2 px-4 tabular-nums text-red-400">{fmtPct(-r.max_drawdown_pct)}</td>
                    <td className="py-2 px-4 tabular-nums">{r.total_trades}</td>
                    <td className="py-2 px-4 text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString("en-IN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Payoff example for straddle */}
      {strategy === "long_straddle" && (
        <div>
          <h2 className="text-base font-semibold mb-3">Strategy Payoff (example: ATM=22500, premium=150 each)</h2>
          <PayoffDiagram
            underlying="NIFTY"
            spot={22500}
            legs={[
              { option_type: "CE", strike: 22500, premium: 150, quantity: 1, action: "BUY", lot_size: 75 },
              { option_type: "PE", strike: 22500, premium: 150, quantity: 1, action: "BUY", lot_size: 75 },
            ]}
          />
        </div>
      )}
    </div>
  );
}
