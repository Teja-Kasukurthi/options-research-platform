import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${n >= 0 ? "+" : ""}${fmt(n)}%`;
}

export function fmtInr(n: number | null | undefined): string {
  if (n == null) return "—";
  return `₹${fmt(n, 0)}`;
}

export function pnlColor(n: number | null | undefined): string {
  if (n == null) return "text-foreground";
  return n >= 0 ? "text-green-400" : "text-red-400";
}
