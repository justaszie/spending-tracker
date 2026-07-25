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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ArrowDown, ArrowUp, MoreHorizontal, Pencil, Undo2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import { ReimbursementModal } from "@/components/transactions/ReimbursementModal";
import {
  Transaction,
  TransactionListItem,
  TransactionUpdatePayload,
} from "@/types/transactions";

// Helper for formatting currency
const formatCurrency = (amount: number, currency: string = "EUR") => {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: currency,
  }).format(amount);
};

export type SortableField = "date" | "counterparty" | "amount" | "category";

export type TransactionsTableProps = {
  transactions: TransactionListItem[];
  totalCount: number;
  spendingCategories: string[];
  onUpdateTransaction: (id: string, updates: TransactionUpdatePayload) => void;

  currentPage: number;
  itemsPerPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;

  sortColumn: SortableField | null;
  sortDirection: "asc" | "desc";
  onSort: (column: SortableField) => void;
};

export function TransactionsTable({
  transactions,
  totalCount,
  spendingCategories,
  onUpdateTransaction,
  currentPage,
  itemsPerPage,
  totalPages,
  onPageChange,
  sortColumn,
  sortDirection,
  onSort,
}: TransactionsTableProps) {
  const [selectedDebit, setSelectedDebit] = useState<Transaction | null>(null);

  return (
    <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
      {transactions.length > 0 && (
        <div className="flex items-center justify-between border-b bg-muted/25 px-6 py-3 text-sm">
          <span className="font-medium text-foreground/80">
            Showing {(currentPage - 1) * itemsPerPage + 1}-
            {Math.min(currentPage * itemsPerPage, totalCount ?? 0)} of{" "}
            {totalCount ?? 0} transactions
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="h-8 px-3"
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
                    variant={currentPage === pageNum ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => onPageChange(pageNum)}
                    className="h-8 w-8 p-0"
                  >
                    {pageNum}
                  </Button>
                );
              })}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="h-8 px-3"
            >
              Next →
            </Button>
          </div>
        </div>
      )}

      <Table>
        <TableHeader className="bg-muted/40">
          <TableRow>
            <SortableHeader
              label="Date"
              className="w-[120px]"
              column="date"
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={onSort}
            />
            <SortableHeader
              label="Counterparty"
              className="w-[500px]"
              column="counterparty"
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={onSort}
            />
            <SortableHeader
              label="Amount"
              className="w-[100px]"
              column="amount"
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={onSort}
            />
            <SortableHeader
              label="Category"
              className="w-[250px]"
              column="category"
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={onSort}
            />
            <TableHead className="w-[200px] text-foreground/80">Note</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {transactions.map((item) => (
            <TransactionRow
              key={item.transaction.id}
              item={item}
              spendingCategories={spendingCategories}
              onUpdate={(updates) =>
                onUpdateTransaction(item.transaction.id, updates)
              }
              onAddReimbursement={() => setSelectedDebit(item.transaction)}
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

      <ReimbursementModal
        open={selectedDebit !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedDebit(null);
        }}
        debit={selectedDebit}
      />
    </div>
  );
}

function SortableHeader({
  label,
  className,
  column,
  sortColumn,
  sortDirection,
  onSort,
}: {
  label: string;
  className?: string;
  column: SortableField;
  sortColumn: SortableField | null;
  sortDirection: "asc" | "desc";
  onSort: (column: SortableField) => void;
}) {
  return (
    <TableHead
      className={cn(
        className,
        "cursor-pointer select-none text-foreground/80 hover:bg-muted/60",
      )}
      onClick={() => onSort(column)}
    >
      <div className="flex items-center gap-2">
        {label}
        {sortColumn === column &&
          (sortDirection === "asc" ? (
            <ArrowUp className="h-4 w-4" />
          ) : (
            <ArrowDown className="h-4 w-4" />
          ))}
      </div>
    </TableHead>
  );
}

function TransactionRow({
  item,
  spendingCategories,
  onUpdate,
  onAddReimbursement,
}: {
  item: TransactionListItem;
  spendingCategories: string[];
  onUpdate: (updates: TransactionUpdatePayload) => void;
  onAddReimbursement: () => void;
}) {
  const transaction = item.transaction;
  const reimbursedAmount = Number(item.eur_total_reimbursed);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteTemp, setNoteTemp] = useState(transaction.note || "");

  const handleSaveNote = () => {
    onUpdate({ note: noteTemp });
    setNoteOpen(false);
  };

  return (
    <TableRow className="group transition-colors hover:bg-muted/20">
      <TableCell className="font-mono text-xs text-muted-foreground">
        {format(new Date(transaction.transaction_datetime), "dd MMM yyyy")}
        <div className="text-[10px] text-muted-foreground/80">
          {format(new Date(transaction.transaction_datetime), "HH:mm")}
        </div>
      </TableCell>
      <TableCell>
        <div className="font-medium text-sm">{transaction.counterparty}</div>
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap items-center gap-2">
          <div
            className={cn(
              "font-mono font-medium",
              transaction.side === "credit"
                ? "text-emerald-600 dark:text-emerald-400"
                : "",
            )}
          >
            {transaction.side === "debit" ? "-" : "+"}
            {formatCurrency(Number(item.net_eur_amount))}
          </div>
          {reimbursedAmount > 0 && (
            <Badge
              variant="secondary"
              className="gap-1 font-mono text-[10px] font-medium text-emerald-700 dark:text-emerald-400"
              title={`${formatCurrency(reimbursedAmount)} reimbursed of ${formatCurrency(Number(transaction.eur_amount))} total`}
            >
              <Undo2 className="h-3 w-3" />
              {formatCurrency(reimbursedAmount)}
            </Badge>
          )}
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
        {transaction.side === "debit" && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={onAddReimbursement}>
                Add reimbursement
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </TableCell>
    </TableRow>
  );
}

