"use client";

import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js-dist-min";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Leg {
  option_type: "CE" | "PE";
  strike: number;
  premium: number;
  quantity: number;
  action: "BUY" | "SELL";
  lot_size: number;
}

interface Props {
  legs: Leg[];
  spot: number;
  underlying: string;
}

function legPayoff(leg: Leg, price: number): number {
  const { option_type, strike, premium, quantity, action, lot_size } = leg;
  const intrinsic = option_type === "CE" ? Math.max(0, price - strike) : Math.max(0, strike - price);
  const pnl = (intrinsic - premium) * quantity * lot_size;
  return action === "BUY" ? pnl : -pnl;
}

export function PayoffDiagram({ legs, spot, underlying }: Props) {
  const low = spot * 0.85;
  const high = spot * 1.15;
  const step = (high - low) / 200;
  const prices = Array.from({ length: 201 }, (_, i) => low + i * step);
  const payoffs = prices.map((p) => legs.reduce((sum, leg) => sum + legPayoff(leg, p), 0));

  const trace: Data = {
    type: "scatter",
    x: prices,
    y: payoffs,
    mode: "lines",
    line: { color: "#60a5fa", width: 2 },
    name: "P&L at Expiry",
  };

  const breakevens = prices.filter((_, i) => {
    if (i === 0) return false;
    return (payoffs[i - 1] < 0) !== (payoffs[i] < 0);
  });

  const zeroLine: Data = {
    type: "scatter",
    x: [prices[0], prices[prices.length - 1]],
    y: [0, 0],
    mode: "lines",
    line: { color: "#52525b", width: 1, dash: "dash" },
    showlegend: false,
  };

  const spotLine: Data = {
    type: "scatter",
    x: [spot, spot],
    y: [Math.min(...payoffs), Math.max(...payoffs)],
    mode: "lines",
    line: { color: "#facc15", width: 1, dash: "dot" },
    name: "Spot",
  };

  const beTrace: Data = {
    type: "scatter",
    x: breakevens,
    y: breakevens.map(() => 0),
    mode: "markers",
    marker: { color: "#fb923c", size: 8 },
    name: "Breakeven",
  };

  const layout: Partial<Layout> = {
    title: { text: `${underlying} Payoff`, font: { color: "#a1a1aa" } },
    paper_bgcolor: "#09090b",
    plot_bgcolor: "#09090b",
    xaxis: { title: "Underlying Price", color: "#a1a1aa", gridcolor: "#27272a" },
    yaxis: { title: "P&L (₹)", color: "#a1a1aa", gridcolor: "#27272a" },
    legend: { font: { color: "#a1a1aa" } },
    margin: { l: 60, r: 20, b: 50, t: 40 },
  };

  return (
    <div className="w-full rounded-lg border border-border overflow-hidden">
      <Plot
        data={[zeroLine, spotLine, trace, beTrace]}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: 320 }}
      />
    </div>
  );
}
