"use client";

import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js-dist-min";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  strikes: number[];
  expiries: string[];
  ivMatrix: number[][];
  underlying: string;
}

export function IVSurface({ strikes, expiries, ivMatrix, underlying }: Props) {
  const trace: Data = {
    type: "surface",
    x: expiries,
    y: strikes,
    z: ivMatrix,
    colorscale: "Viridis",
    showscale: true,
    colorbar: { title: "IV %" },
  } as Data;

  const layout: Partial<Layout> = {
    title: { text: `${underlying} IV Surface`, font: { color: "#a1a1aa" } },
    paper_bgcolor: "#09090b",
    plot_bgcolor: "#09090b",
    scene: {
      xaxis: { title: "Expiry", color: "#a1a1aa", gridcolor: "#27272a" },
      yaxis: { title: "Strike", color: "#a1a1aa", gridcolor: "#27272a" },
      zaxis: { title: "IV %", color: "#a1a1aa", gridcolor: "#27272a" },
      bgcolor: "#09090b",
    },
    font: { color: "#a1a1aa" },
    margin: { l: 0, r: 0, b: 0, t: 40 },
  };

  return (
    <div className="w-full rounded-lg border border-border overflow-hidden">
      <Plot
        data={[trace]}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: 400 }}
      />
    </div>
  );
}
