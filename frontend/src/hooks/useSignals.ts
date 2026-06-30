import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSignals, approveSignal, rejectSignal, executeSignal } from "@/lib/api";

export function useSignals(status?: string) {
  return useQuery({
    queryKey: ["signals", status],
    queryFn: () => getSignals(status),
    refetchInterval: 30_000,
  });
}

export function useApproveSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: approveSignal,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["signals"] }),
  });
}

export function useRejectSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => rejectSignal(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["signals"] }),
  });
}

export function useExecuteSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: executeSignal,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["signals"] });
      qc.invalidateQueries({ queryKey: ["positions"] });
    },
  });
}
