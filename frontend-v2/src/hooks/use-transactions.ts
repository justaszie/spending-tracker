import { useQuery } from "@tanstack/react-query";
import {
  GetTransactionsParams,
  TransactionsResponse,
} from "@/types/transactions";
import { transactionsAPI } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export function useTransactions(params: GetTransactionsParams) {
  const { session, isAuthLoading } = useAuth();

  return useQuery<TransactionsResponse>({
    queryKey: ["transactions", params],
    queryFn: () => transactionsAPI.getTransactions(params),
    placeholderData: (prev) => prev,
    // Prevent backend queries when unauthenticated
    enabled: !!session && !isAuthLoading,
  });
}

