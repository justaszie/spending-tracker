import { useState } from "react";
import { TransactionSearch } from "@/components/transactions/TransactionSearch";
import { useTransactions } from "@/hooks/transactions/use-transactions";
import { useSpendingCategories } from "@/hooks/transactions/use-spending-cateogries";
import { useUpdateTransaction } from "@/hooks/transactions/use-update-transaction";
import {
  GetTransactionsParams,
  TransactionUpdatePayload,
} from "@/types/transactions";
import ErrorPage from "@/pages/error";
import { FullScreenLoader } from "@/components/FullScreenLoader";
import {
  SortableField,
  TransactionsTable,
} from "@/components/transactions/TransactionsTable";

export default function ReviewPage() {
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

  // Same behavior as Transactions with `filterType="untagged"`
  const params: GetTransactionsParams = {
    page: currentPage,
    size: itemsPerPage,
    search: searchTerm || undefined,
    sortBy: sortColumn ? sortByMapping[sortColumn] : undefined,
    sortOrder: sortDirection,
    untaggedOnly: true,
    side: ["debit"],
  };

  const { data, isLoading, error } = useTransactions(params);
  const { data: spendingCategoriesData } = useSpendingCategories();
  const updateTransactionMutation = useUpdateTransaction();

  if (isLoading) {
    return <FullScreenLoader open label="Loading transactions review..." />;
  }

  if (error) {
    return (
      <ErrorPage
        title="Unable to load review page"
        message="An unexpected error occurred while loading your untagged transactions. Please try again in a moment."
      />
    );
  }

  const transactions = data?.transactions ?? [];
  const totalCount = data?.total || 0;
  const spendingCategories = spendingCategoriesData ?? [];
  const totalPages = Math.ceil(totalCount / itemsPerPage);

  const handleSort = (column: SortableField) => {
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

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  return (
    <main className="py-8 px-6">
      <h2 className="mb-1 font-bold">Review</h2>
      <p className="text-muted-foreground text-sm mb-6">
        Untagged debit transactions that need a category.
      </p>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <TransactionSearch
            value={searchTerm}
            onSearchChange={handleSearchChange}
          />
        </div>
      </div>

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
