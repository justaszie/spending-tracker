import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reimbursementsAPI } from "@/lib/api";
import type {
  Reimbursement,
  ReimbursementCreatePayload,
} from "@/types/reimbursements";

export function useCreateReimbursement() {
  const queryClient = useQueryClient();

  return useMutation<Reimbursement, Error, ReimbursementCreatePayload>({
    mutationFn: (payload) => reimbursementsAPI.createReimbursement(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}
