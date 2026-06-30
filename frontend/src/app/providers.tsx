"use client";

import { useState, useCallback, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePnlSocket, useAlertsSocket, useSignalsSocket } from "@/hooks/useWebSocket";
import { useMarketStore } from "@/stores/marketStore";
import type { LivePnl, Alert } from "@/stores/marketStore";

function LiveDataSyncer() {
  const setPnl = useMarketStore((s) => s.setPnl);
  const addAlert = useMarketStore((s) => s.addAlert);
  const incrementSignalCount = useMarketStore((s) => s.incrementSignalCount);

  const onPnl = useCallback((data: unknown) => setPnl(data as LivePnl), [setPnl]);
  const onAlert = useCallback((data: unknown) => addAlert(data as Alert), [addAlert]);
  const onSignal = useCallback(() => incrementSignalCount(), [incrementSignalCount]);

  usePnlSocket(onPnl);
  useAlertsSocket(onAlert);
  useSignalsSocket(onSignal);

  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 2,
      },
    },
  }));

  return (
    <QueryClientProvider client={qc}>
      <LiveDataSyncer />
      {children}
    </QueryClientProvider>
  );
}
