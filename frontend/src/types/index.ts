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
  l1_category: string | null
  l2_category: string | null
  l3_category: string | null
  note: string | null
  import_job_id: string | null
}

/** Backend may return either a list or a paginated response */
export interface TransactionsResponse {
  transactions: Transaction[]
  total?: number
  page?: number
  limit?: number
}

export interface GetTransactionsParams {
  page?: number
  limit?: number
  search?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
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
