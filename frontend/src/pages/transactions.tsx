import { useState } from "react";
import {
  GetTransactionsParams,
  TransactionUpdatePayload,
} from "@/types/transactions";
import { useTransactions } from "@/hooks/transactions/use-transactions";
import { useSpendingCategories } from "@/hooks/transactions/use-spending-cateogries";
import { useUpdateTransaction } from "@/hooks/transactions/use-update-transaction";
import { TransactionSearch } from "@/components/transactions/TransactionSearch";
import ErrorPage from "@/pages/error";
import { FullScreenLoader } from "@/components/FullScreenLoader";
import {
  SortableField,
  TransactionsTable,
} from "@/components/transactions/TransactionsTable";

export default function TransactionsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<SortableField | null>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const itemsPerPage = 50;

  const sortByMapping: Record<SortableField, GetTransactionsParams["sortBy"]> =
    {
      date: "transaction_datetime",
      counterparty: "counterparty",
      amount: "eur_amount",
      category: "spending_category",
    };

  // Defining query params to be used to query transactions
  const params: GetTransactionsParams = {
    page: currentPage,
    size: itemsPerPage,
    search: searchTerm || undefined,
    sortBy: sortColumn ? sortByMapping[sortColumn] : undefined,
    sortOrder: sortDirection,
  };

  const { data, isLoading, error } = useTransactions(params);
  const { data: spendingCategoriesData } = useSpendingCategories();

  const updateTransactionMutation = useUpdateTransaction();

  if (isLoading) {
    return <FullScreenLoader open label="Loading transactions..." />;
  }

  if (error) {
    return (
      <ErrorPage
        title="Unable to load transactions"
        message="An unexpected error occurred while loading your transactions. Please try again in a moment."
      />
    );
  }

  const transactions = data?.transactions ?? [];
  const totalCount = data?.total || 0;
  const spendingCategories = spendingCategoriesData ?? [];

  const handleSort = (
    column: "date" | "counterparty" | "amount" | "category",
  ) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const handleUpdateTransaction = (
    id: string,
    updates: TransactionUpdatePayload,
  ) => {
    updateTransactionMutation.mutate({ id, updates });
  };

  const totalPages = Math.ceil(totalCount / itemsPerPage);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  return (
    <main className="py-8 px-6">
      {/* Stats Row - Placeholder for future analytics cards */}
      <div></div>
      <h2 className="mb-1 font-bold">Transaction History</h2>
      <p className="text-muted-foreground text-sm mb-6">
        All transactions
      </p>
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <TransactionSearch
            value={searchTerm}
            onSearchChange={handleSearchChange}
          />
        </div>
      </div>

      {/* Transactions Table */}
      <TransactionsTable
        transactions={transactions}
        totalCount={totalCount}
        spendingCategories={spendingCategories}
        onUpdateTransaction={handleUpdateTransaction}
        currentPage={currentPage}
        itemsPerPage={itemsPerPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        onSort={handleSort}
      />
    </main>
  );
}

