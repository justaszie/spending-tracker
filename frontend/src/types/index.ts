// Align with backend Transaction / API responses where applicable

export type Side = 'debit' | 'credit'
export type TransactionSource = 'swedbank' | 'revolut' | string

export interface Transaction {
  id: string
  transaction_datetime: string
  type?: string
  counterparty: string
  orig_amount: string
  orig_currency: string
  side: Side
  source: TransactionSource
  eur_amount: string
  manually_added?: boolean
  note: string | null
  spending_category: string | null
  meal_type: string | null
  import_job_id: string | null
}

/** Backend may return either a list or a paginated response */
export interface TransactionsResponse {
  transactions: Transaction[]
  total?: number
  page?: number
  size?: number
}

export interface GetTransactionsParams {
  page?: number
  size?: number
  search?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  /** Filter by transaction side (repeated param: side=debit&side=credit) */
  side?: Side[]
  /** Filter by spending category (repeated param: spending_category=...&spending_category=...) */
  spending_category?: string[]
  /** Only transactions with null spending_category */
  untaggedOnly?: boolean
}

export interface ImportJobResult {
  import_job_id: string
  import_job_status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface ImportJobTransactionsResponse {
  transactions: Array<{
    id: string
    transaction_datetime: string
    counterparty: string
    orig_amount: string
    orig_currency: string
    side: Side
  }>
}

export type StatementSource = 'swedbank' | 'revolut'
