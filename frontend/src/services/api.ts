import { supabase } from "../supabaseClient";
import type {
  GetTransactionsParams,
  TransactionsResponse,
  ImportJobResult,
  ImportJobTransactionsResponse,
  StatementSource,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function getAuthHeaders(): Promise<HeadersInit> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token;
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

export const transactionsAPI = {
  getTransactions: async (
    params: GetTransactionsParams = {},
  ): Promise<TransactionsResponse> => {
    const {
      page = 1,
      size = 50,
      search = "",
      sortBy = "transaction_datetime",
      sortOrder = "desc",
      side,
      spending_category,
      untaggedOnly,
    } = params;

    const queryParams = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    if (search) queryParams.set("search", search.trim());

    if (side?.length) {
      side.forEach((value) => queryParams.append("side", value));
    }
    if (spending_category?.length) {
      spending_category.forEach((value) => queryParams.append("spending_category", value));
    }
    if (untaggedOnly) {
      queryParams.set("untagged_only", "true");
    }

    const response = await fetch(
      `${API_BASE_URL}/transactions?${queryParams}`,
      {
        method: "GET",
        headers: await getAuthHeaders(),
      },
    );
    if (!response.ok) throw new Error("Failed to fetch transactions");
    const data = await response.json();
    // Backend may return list directly or { transactions, total, page, limit }
    if (Array.isArray(data)) {
      return { transactions: data, total: data.length, page, size };
    }
    return data as TransactionsResponse;
  },
};

export const statementImportAPI = {
  uploadStatement: async (
    file: File,
    statementSource: StatementSource,
  ): Promise<ImportJobResult> => {
    const formData = new FormData();
    formData.append("statement_file", file);
    formData.append("statement_source", statementSource);
    const headers = await getAuthHeaders();
    const authHeader =
      typeof headers === "object" && headers && "Authorization" in headers
        ? (headers as Record<string, string>).Authorization
        : undefined;
    const response = await fetch(`${API_BASE_URL}/statement-imports`, {
      method: "POST",
      headers: authHeader ? { Authorization: authHeader } : {},
      body: formData,
    });
    if (!response.ok) throw new Error("Upload failed");
    return response.json() as Promise<ImportJobResult>;
  },

  getImportJobStatus: async (importJobId: string): Promise<ImportJobResult> => {
    const response = await fetch(
      `${API_BASE_URL}/statement-imports/${importJobId}`,
      {
        method: "GET",
        headers: await getAuthHeaders(),
      },
    );
    if (!response.ok) throw new Error("Failed to fetch job status");
    return response.json() as Promise<ImportJobResult>;
  },

  getImportJobTransactions: async (
    importJobId: string,
  ): Promise<ImportJobTransactionsResponse> => {
    const response = await fetch(
      `${API_BASE_URL}/statement-imports/${importJobId}/transactions`,
      {
        method: "GET",
        headers: await getAuthHeaders(),
      },
    );
    if (!response.ok) throw new Error("Failed to fetch transactions");
    return response.json() as Promise<ImportJobTransactionsResponse>;
  },
};
