export type Reimbursement = {
  debit_txn_id: string;
  credit_txn_id: string;
  orig_reimbursed_amount: number;
  orig_reimbursed_ccy: string;
  eur_reimbursed_amount: number;
  created_at: string;
  updated_at: string;
};

export type ReimbursementCreatePayload = {
  debit_txn_id: string;
  credit_txn_id: string;
  orig_reimbursed_amount: number;
};
