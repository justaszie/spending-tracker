import { useState } from "react";
import {
  GetTransactionsParams,
  TransactionUpdatePayload,
} from "@/types/transactions";
import { useTransactions } from "@/hooks/transactions/use-transactions";
import { useSpendingCategories } from "@/hooks/transactions/use-spending-cateogries";
import { useUpdateTransaction } from "@/hooks/transactions/use-update-transaction";
import { TransactionSearch } from "@/components/transactions/TransactionSearch";
import { UntaggedReviewBanner } from "@/components/transactions/UntaggedReviewBanner";
import { TotalSpendCard } from "@/components/transactions/stats/TotalSpendCard";
import { AvgDailySpendCard } from "@/components/transactions/stats/AvgDailySpendCard";
import { TopCategoriesCard } from "@/components/transactions/stats/TopCategoriesCard";
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
  const { data: untaggedDebitData, dataUpdatedAt: untaggedDebitUpdatedAt } =
    useTransactions({
    page: 1,
    size: 1,
    untaggedOnly: true,
    side: ["debit"],
    });
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
  const untaggedDebitCount = untaggedDebitData?.total || 0;
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
    <main className="px-6 py-6">
      <UntaggedReviewBanner
        untaggedDebitCount={untaggedDebitCount}
        refreshedAt={untaggedDebitUpdatedAt}
      />

      <header className="mb-4">
        <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
      </header>

      <div className="mb-6 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-12">
        <div className="xl:col-span-3">
          <TotalSpendCard />
        </div>
        <div className="xl:col-span-3">
          <AvgDailySpendCard />
        </div>
        <div className="md:col-span-2 xl:col-span-6">
          <TopCategoriesCard />
        </div>
      </div>

      <section>
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Transaction history</h2>
            <p className="text-sm text-muted-foreground">
              All imported transactions
            </p>
          </div>
          <div className="flex w-full items-center gap-2 sm:w-auto">
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
      </section>
    </main>
  );
}

