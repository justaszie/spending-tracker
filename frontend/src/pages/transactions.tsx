import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { ImportModal } from "@/components/transactions/ImportModal";
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
import { queryClient } from "@/lib/queryClient";
import { AppHeader } from "@/components/layout/AppHeader";
import {
  SortableField,
  TransactionsTable,
} from "@/components/transactions/TransactionsTable";

export default function TransactionsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<"all" | "untagged">("all");
  const [importModalOpen, setImportModalOpen] = useState(false);
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
    untaggedOnly: filterType === "untagged" ? true : undefined,
    side: filterType === "untagged" ? ["debit"] : undefined,
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

  const handleFilterChange = (filter: "all" | "untagged") => {
    setFilterType(filter);
    setCurrentPage(1); // Reset to first page on filter change
  };

  // Fire when user comes back from import modal to view refreshed transactions
  const handleViewTransactions = () => {
    // Refresh transactions data and close the modal
    queryClient.invalidateQueries({ queryKey: ["transactions"] });
    setImportModalOpen(false);
  };

  return (
    <div className="container mx-auto min-h-screen bg-background text-foreground font-sans selection:bg-primary/10">
      <AppHeader />

      <main className="py-8 px-6">
        {/* Stats Row - Placeholder for future analytics cards */}
        <div></div>

        <h2 className="mb-1 font-bold">Transaction History</h2>
        <p></p>
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <TransactionSearch
              value={searchTerm}
              onSearchChange={handleSearchChange}
            />
            <div className="flex items-center border rounded-md bg-card p-1">
              <Button
                variant={filterType === "all" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => handleFilterChange("all")}
                className="h-7 px-3 text-xs"
              >
                All
              </Button>
              <Button
                variant={filterType === "untagged" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => handleFilterChange("untagged")}
                className="h-7 px-3 text-xs"
              >
                Untagged
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setImportModalOpen(true)}>
              <Upload className="mr-2 h-4 w-4" />
              Import Statement
            </Button>
            {/* Not supported right now */}
            {/* <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Manual
            </Button> */}
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

      <ImportModal
        open={importModalOpen}
        onOpenChange={setImportModalOpen}
        onViewTransactions={handleViewTransactions}
      />
    </div>
  );
}

