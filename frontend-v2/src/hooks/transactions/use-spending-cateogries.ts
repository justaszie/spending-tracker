import { useQuery } from "@tanstack/react-query";
import { transactionsAPI } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export function useSpendingCategories() {
  const { session, isAuthLoading } = useAuth();

  return useQuery<string[]>({
    queryKey: ["transactions", "spending-categories"],
    queryFn: () => transactionsAPI.getSpendingCategories(),
    // Prevent backend queries when unauthenticated
    enabled: !!session && !isAuthLoading,
  });
}

