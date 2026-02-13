// API service with placeholder functions
// TODO: Replace placeholder functions with actual fetch() calls to your backend

// The quickest way to get user's access token is from supabase directly
import { supabase  } from "../supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

// Helper function to get auth headers
const getAuthHeaders = async () => {
  const {data: {session}} = await supabase.auth.getSession();
  const token = session.access_token
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

// Transactions API
export const transactionsAPI = {
  // TODO: Replace with actual API call
  // GET /api/v1/transactions?page=1&limit=50&search=...&sort=...
  getTransactions: async (params = {}) => {
    const {
      page = 1,
      limit = 50,
      search = "",
      sortBy = "transaction_datetime",
      sortOrder = "desc",
    } = params;


    // PLACEHOLDER: Replace this with actual fetch call
    // Example:
    // const queryParams = new URLSearchParams({
    //   page: page.toString(),
    //   limit: limit.toString(),
    //   ...(search && { search }),
    //   sort_by: sortBy,
    //   sort_order: sortOrder,
    // });
    // const response = await fetch(`${API_BASE_URL}/transactions?${queryParams}`, {
    //   method: 'GET',
    //   headers: getAuthHeaders(),
    // });
    // if (!response.ok) throw new Error('Failed to fetch transactions');
    // const data = await response.json();
    // return data;

    const response = await fetch(`${API_BASE_URL}/transactions`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch transactions');
    const data = await response.json();
    return data;

    // Static placeholder data
    const mockTransactions = [
      {
        id: "txn_001",
        transaction_datetime: "2024-03-01T09:30:00Z",
        type: "card_payment",
        counterparty: "Uber BV",
        orig_amount: "14.50",
        orig_currency: "EUR",
        side: "debit",
        source: "swedbank",
        eur_amount: "14.50",
        l1_category: "Transport",
        l2_category: "Taxi",
        l3_category: "Rideshare",
        note: "Morning commute",
        import_job_id: "job-1",
      },
      {
        id: "txn_002",
        transaction_datetime: "2024-03-01T12:15:00Z",
        type: "card_payment",
        counterparty: "Coffee Shop",
        orig_amount: "5.50",
        orig_currency: "EUR",
        side: "debit",
        source: "revolut",
        eur_amount: "5.50",
        l1_category: "Food & Drink",
        l2_category: "Coffee",
        l3_category: null,
        note: "Morning coffee",
        import_job_id: "job-2",
      },
      {
        id: "txn_003",
        transaction_datetime: "2024-02-28T18:45:00Z",
        type: "card_payment",
        counterparty: "Grocery Store",
        orig_amount: "87.30",
        orig_currency: "EUR",
        side: "debit",
        source: "swedbank",
        eur_amount: "87.30",
        l1_category: "Food & Drink",
        l2_category: "Groceries",
        l3_category: null,
        note: "Weekly groceries",
        import_job_id: "job-1",
      },
      {
        id: "txn_004",
        transaction_datetime: "2024-02-28T10:00:00Z",
        type: "transfer",
        counterparty: "Salary Payment",
        orig_amount: "3200.00",
        orig_currency: "EUR",
        side: "credit",
        source: "swedbank",
        eur_amount: "3200.00",
        l1_category: "Income",
        l2_category: "Salary",
        l3_category: null,
        note: "Monthly salary",
        import_job_id: null,
      },
      {
        id: "txn_005",
        transaction_datetime: "2024-02-27T14:20:00Z",
        type: "card_payment",
        counterparty: "Restaurant",
        orig_amount: "45.80",
        orig_currency: "EUR",
        side: "debit",
        source: "revolut",
        eur_amount: "45.80",
        l1_category: "Food & Drink",
        l2_category: "Restaurant",
        l3_category: "Dinner",
        note: "Team lunch",
        import_job_id: "job-2",
      },
    ];

    // Simulate filtering and sorting
    let filtered = mockTransactions;
    if (search) {
      filtered = filtered.filter(
        (t) =>
          t.counterparty.toLowerCase().includes(search.toLowerCase()) ||
          t.note?.toLowerCase().includes(search.toLowerCase()),
      );
    }

    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          transactions: filtered,
          total: filtered.length,
          page,
          limit,
        });
      }, 300);
    });
  },
};

// Statement Import API
export const statementImportAPI = {
  // TODO: Replace with actual API call
  // POST /api/v1/statement-imports
  uploadStatement: async (file, statementSource) => {
    // PLACEHOLDER: Replace this with actual fetch call
    // Example:
    // const formData = new FormData();
    // formData.append('statement_file', file);
    // formData.append('statement_source', statementSource);
    // const response = await fetch(`${API_BASE_URL}/statement-imports`, {
    //   method: 'POST',
    //   headers: {
    //     'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    //   },
    //   body: formData,
    // });
    // if (!response.ok) throw new Error('Upload failed');
    // const data = await response.json();
    // return data;

    // Static placeholder
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          import_job_id: "job-" + Date.now(),
          import_job_status: "pending",
        });
      }, 1000);
    });
  },

  // TODO: Replace with actual API call
  // GET /api/v1/statement-imports/{import_job_id}
  getImportJobStatus: async (importJobId) => {
    // PLACEHOLDER: Replace this with actual fetch call
    // Example:
    // const response = await fetch(`${API_BASE_URL}/statement-imports/${importJobId}`, {
    //   method: 'GET',
    //   headers: getAuthHeaders(),
    // });
    // if (!response.ok) throw new Error('Failed to fetch job status');
    // const data = await response.json();
    // return data;

    // Static placeholder - simulate status progression
    const statuses = ["pending", "running", "completed"];
    const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];

    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          import_job_id: importJobId,
          import_job_status: randomStatus,
        });
      }, 500);
    });
  },

  // TODO: Replace with actual API call
  // GET /api/v1/statement-imports/{import_job_id}/transactions
  getImportJobTransactions: async (importJobId) => {
    // PLACEHOLDER: Replace this with actual fetch call
    // Example:
    // const response = await fetch(`${API_BASE_URL}/statement-imports/${importJobId}/transactions`, {
    //   method: 'GET',
    //   headers: getAuthHeaders(),
    // });
    // if (!response.ok) throw new Error('Failed to fetch transactions');
    // const data = await response.json();
    // return data;

    // Static placeholder
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          transactions: [
            {
              id: "1",
              transaction_datetime: "2024-01-15T10:30:00Z",
              counterparty: "Coffee Shop",
              orig_amount: "5.50",
              orig_currency: "EUR",
              side: "debit",
            },
            {
              id: "2",
              transaction_datetime: "2024-01-14T15:20:00Z",
              counterparty: "Grocery Store",
              orig_amount: "45.30",
              orig_currency: "EUR",
              side: "debit",
            },
          ],
        });
      }, 500);
    });
  },
};
