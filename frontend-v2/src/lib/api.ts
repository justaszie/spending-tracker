import { supabase } from "@/lib/supabaseClient";
import type {
  GetTransactionsParams,
  TransactionsResponse,
  Transaction,
  ImportJobResult,
  StatementSource,
} from "@/types/transactions";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export type ApiFieldError = { path: string; message: string };

export class ApiError extends Error {
  status: number;
  fieldErrors?: ApiFieldError[];
  raw?: unknown;

  constructor(args: {
    status: number;
    message: string;
    fieldErrors?: ApiFieldError[];
    raw?: unknown;
  }) {
    super(args.message);
    this.name = "ApiError";
    this.status = args.status;
    this.fieldErrors = args.fieldErrors;
    this.raw = args.raw;
  }
}

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

type FastApiValidationErrorItem = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getFastApiValueErrorMessage(detail: unknown): string | null {
  if (!Array.isArray(detail)) return null;
  const match = detail
    .map((item) => (isRecord(item) ? (item as FastApiValidationErrorItem) : null))
    .filter((item): item is FastApiValidationErrorItem => Boolean(item))
    .find((item) => item.type === "value_error" && typeof item.msg === "string" && item.msg);
  return match?.msg ?? null;
}

function normalizeLocToPath(loc: Array<string | number> | undefined): string {
  if (!loc?.length) return "body";
  const parts = loc
    .filter((p) => p !== "body" && p !== "query" && p !== "path" && p !== "header")
    .map(String);
  return parts.length ? parts.join(".") : "body";
}

function normalizeFastApi422(detail: unknown): ApiFieldError[] {
  if (!Array.isArray(detail)) return [];
  return detail
    .map((item) => (isRecord(item) ? (item as FastApiValidationErrorItem) : null))
    .filter((item): item is FastApiValidationErrorItem => Boolean(item))
    .map((item) => ({
      path: normalizeLocToPath(item.loc),
      message: String(item.msg ?? "Invalid value"),
    }));
}

function summarizeFieldErrors(fieldErrors: ApiFieldError[]): string | null {
  if (!fieldErrors.length) return null;
  const prioritized = fieldErrors.find((e) =>
    ["file_size", "file_type", "statement_file", "statement_source"].includes(e.path),
  );
  if (prioritized) return prioritized.message;
  return fieldErrors[0]?.message ?? null;
}

async function throwApiErrorFromResponse(
  response: Response,
  fallbackMessage: string,
): Promise<never> {
  const contentType = response.headers.get("content-type") ?? "";
  let raw: unknown = undefined;

  try {
    if (contentType.includes("application/json")) {
      raw = (await response.json()) as unknown;
    } else {
      const text = await response.text();
      raw = text ? { detail: text } : undefined;
    }
  } catch {
    // ignore parsing errors; we'll fall back to generic message
  }

  const status = response.status || 0;
  let fieldErrors: ApiFieldError[] | undefined;
  let message = fallbackMessage;

  if (status === 422 && isRecord(raw) && "detail" in raw) {
    const detail = (raw as Record<string, unknown>).detail;
    const valueErrorMessage = getFastApiValueErrorMessage(detail);
    if (valueErrorMessage) {
      message = valueErrorMessage;
    } else {
      fieldErrors = normalizeFastApi422(detail);
      message = fallbackMessage;
    }
  } else if (isRecord(raw) && typeof raw.detail === "string" && raw.detail) {
    message = raw.detail;
  }

  throw new ApiError({ status, message, fieldErrors, raw });
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
      spendingCategory,
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
    if (spendingCategory?.length) {
      spendingCategory.forEach((value) =>
        queryParams.append("spending_category", value),
      );
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
    if (!response.ok) {
      await throwApiErrorFromResponse(response, "Failed to fetch transactions");
    }
    const data = await response.json();
    // Backend may return list directly or { transactions, total, page, limit }
    if (Array.isArray(data)) {
      return { transactions: data, total: data.length, page, size };
    }
    return data as TransactionsResponse;
  },

  getSpendingCategories: async (): Promise<string[]> => {
    const response = await fetch(
      `${API_BASE_URL}/transactions/spending-categories`,
      { method: "GET", headers: await getAuthHeaders() },
    );
    if (!response.ok) {
      await throwApiErrorFromResponse(response, "Failed to fetch spending categories");
    }
    return response.json() as Promise<string[]>;
  },

  patchTransaction: async (
    transactionId: string,
    payload: { spending_category?: string | null; note?: string | null },
  ): Promise<Transaction> => {
    const response = await fetch(
      `${API_BASE_URL}/transactions/${transactionId}`,
      {
        method: "PATCH",
        headers: await getAuthHeaders(),
        body: JSON.stringify(payload),
      },
    );
    if (!response.ok) {
      await throwApiErrorFromResponse(response, "Failed to update transaction");
    }
    return response.json() as Promise<Transaction>;
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
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/statement-imports`, {
        method: "POST",
        headers: authHeader ? { Authorization: authHeader } : {},
        body: formData,
      });
    } catch (error) {
      throw new ApiError({
        status: 0,
        message: "Upload failed. Please try again.",
        raw: error,
      });
    }

    if (!response.ok) {
      await throwApiErrorFromResponse(
        response,
        "Upload failed. Please try again.",
      );
    }
    return response.json() as Promise<ImportJobResult>;
  },

  getImportJobStatus: async (
    importJobId: string,
  ): Promise<ImportJobResult> => {
    const response = await fetch(
      `${API_BASE_URL}/statement-imports/${importJobId}`,
      {
        method: "GET",
        headers: await getAuthHeaders(),
      },
    );
    if (!response.ok) {
      await throwApiErrorFromResponse(response, "Failed to fetch job status");
    }
    return response.json() as Promise<ImportJobResult>;
  },
};
