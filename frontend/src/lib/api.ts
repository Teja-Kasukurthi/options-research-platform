import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 30_000,
});

let _token: string | null = null;

export function setAuthToken(token: string | null) {
  _token = token;
}

api.interceptors.request.use((config) => {
  const stored = _token ?? (typeof window !== "undefined" ? localStorage.getItem("access_token") : null);
  if (stored) config.headers.Authorization = `Bearer ${stored}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const res = await axios.post(`${BASE}/api/auth/refresh`, { refresh_token: refresh });
          const { access_token } = res.data;
          localStorage.setItem("access_token", access_token);
          setAuthToken(access_token);
          err.config.headers.Authorization = `Bearer ${access_token}`;
          return api.request(err.config);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(err);
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/login", { email, password });
  return data as { access_token: string; refresh_token: string };
}

export async function logout() {
  await api.post("/auth/logout");
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// ─── Market ────────────────────────────────────────────────────────────────────

export async function getOptionsChain(underlying: string, expiry?: string) {
  const params = expiry ? { expiry } : {};
  const { data } = await api.get(`/market/chain/${underlying}`, { params });
  return data;
}

export async function getOHLCV(symbol: string, interval = "minute", from?: string, to?: string) {
  const { data } = await api.get(`/market/ohlcv/${symbol}`, { params: { interval, from, to } });
  return data as { time: number; open: number; high: number; low: number; close: number; volume: number }[];
}

export async function getFiiDii() {
  const { data } = await api.get("/market/fii-dii");
  return data;
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export async function getGreeks(underlying: string, expiry: string) {
  const { data } = await api.get(`/analytics/greeks/${underlying}`, { params: { expiry } });
  return data;
}

export async function getIvSurface(underlying: string) {
  const { data } = await api.get(`/analytics/iv-surface/${underlying}`);
  return data as {
    strikes: number[];
    expiries: string[];
    iv_matrix: number[][];
  };
}

export async function getOiAnalysis(underlying: string, expiry: string) {
  const { data } = await api.get(`/analytics/oi/${underlying}`, { params: { expiry } });
  return data;
}

// ─── Signals ──────────────────────────────────────────────────────────────────

export interface Signal {
  id: string;
  underlying: string;
  strategy_type: string;
  direction: string;
  status: string;
  confidence: number;
  score: number;
  entry_price: number | null;
  target_price: number | null;
  stop_loss: number | null;
  expiry: string;
  reasoning: string;
  created_at: string;
}

export async function getSignals(status?: string, limit = 20) {
  const { data } = await api.get("/signals/", { params: { status, limit } });
  return data as Signal[];
}

export async function approveSignal(id: string) {
  const { data } = await api.post(`/signals/${id}/approve`);
  return data;
}

export async function rejectSignal(id: string, reason?: string) {
  const { data } = await api.post(`/signals/${id}/reject`, { reason });
  return data;
}

export async function executeSignal(id: string) {
  const { data } = await api.post(`/signals/${id}/execute`);
  return data;
}

// ─── Positions ────────────────────────────────────────────────────────────────

export interface Position {
  id: string;
  symbol: string;
  underlying: string;
  option_type: string;
  strike: number;
  expiry: string;
  quantity: number;
  avg_price: number;
  ltp: number | null;
  pnl: number | null;
  delta: number | null;
  theta: number | null;
  gamma: number | null;
  vega: number | null;
  status: string;
  opened_at: string;
}

export async function getPositions(status = "open") {
  const { data } = await api.get("/positions/", { params: { status } });
  return data as Position[];
}

export async function closePosition(id: string) {
  const { data } = await api.post(`/positions/${id}/close`);
  return data;
}

export async function getPortfolioGreeks() {
  const { data } = await api.get("/positions/greeks");
  return data as { delta: number; theta: number; gamma: number; vega: number; total_pnl: number };
}

// ─── Research ─────────────────────────────────────────────────────────────────

export interface ResearchEntry {
  id: string;
  underlying: string;
  summary: string;
  sentiment: string;
  key_levels: Record<string, number>;
  created_at: string;
}

export async function getResearch(underlying?: string, limit = 10) {
  const { data } = await api.get("/research/", { params: { underlying, limit } });
  return data as ResearchEntry[];
}

export async function triggerResearch(underlying?: string) {
  const { data } = await api.post("/research/trigger", { underlying });
  return data;
}

// ─── Backtest ─────────────────────────────────────────────────────────────────

export interface BacktestResult {
  id: string;
  strategy_name: string;
  from_date: string;
  to_date: string;
  initial_capital: number;
  final_capital: number;
  total_return_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  win_rate: number;
  total_trades: number;
  equity_curve: number[];
  trades: unknown[];
  status: string;
  created_at: string;
}

export async function runBacktest(payload: {
  strategy_name: string;
  parameters: Record<string, unknown>;
  from_date: string;
  to_date: string;
  initial_capital?: number;
}) {
  const { data } = await api.post("/backtest/run", payload);
  return data as BacktestResult;
}

export async function getBacktestHistory(limit = 10) {
  const { data } = await api.get("/backtest/", { params: { limit } });
  return data as BacktestResult[];
}

export async function getBacktest(id: string) {
  const { data } = await api.get(`/backtest/${id}`);
  return data as BacktestResult;
}
