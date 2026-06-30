"use client";

import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData } from "lightweight-charts";

interface Bar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  data: Bar[];
  symbol: string;
  height?: number;
}

export function PriceChart({ data, symbol, height = 320 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: "#09090b" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      crosshair: { mode: 1 },
      timeScale: {
        borderColor: "#27272a",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: { borderColor: "#27272a" },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#4ade80",
      downColor: "#f87171",
      borderUpColor: "#4ade80",
      borderDownColor: "#f87171",
      wickUpColor: "#4ade80",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [height]);

  useEffect(() => {
    if (!seriesRef.current || !data.length) return;
    const sorted = [...data].sort((a, b) => a.time - b.time);
    seriesRef.current.setData(sorted as CandlestickData[]);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return (
    <div className="w-full rounded-lg overflow-hidden border border-border">
      <div className="px-4 py-2 text-sm font-medium text-muted-foreground">{symbol}</div>
      <div ref={containerRef} style={{ height }} />
    </div>
  );
}
