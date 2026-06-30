"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getResearch, triggerResearch } from "@/lib/api";
import { useIvSurface } from "@/hooks/useAnalytics";
import { IVSurface } from "@/components/charts/IVSurface";
import { RefreshCw } from "lucide-react";
import type { ResearchEntry } from "@/lib/api";

const SENTIMENT_COLOR: Record<string, string> = {
  bullish: "text-green-400",
  bearish: "text-red-400",
  neutral: "text-blue-400",
  mixed: "text-yellow-400",
};

function ResearchCard({ entry }: { entry: ResearchEntry }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="font-semibold">{entry.underlying}</span>
        <span className={`text-xs font-medium capitalize ${SENTIMENT_COLOR[entry.sentiment] ?? "text-muted-foreground"}`}>
          {entry.sentiment}
        </span>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">{entry.summary}</p>
      {entry.key_levels && Object.keys(entry.key_levels).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(entry.key_levels).map(([k, v]) => (
            <span key={k} className="text-xs px-2 py-0.5 rounded border border-border bg-muted/20">
              {k}: <strong className="text-foreground">{v}</strong>
            </span>
          ))}
        </div>
      )}
      <p className="text-xs text-muted-foreground/60">
        {new Date(entry.created_at).toLocaleString("en-IN")}
      </p>
    </div>
  );
}

function IVPanel({ underlying }: { underlying: string }) {
  const { data, isLoading } = useIvSurface(underlying);
  if (isLoading || !data) return <div className="h-96 rounded-lg border border-border flex items-center justify-center text-muted-foreground text-sm">Loading IV surface…</div>;
  if (!data.strikes?.length) return <div className="h-40 rounded-lg border border-border flex items-center justify-center text-muted-foreground text-sm">No IV data</div>;
  return <IVSurface strikes={data.strikes} expiries={data.expiries} ivMatrix={data.iv_matrix} underlying={underlying} />;
}

export default function ResearchPage() {
  const [underlying, setUnderlying] = useState("NIFTY");
  const { data: entries, isLoading, refetch } = useQuery({
    queryKey: ["research", underlying],
    queryFn: () => getResearch(underlying),
    refetchInterval: 5 * 60_000,
  });

  const trigger = useMutation({
    mutationFn: () => triggerResearch(underlying),
    onSuccess: () => { void refetch(); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Research</h1>
        <div className="flex items-center gap-2">
          <select
            value={underlying}
            onChange={(e) => setUnderlying(e.target.value)}
            className="text-sm rounded-md border border-border bg-card px-3 py-1.5 text-foreground"
          >
            <option value="NIFTY">NIFTY</option>
            <option value="BANKNIFTY">BANKNIFTY</option>
            <option value="FINNIFTY">FINNIFTY</option>
          </select>
          <button
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border border-border bg-card hover:bg-muted/40 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={trigger.isPending ? "animate-spin" : ""} />
            Run Research
          </button>
        </div>
      </div>

      <IVPanel underlying={underlying} />

      <div>
        <h2 className="text-base font-semibold mb-3">AI Market View</h2>
        {isLoading && <div className="text-muted-foreground text-sm">Loading…</div>}
        {!isLoading && !entries?.length && (
          <div className="rounded-lg border border-border p-8 text-center text-muted-foreground text-sm">
            No research yet — click &quot;Run Research&quot; to generate
          </div>
        )}
        <div className="space-y-3">
          {entries?.map((e) => <ResearchCard key={e.id} entry={e} />)}
        </div>
      </div>
    </div>
  );
}
