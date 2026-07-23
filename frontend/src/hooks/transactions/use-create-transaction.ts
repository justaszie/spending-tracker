import { useMutation, useQueryClient } from "@tanstack/react-query";
import { transactionsAPI } from "@/lib/api";
import type {
  Transaction,
  TransactionCreatePayload,
} from "@/types/transactions";

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation<Transaction, Error, TransactionCreatePayload>({
    mutationFn: (payload) => transactionsAPI.createTransaction(payload),
    onSuccess: () => {
      // Refetch transactions list, stats and spending categories
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}