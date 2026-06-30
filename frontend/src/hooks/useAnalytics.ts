import { useQuery } from "@tanstack/react-query";
import { getOptionsChain, getGreeks, getIvSurface, getOiAnalysis, getOHLCV } from "@/lib/api";

export function useOptionsChain(underlying: string, expiry?: string) {
  return useQuery({
    queryKey: ["options-chain", underlying, expiry],
    queryFn: () => getOptionsChain(underlying, expiry),
    refetchInterval: 30_000,
    enabled: !!underlying,
  });
}

export function useGreeks(underlying: string, expiry: string) {
  return useQuery({
    queryKey: ["greeks", underlying, expiry],
    queryFn: () => getGreeks(underlying, expiry),
    refetchInterval: 60_000,
    enabled: !!(underlying && expiry),
  });
}

export function useIvSurface(underlying: string) {
  return useQuery({
    queryKey: ["iv-surface", underlying],
    queryFn: () => getIvSurface(underlying),
    refetchInterval: 5 * 60_000,
    enabled: !!underlying,
  });
}

export function useOiAnalysis(underlying: string, expiry: string) {
  return useQuery({
    queryKey: ["oi-analysis", underlying, expiry],
    queryFn: () => getOiAnalysis(underlying, expiry),
    refetchInterval: 5 * 60_000,
    enabled: !!(underlying && expiry),
  });
}

export function useOHLCV(symbol: string, from?: string, to?: string) {
  return useQuery({
    queryKey: ["ohlcv", symbol, from, to],
    queryFn: () => getOHLCV(symbol, "minute", from, to),
    refetchInterval: 60_000,
    enabled: !!symbol,
  });
}
