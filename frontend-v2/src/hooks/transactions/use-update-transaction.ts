import { useMutation, useQueryClient } from "@tanstack/react-query";
import { transactionsAPI } from "@/lib/api";
import {
  Transaction,
  TransactionUpdatePayload,
} from "@/types/transactions";

interface UpdateTransactionVariables {
  id: string;
  updates: TransactionUpdatePayload;
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, updates }: UpdateTransactionVariables) =>
      transactionsAPI.patchTransaction(id, updates),
    onSuccess: () => {
      // Refetch transactions after a successful update
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

