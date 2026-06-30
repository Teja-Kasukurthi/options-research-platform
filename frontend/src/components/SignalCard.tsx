"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, CheckCircle, XCircle, Zap } from "lucide-react";
import { cn, fmt, fmtInr } from "@/lib/utils";
import type { Signal } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  approved: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  executed: "text-green-400 border-green-400/30 bg-green-400/10",
  rejected: "text-red-400 border-red-400/30 bg-red-400/10",
  expired: "text-muted-foreground border-border bg-muted/10",
};

interface Props {
  signal: Signal;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onExecute?: (id: string) => void;
}

export function SignalCard({ signal, onApprove, onReject, onExecute }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={cn("rounded-lg border p-4 transition-all", STATUS_COLORS[signal.status])}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold">{signal.underlying}</span>
            <span className="text-xs px-1.5 py-0.5 rounded border border-current">{signal.strategy_type.replace(/_/g, " ")}</span>
            <span className={cn("text-xs font-medium", signal.direction === "BULLISH" ? "text-green-400" : signal.direction === "BEARISH" ? "text-red-400" : "text-blue-400")}>
              {signal.direction}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span>Score: <strong className="text-foreground">{fmt(signal.score * 100, 0)}%</strong></span>
            <span>Confidence: <strong className="text-foreground">{fmt(signal.confidence * 100, 0)}%</strong></span>
            {signal.entry_price && <span>Entry: <strong className="text-foreground">{fmtInr(signal.entry_price)}</strong></span>}
            {signal.target_price && <span>Target: <strong className="text-green-400">{fmtInr(signal.target_price)}</strong></span>}
            {signal.stop_loss && <span>SL: <strong className="text-red-400">{fmtInr(signal.stop_loss)}</strong></span>}
            <span>Expiry: {signal.expiry}</span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {signal.status === "pending" && (
            <>
              {onApprove && (
                <button onClick={() => onApprove(signal.id)} className="p-1.5 rounded hover:bg-green-400/20 text-green-400 transition-colors" title="Approve">
                  <CheckCircle size={16} />
                </button>
              )}
              {onExecute && (
                <button onClick={() => onExecute(signal.id)} className="p-1.5 rounded hover:bg-blue-400/20 text-blue-400 transition-colors" title="Execute now">
                  <Zap size={16} />
                </button>
              )}
              {onReject && (
                <button onClick={() => onReject(signal.id)} className="p-1.5 rounded hover:bg-red-400/20 text-red-400 transition-colors" title="Reject">
                  <XCircle size={16} />
                </button>
              )}
            </>
          )}
          <button onClick={() => setExpanded(!expanded)} className="p-1.5 rounded hover:bg-muted/40 text-muted-foreground transition-colors">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-current/20">
          <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">{signal.reasoning}</p>
          <p className="mt-2 text-xs text-muted-foreground/60">
            {new Date(signal.created_at).toLocaleString("en-IN")}
          </p>
        </div>
      )}
    </div>
  );
}
