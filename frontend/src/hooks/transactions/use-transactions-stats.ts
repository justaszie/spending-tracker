import { useQuery } from "@tanstack/react-query";
import { transactionsAPI } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  TransactionsStatsParams,
  TransactionsStatsResponse,
} from "@/types/transactions";

export function useTransactionsStats(params: TransactionsStatsParams) {
  const { session, isAuthLoading } = useAuth();

  return useQuery<TransactionsStatsResponse>({
    queryKey: ["transactions", "stats", params],
    queryFn: () => transactionsAPI.getTransactionsStats(params),
    enabled: !!session && !isAuthLoading,
  });
}
