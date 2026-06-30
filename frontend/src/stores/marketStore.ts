import { create } from "zustand";

export interface Tick {
  symbol: string;
  ltp: number;
  bid: number;
  ask: number;
  volume: number;
  oi: number;
  timestamp: string;
}

export interface LivePnl {
  total_pnl: number;
  total_pnl_pct: number;
  positions: Record<string, number>;
  updated_at: string;
}

export interface Alert {
  id: string;
  type: "stop_loss" | "target" | "expiry";
  message: string;
  trade_id: string;
  timestamp: string;
}

interface MarketState {
  ticks: Record<string, Tick>;
  pnl: LivePnl | null;
  alerts: Alert[];
  newSignalCount: number;
  setTick: (tick: Tick) => void;
  setPnl: (pnl: LivePnl) => void;
  addAlert: (alert: Alert) => void;
  dismissAlert: (id: string) => void;
  incrementSignalCount: () => void;
  resetSignalCount: () => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  ticks: {},
  pnl: null,
  alerts: [],
  newSignalCount: 0,

  setTick: (tick) =>
    set((s) => ({ ticks: { ...s.ticks, [tick.symbol]: tick } })),

  setPnl: (pnl) => set({ pnl }),

  addAlert: (alert) =>
    set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 20) })),

  dismissAlert: (id) =>
    set((s) => ({ alerts: s.alerts.filter((a) => a.id !== id) })),

  incrementSignalCount: () =>
    set((s) => ({ newSignalCount: s.newSignalCount + 1 })),

  resetSignalCount: () => set({ newSignalCount: 0 }),
}));
