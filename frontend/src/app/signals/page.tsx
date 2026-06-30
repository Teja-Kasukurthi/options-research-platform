"use client";

import { useState, useCallback } from "react";
import { useSignals, useApproveSignal, useRejectSignal, useExecuteSignal } from "@/hooks/useSignals";
import { useSignalsSocket } from "@/hooks/useWebSocket";
import { useMarketStore } from "@/stores/marketStore";
import { SignalCard } from "@/components/SignalCard";

const TABS = ["pending", "approved", "executed", "rejected"] as const;
type Tab = typeof TABS[number];

export default function SignalsPage() {
  const [tab, setTab] = useState<Tab>("pending");
  const resetSignalCount = useMarketStore((s) => s.resetSignalCount);
  const { data: signals, isLoading, refetch } = useSignals(tab);
  const approve = useApproveSignal();
  const reject = useRejectSignal();
  const execute = useExecuteSignal();

  const onNewSignal = useCallback(() => { void refetch(); }, [refetch]);
  useSignalsSocket(onNewSignal);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Signals</h1>

      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); if (t === "pending") resetSignalCount(); }}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {isLoading && <div className="text-muted-foreground text-sm">Loading…</div>}

      {!isLoading && !signals?.length && (
        <div className="rounded-lg border border-border p-8 text-center text-muted-foreground text-sm">
          No {tab} signals
        </div>
      )}

      <div className="space-y-3">
        {signals?.map((sig) => (
          <SignalCard
            key={sig.id}
            signal={sig}
            onApprove={tab === "pending" ? (id) => approve.mutate(id) : undefined}
            onReject={tab === "pending" ? (id) => reject.mutate({ id }) : undefined}
            onExecute={tab === "pending" ? (id) => execute.mutate(id) : undefined}
          />
        ))}
      </div>
    </div>
  );
}
