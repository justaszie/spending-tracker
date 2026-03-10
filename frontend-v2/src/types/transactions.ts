export type TransactionSide = "credit" | "debit";
export type TransactionSource = "swedbank" | "revolut";

export type Transaction = {
  id: string;
  transaction_datetime: string;
  type?: string;
  counterparty: string;
  orig_amount: string;
  orig_currency: string;
  side: TransactionSide;
  source: TransactionSource;
  eur_amount: string;
  manually_added?: boolean;
  note: string | null;
  spending_category: string | null;
  meal_type: string | null;
  import_job_id: string | null;
};

export type TransactionUpdatePayload = Partial<
  Pick<Transaction, "spending_category" | "note">
>;

export type GetTransactionsParams = {
  page?: number;
  size?: number;
  search?: string;
  sortBy?:
    | "transaction_datetime"
    | "counterparty"
    | "eur_amount"
    | "spending_category";
  sortOrder?: "asc" | "desc";
  untaggedOnly?: boolean;
  side?: TransactionSide[];
  spendingCategory?: string[];
};

export type TransactionsResponse = {
  transactions: Transaction[];
  total?: number;
  page?: number;
  size?: number;
};

export type ImportJobStatus = "pending" | "running" | "completed" | "failed";

export type StatementSource = "swedbank" | "revolut";

export type ImportJobResult = {
  import_job_id: string;
  import_job_status: ImportJobStatus;
  failure_reason: string | null;
  imported_txn_count: number | null;
  duplicate_txn_count: number | null;
};
