export type TransactionSide = "credit" | "debit";
export type TransactionSource = "swedbank" | "revolut" | "manual";

export type TransactionType =
  | "card_payment"
  | "cash_withdrawal"
  | "cash_payment"
  | "transfer"
  | "card_refund"
  | "other";

export type Transaction = {
  id: string;
  transaction_datetime: string;
  type?: TransactionType;
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

export type TransactionCreatePayload = {
  transaction_datetime: string;
  counterparty: string;
  orig_amount: number;
  orig_currency: string;
  side: TransactionSide;
  type: TransactionType;
  spending_category?: string | null;
  note?: string | null;
};

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

export type TransactionListItem = {
  transaction: Transaction;
  eur_total_reimbursed: string;
  net_eur_amount: string;
};

export type TransactionsResponse = {
  transactions: TransactionListItem[];
  total?: number;
  page?: number;
  size?: number;
};

export type PeriodPreset = "L30" | "MTD" | "YTD" | "ALL_TIME" | "CUSTOM";

export type TransactionsStatsParams = {
  period?: PeriodPreset;
  dateFrom?: string;
  dateTo?: string;
  includePrevious?: boolean;
};

export type StatsNumeric = number | string;

export type TransactionsStatsCategory = {
  category: string | null;
  total: StatsNumeric;
  avg_daily: StatsNumeric | null;
};

export type TransactionsStatsSpendGroup = {
  total: StatsNumeric;
  avg_daily: StatsNumeric;
  by_category: TransactionsStatsCategory[];
};

export type TransactionsStatsPeriod = {
  date_from: string;
  date_to: string;
  days_count: number;
  groups: {
    spend: TransactionsStatsSpendGroup;
  };
};

export type TransactionsStatsDeltaValues = {
  abs_change: StatsNumeric;
  pct_change: StatsNumeric | null;
};

export type TransactionsStatsDeltas = {
  groups: {
    spend: {
      total: TransactionsStatsDeltaValues;
      avg_daily: TransactionsStatsDeltaValues;
    };
  };
};

export type TransactionsStatsResponse = {
  period: PeriodPreset;
  current_period: TransactionsStatsPeriod | null;
  previous_period: TransactionsStatsPeriod | null;
  deltas: TransactionsStatsDeltas | null;
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
