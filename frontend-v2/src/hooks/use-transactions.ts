import { useQuery } from "@tanstack/react-query"
import { GetTransactionsParams, TransactionsResponse } from "@/types/transactions"

import { transactionsAPI } from "@/lib/api"

export function useTransactions(params: GetTransactionsParams) {
  return useQuery<TransactionsResponse>({
    queryKey: ["transactions", params],
    queryFn: () => transactionsAPI.getTransactions(params),
    placeholderData: (prev) => prev,
  })
}

