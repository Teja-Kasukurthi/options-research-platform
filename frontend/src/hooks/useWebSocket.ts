"use client";

import { useEffect } from "react";
import { getWebSocket, closeWebSocket } from "@/lib/websocket";

export function useWebSocket(path: string, onMessage: (data: unknown) => void) {
  useEffect(() => {
    const ws = getWebSocket(path);
    const unsub = ws.subscribe(onMessage);
    return () => {
      unsub();
    };
  }, [path, onMessage]);
}

export function usePnlSocket(onMessage: (data: unknown) => void) {
  useWebSocket("/ws/paper/pnl", onMessage);
}

export function useAlertsSocket(onMessage: (data: unknown) => void) {
  useWebSocket("/ws/positions/alerts", onMessage);
}

export function useSignalsSocket(onMessage: (data: unknown) => void) {
  useWebSocket("/ws/signals/new", onMessage);
}

export function useTickSocket(symbol: string, onMessage: (data: unknown) => void) {
  useWebSocket(`/ws/market/ticks/${symbol}`, onMessage);
}
