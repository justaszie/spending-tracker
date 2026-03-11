import { useState } from "react";
import { format } from "date-fns";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Plus, MoreHorizontal, Pencil, Upload, ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import { ImportModal } from "@/components/transactions/ImportModal";
import {
  GetTransactionsParams,
  Transaction,
  TransactionUpdatePayload,
} from "@/types/transactions";
import { useTransactions } from "@/hooks/transactions/use-transactions";
import { useSpendingCategories } from "@/hooks/transactions/use-spending-cateogries";
import { useUpdateTransaction } from "@/hooks/transactions/use-update-transaction";
import { useAuth } from "@/contexts/AuthContext";
import { TransactionSearch } from "@/components/transactions/TransactionSearch";
import ErrorPage from "@/pages/error";
import { FullScreenLoader } from "@/components/FullScreenLoader";

// Helper for formatting currency
const formatCurrency = (amount: number, currency: string = "EUR") => {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: currency,
  }).format(amount);
};

type SortableField = "date" | "counterparty" | "amount" | "category";

export default function Dashboard() {
  const [searchTerm, setSearchTerm] = useState("");
  // const [transactions, setTransactions] =
  // useState<Transaction[]>(mockTransactions);
  const [filterType, setFilterType] = useState<"all" | "untagged">("all");
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<SortableField | null>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const { logout, user } = useAuth();

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

  const { data, isLoading, error, isFetching } = useTransactions(params);
  const {
    data: spendingCategoriesData,
  } = useSpendingCategories();

  const updateTransactionMutation = useUpdateTransaction();

  if (isLoading) {
    return <FullScreenLoader open label="Loading dashboard..." />;
  }

  if (error) {
    return (
      <ErrorPage
        title="Unable to load dashboard"
        message="An unexpected error occurred while loading your transactions. Please try again in a moment."
      />
    );
  }

  const transactions = data?.transactions ?? [];
  // TODO - Remove the test value once the API returns proper total value
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

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/10">
      {/* Navbar */}
      <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center px-6">
          <div className="mr-4 flex items-center gap-2 font-semibold">
            <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              <span className="text-xs font-bold">S</span>
            </div>
            <span>SpendFlow</span>
          </div>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <a
              href="#"
              className="transition-colors hover:text-foreground/80 text-foreground"
            >
              Transactions
            </a>
            <a
              href="#"
              className="transition-colors hover:text-foreground/80 text-foreground/60"
            >
              Analytics
            </a>
            <a
              href="#"
              onClick={() => setImportModalOpen(true)}
              className="transition-colors hover:text-foreground/80 text-foreground/60"
            >
              Import
            </a>
          </nav>
          <div className="ml-auto flex items-center space-x-4">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setImportModalOpen(true)}
            >
              <Upload className="mr-2 h-4 w-4" />
              Import
            </Button>
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center">
                <p>{user && user.email?.slice(0, 1).toUpperCase()}</p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="text-xs text-muted-foreground"
                onClick={() => logout()}
              >
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container py-8 px-6">
        {/* Stats Row - Placeholder for future analytics cards */}
        <div></div>

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <TransactionSearch value={searchTerm} onSearchChange={handleSearchChange} />
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
            <Button
              variant="outline"
              size="sm"
              onClick={() => setImportModalOpen(true)}
            >
              <Upload className="mr-2 h-4 w-4" />
              Import
            </Button>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Manual
            </Button>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          {transactions.length > 0 && (
            <div className="px-6 py-3 border-b bg-muted/20 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {(currentPage - 1) * itemsPerPage + 1} -
                {Math.min(currentPage * itemsPerPage, totalCount ?? 0)} of{" "}
                {totalCount ?? 0} transactions
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="h-7 px-3"
                >
                  ← Prev
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum =
                      currentPage > 3 ? currentPage - 2 + i : i + 1;
                    if (pageNum > totalPages) return null;
                    return (
                      <Button
                        key={pageNum}
                        variant={
                          currentPage === pageNum ? "secondary" : "outline"
                        }
                        size="sm"
                        onClick={() => setCurrentPage(pageNum)}
                        className="h-7 w-7 p-0"
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setCurrentPage((p) => Math.min(totalPages, p + 1))
                  }
                  disabled={currentPage === totalPages}
                  className="h-7 px-3"
                >
                  Next →
                </Button>
              </div>
            </div>
          )}
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow>
                <TableHead
                  className="w-[120px] cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("date")}
                >
                  <div className="flex items-center gap-2">
                    Date
                    {sortColumn === "date" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="h-4 w-4" />
                      ) : (
                        <ArrowDown className="h-4 w-4" />
                      ))}
                  </div>
                </TableHead>
                <TableHead
                  className="w-[250px] cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("counterparty")}
                >
                  <div className="flex items-center gap-2">
                    Counterparty
                    {sortColumn === "counterparty" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="h-4 w-4" />
                      ) : (
                        <ArrowDown className="h-4 w-4" />
                      ))}
                  </div>
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("amount")}
                >
                  <div className="flex items-center gap-2">
                    Amount
                    {sortColumn === "amount" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="h-4 w-4" />
                      ) : (
                        <ArrowDown className="h-4 w-4" />
                      ))}
                  </div>
                </TableHead>
                <TableHead
                  className="w-[300px] cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("category")}
                >
                  <div className="flex items-center gap-2">
                    Category
                    {sortColumn === "category" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="h-4 w-4" />
                      ) : (
                        <ArrowDown className="h-4 w-4" />
                      ))}
                  </div>
                </TableHead>
                <TableHead className="w-[200px]">Note</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((t) => (
                <TransactionRow
                  key={t.id}
                  transaction={t}
                  spendingCategories={spendingCategories}
                  onUpdate={(updates) => handleUpdateTransaction(t.id, updates)}
                />
              ))}
              {transactions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center">
                    No transactions found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </main>

      <ImportModal open={importModalOpen} onOpenChange={setImportModalOpen} />
    </div>
  );
}

