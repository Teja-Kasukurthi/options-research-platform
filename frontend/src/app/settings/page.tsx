"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Save } from "lucide-react";

interface Settings {
  watchlist: string[];
  max_positions: number;
  max_capital_pct_per_trade: number;
  sector_concentration_pct: number;
  max_delta: number;
  stop_loss_required: boolean;
  min_rr_ratio: number;
  min_days_to_expiry: number;
  max_bid_ask_spread_pct: number;
  kelly_fraction: number;
  telegram_alerts: boolean;
  email_alerts: boolean;
}

const DEFAULT: Settings = {
  watchlist: ["NIFTY", "BANKNIFTY"],
  max_positions: 5,
  max_capital_pct_per_trade: 2,
  sector_concentration_pct: 40,
  max_delta: 50000,
  stop_loss_required: true,
  min_rr_ratio: 1.5,
  min_days_to_expiry: 7,
  max_bid_ask_spread_pct: 2,
  kelly_fraction: 0.25,
  telegram_alerts: true,
  email_alerts: false,
};

function Field({ label, help, children }: { label: string; help?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-border/50 last:border-0">
      <div className="flex-1">
        <div className="text-sm font-medium">{label}</div>
        {help && <div className="text-xs text-muted-foreground mt-0.5">{help}</div>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data: saved } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      try { const { data } = await api.get("/settings/"); return data as Settings; }
      catch { return DEFAULT; }
    },
  });

  const [form, setForm] = useState<Settings>(saved ?? DEFAULT);

  const save = useMutation({
    mutationFn: () => api.post("/settings/", form),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  const set = <K extends keyof Settings>(k: K, v: Settings[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const watchlistStr = form.watchlist.join(", ");

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Settings</h1>
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          <Save size={14} />
          {save.isPending ? "Saving…" : "Save"}
        </button>
      </div>

      {save.isSuccess && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-2 text-sm text-green-400">
          Settings saved
        </div>
      )}

      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-muted-foreground mb-2">Watchlist</h2>
        <Field label="Underlyings" help="Comma-separated list of underlyings to track">
          <input
            className="w-48 text-sm rounded border border-border bg-background px-3 py-1.5"
            value={watchlistStr}
            onChange={(e) => set("watchlist", e.target.value.split(",").map((s) => s.trim().toUpperCase()))}
          />
        </Field>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-muted-foreground mb-2">Risk Gates</h2>
        <Field label="Max open positions" help="Layer 1: hard limit on concurrent trades">
          <input type="number" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.max_positions} onChange={(e) => set("max_positions", Number(e.target.value))} />
        </Field>
        <Field label="Capital per trade (%)" help="Layer 2: max % of capital per single trade">
          <input type="number" step="0.5" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.max_capital_pct_per_trade} onChange={(e) => set("max_capital_pct_per_trade", Number(e.target.value))} />
        </Field>
        <Field label="Sector concentration (%)" help="Layer 1: max % in one underlying">
          <input type="number" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.sector_concentration_pct} onChange={(e) => set("sector_concentration_pct", Number(e.target.value))} />
        </Field>
        <Field label="Net delta limit (₹)" help="Layer 1: max portfolio delta in rupees">
          <input type="number" step="1000" className="w-28 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.max_delta} onChange={(e) => set("max_delta", Number(e.target.value))} />
        </Field>
        <Field label="Min R:R ratio" help="Layer 3: minimum reward:risk ratio required">
          <input type="number" step="0.1" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.min_rr_ratio} onChange={(e) => set("min_rr_ratio", Number(e.target.value))} />
        </Field>
        <Field label="Min days to expiry" help="Layer 3: don't trade options expiring within N days">
          <input type="number" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.min_days_to_expiry} onChange={(e) => set("min_days_to_expiry", Number(e.target.value))} />
        </Field>
        <Field label="Max bid-ask spread (%)" help="Layer 3: reject illiquid options above this spread">
          <input type="number" step="0.1" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.max_bid_ask_spread_pct} onChange={(e) => set("max_bid_ask_spread_pct", Number(e.target.value))} />
        </Field>
        <Field label="Stop-loss required" help="Layer 3: reject any trade without a stop-loss">
          <input type="checkbox" checked={form.stop_loss_required} onChange={(e) => set("stop_loss_required", e.target.checked)} className="w-4 h-4" />
        </Field>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-muted-foreground mb-2">Position Sizing</h2>
        <Field label="Kelly fraction" help="Fractional Kelly multiplier (0.25 = quarter-Kelly)">
          <input type="number" step="0.05" min="0.1" max="1" className="w-24 text-sm rounded border border-border bg-background px-3 py-1.5" value={form.kelly_fraction} onChange={(e) => set("kelly_fraction", Number(e.target.value))} />
        </Field>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-muted-foreground mb-2">Notifications</h2>
        <Field label="Telegram alerts">
          <input type="checkbox" checked={form.telegram_alerts} onChange={(e) => set("telegram_alerts", e.target.checked)} className="w-4 h-4" />
        </Field>
        <Field label="Email alerts">
          <input type="checkbox" checked={form.email_alerts} onChange={(e) => set("email_alerts", e.target.checked)} className="w-4 h-4" />
        </Field>
      </div>
    </div>
  );
}
