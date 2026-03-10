import { QueryClient } from "@tanstack/react-query";

// Expose for React Query DevTools
declare global {
  interface Window {
    __TANSTACK_QUERY_CLIENT__: import("@tanstack/query-core").QueryClient;
  }
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: 2,
    },
    mutations: {
      retry: 2,
    },
  },
});