interface TransactionRowProps {
  transaction: Transaction;
  spendingCategories: string[],
  onUpdate: (updates: TransactionUpdatePayload) => void;
}

function TransactionRow({ transaction, spendingCategories, onUpdate }: TransactionRowProps) {
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteTemp, setNoteTemp] = useState(transaction.note || "");

  const handleSaveNote = () => {
    onUpdate({ note: noteTemp });
    setNoteOpen(false);
  };

  return (
    <TableRow className="group hover:bg-muted/30 transition-colors">
      <TableCell className="font-mono text-xs text-muted-foreground">
        {format(new Date(transaction.transaction_datetime), "dd MMM yyyy")}
        <div className="text-[10px] opacity-60">
          {format(new Date(transaction.transaction_datetime), "HH:mm")}
        </div>
      </TableCell>
      <TableCell>
        <div className="font-medium text-sm">{transaction.counterparty}</div>
      </TableCell>
      <TableCell>
        <div
          className={cn(
            "font-mono font-medium",
            transaction.side === "credit"
              ? "text-emerald-600 dark:text-emerald-400"
              : "",
          )}
        >
          {transaction.side === "debit" ? "-" : "+"}
          {formatCurrency(Number(transaction.eur_amount))}
        </div>
      </TableCell>
      <TableCell>
        <div className="w-full max-w-[280px]">
          <CategorySelector
            category={transaction.spending_category}
            existing={spendingCategories}
            onSelect={(cat) => onUpdate({ spending_category: cat })}
          />
        </div>
      </TableCell>
      <TableCell>
        <Popover open={noteOpen} onOpenChange={setNoteOpen}>
          <PopoverTrigger asChild>
            <div className="cursor-pointer min-h-[32px] flex items-center group/note">
              {transaction.note ? (
                <span
                  className="text-sm text-muted-foreground truncate max-w-[150px] block"
                  title={transaction.note}
                >
                  {transaction.note}
                </span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-auto px-2 opacity-0 group-hover:opacity-100 group-hover/note:opacity-100 text-muted-foreground text-xs"
                >
                  <Pencil className="h-3 w-3 mr-1" /> Note
                </Button>
              )}
            </div>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="grid gap-4">
              <div className="space-y-2">
                <h4 className="font-medium leading-none">Note</h4>
                <p className="text-sm text-muted-foreground">
                  Add details about this transaction.
                </p>
              </div>
              <Textarea
                value={noteTemp}
                onChange={(e) => setNoteTemp(e.target.value)}
                placeholder="e.g. Dinner with clients..."
                className="h-24 resize-none"
              />
              <Button size="sm" onClick={handleSaveNote}>
                Save Note
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      </TableCell>
      <TableCell>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground"
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
}
