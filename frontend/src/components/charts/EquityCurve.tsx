"use client";

import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js-dist-min";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  equity: number[];
  initialCapital: number;
  fromDate: string;
  toDate: string;
}

export function EquityCurve({ equity, initialCapital, fromDate, toDate }: Props) {
  const n = equity.length;
  const dates = Array.from({ length: n }, (_, i) => {
    const from = new Date(fromDate).getTime();
    const to = new Date(toDate).getTime();
    return new Date(from + ((to - from) / Math.max(n - 1, 1)) * i).toISOString().split("T")[0];
  });

  const pctCurve = equity.map((v) => ((v - initialCapital) / initialCapital) * 100);

  const trace: Data = {
    type: "scatter",
    x: dates,
    y: pctCurve,
    mode: "lines",
    fill: "tozeroy",
    fillcolor: "rgba(96,165,250,0.1)",
    line: { color: "#60a5fa", width: 2 },
    name: "Return %",
  };

  const zeroLine: Data = {
    type: "scatter",
    x: [dates[0], dates[dates.length - 1]],
    y: [0, 0],
    mode: "lines",
    line: { color: "#52525b", width: 1, dash: "dash" },
    showlegend: false,
  };

  const layout: Partial<Layout> = {
    paper_bgcolor: "#09090b",
    plot_bgcolor: "#09090b",
    xaxis: { color: "#a1a1aa", gridcolor: "#27272a" },
    yaxis: { title: "Return %", color: "#a1a1aa", gridcolor: "#27272a" },
    legend: { font: { color: "#a1a1aa" } },
    margin: { l: 60, r: 20, b: 50, t: 20 },
  };

  return (
    <div className="w-full rounded-lg border border-border overflow-hidden">
      <Plot
        data={[zeroLine, trace]}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: 300 }}
      />
    </div>
  );
}
