import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPositions, closePosition, getPortfolioGreeks } from "@/lib/api";

export function usePositions(status = "open") {
  return useQuery({
    queryKey: ["positions", status],
    queryFn: () => getPositions(status),
    refetchInterval: 60_000,
  });
}

export function usePortfolioGreeks() {
  return useQuery({
    queryKey: ["portfolio-greeks"],
    queryFn: getPortfolioGreeks,
    refetchInterval: 60_000,
  });
}

export function useClosePosition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: closePosition,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["positions"] }),
  });
}
