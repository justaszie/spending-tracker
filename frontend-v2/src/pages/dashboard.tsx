import { useState, useEffect } from "react";
import { format } from "date-fns";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { 
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { 
  Search, 
  Filter, 
  Download, 
  Plus, 
  MoreHorizontal, 
  Tag,
  CreditCard,
  Wallet,
  CheckCircle2,
  Pencil,
  Play,
  ArrowRight,
  SkipForward,
  X,
  Upload,
  ArrowUp,
  ArrowDown
} from "lucide-react";
import { mockTransactions, type Transaction } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import { ImportModal } from "@/components/transactions/ImportModal";
import { useToast } from "@/hooks/use-toast";

// Helper for formatting currency
const formatCurrency = (amount: number, currency: string = "EUR") => {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: currency,
  }).format(amount);
};

export default function Dashboard() {
  const [searchTerm, setSearchTerm] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>(mockTransactions);
  const [filterType, setFilterType] = useState<"all" | "untagged">("all");
  const [reviewMode, setReviewMode] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [currentReviewIndex, setCurrentReviewIndex] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<"date" | "counterparty" | "amount" | "category" | null>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const itemsPerPage = 20;
  
  const { toast } = useToast();

  const handleSort = (column: "date" | "counterparty" | "amount" | "category") => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const handleUpdateTransaction = (id: string, updates: Partial<Transaction>) => {
    setTransactions(prev => prev.map(t => t.id === id ? { ...t, ...updates } : t));
  };

  const filteredTransactions = transactions.filter(t => {
    const matchesSearch = t.counterparty.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          (t.note && t.note.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesFilter = filterType === "all" ? true : (t.side === "debit" && !t.category);
    return matchesSearch && matchesFilter;
  });

  const sortedTransactions = [...filteredTransactions].sort((a, b) => {
    let compareResult = 0;
    
    if (sortColumn === "date") {
      compareResult = new Date(a.transaction_datetime).getTime() - new Date(b.transaction_datetime).getTime();
    } else if (sortColumn === "counterparty") {
      compareResult = a.counterparty.localeCompare(b.counterparty);
    } else if (sortColumn === "amount") {
      compareResult = a.eur_amount - b.eur_amount;
    } else if (sortColumn === "category") {
      compareResult = (a.category || "").localeCompare(b.category || "");
    }
    
    return sortDirection === "asc" ? compareResult : -compareResult;
  });

  const totalPages = Math.ceil(sortedTransactions.length / itemsPerPage);
  const startIdx = (currentPage - 1) * itemsPerPage;
  const paginatedTransactions = sortedTransactions.slice(startIdx, startIdx + itemsPerPage);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // Reset to first page on search
  };

  const handleFilterChange = (filter: "all" | "untagged") => {
    setFilterType(filter);
    setCurrentPage(1); // Reset to first page on filter change
  };

  const untaggedTransactions = transactions.filter(t => t.side === "debit" && !t.category);
  const untaggedCount = untaggedTransactions.length;

  const startReview = () => {
    if (untaggedCount > 0) {
      setCurrentReviewIndex(0);
      setReviewMode(true);
    } else {
      toast({ description: "All transactions are tagged! Great job." });
    }
  };

  const handleReviewNext = () => {
    if (currentReviewIndex < untaggedTransactions.length - 1) {
      setCurrentReviewIndex(prev => prev + 1);
    } else {
      setReviewMode(false);
      toast({ description: "Review complete!" });
    }
  };

  const currentReviewTransaction = untaggedTransactions[currentReviewIndex];

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
            <a href="#" className="transition-colors hover:text-foreground/80 text-foreground">Transactions</a>
            <a href="#" className="transition-colors hover:text-foreground/80 text-foreground/60">Analytics</a>
            <a href="#" onClick={() => setImportModalOpen(true)} className="transition-colors hover:text-foreground/80 text-foreground/60">Import</a>
          </nav>
          <div className="ml-auto flex items-center space-x-4">
            <Button size="sm" variant="outline" onClick={() => setImportModalOpen(true)}>
              <Upload className="mr-2 h-4 w-4" />
              Import
            </Button>
            <div className="h-8 w-8 rounded-full bg-secondary"></div>
          </div>
        </div>
      </header>

      <main className="container py-8 px-6">
        {/* Stats Row - Placeholder for future stats */}
        <div className="mb-8"></div>

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search transactions..."
                className="pl-9 bg-card"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
              />
            </div>
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
            <Button variant="outline" size="sm" onClick={() => setImportModalOpen(true)}>
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
          {sortedTransactions.length > 0 && (
            <div className="px-6 py-3 border-b bg-muted/20 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {startIdx + 1}–{Math.min(startIdx + itemsPerPage, sortedTransactions.length)} of {sortedTransactions.length} transactions
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="h-7 px-3"
                >
                  ← Prev
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum = currentPage > 3 ? currentPage - 2 + i : i + 1;
                    if (pageNum > totalPages) return null;
                    return (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? "secondary" : "outline"}
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
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
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
                    {sortColumn === "date" && (
                      sortDirection === "asc" ? 
                        <ArrowUp className="h-4 w-4" /> : 
                        <ArrowDown className="h-4 w-4" />
                    )}
                  </div>
                </TableHead>
                <TableHead 
                  className="w-[250px] cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("counterparty")}
                >
                  <div className="flex items-center gap-2">
                    Counterparty
                    {sortColumn === "counterparty" && (
                      sortDirection === "asc" ? 
                        <ArrowUp className="h-4 w-4" /> : 
                        <ArrowDown className="h-4 w-4" />
                    )}
                  </div>
                </TableHead>
                <TableHead 
                  className="cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("amount")}
                >
                  <div className="flex items-center gap-2">
                    Amount
                    {sortColumn === "amount" && (
                      sortDirection === "asc" ? 
                        <ArrowUp className="h-4 w-4" /> : 
                        <ArrowDown className="h-4 w-4" />
                    )}
                  </div>
                </TableHead>
                <TableHead 
                  className="w-[300px] cursor-pointer hover:bg-muted/60 select-none"
                  onClick={() => handleSort("category")}
                >
                  <div className="flex items-center gap-2">
                    Category
                    {sortColumn === "category" && (
                      sortDirection === "asc" ? 
                        <ArrowUp className="h-4 w-4" /> : 
                        <ArrowDown className="h-4 w-4" />
                    )}
                  </div>
                </TableHead>
                <TableHead className="w-[200px]">Note</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedTransactions.map((t) => (
                <TransactionRow 
                  key={t.id} 
                  transaction={t} 
                  onUpdate={(updates) => handleUpdateTransaction(t.id, updates)}
                />
              ))}
              {sortedTransactions.length === 0 && (
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

      {/* Review Mode Overlay */}
      <Dialog open={reviewMode} onOpenChange={setReviewMode}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Review Transaction</span>
              <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-1 rounded-full">
                {currentReviewIndex + 1} of {untaggedCount}
              </span>
            </DialogTitle>
          </DialogHeader>
          
          {currentReviewTransaction && (
            <div className="grid gap-6 py-4">
              <div className="flex flex-col items-center justify-center p-6 bg-muted/20 rounded-lg border border-dashed">
                <div className="text-3xl font-bold font-mono mb-1">
                  {formatCurrency(currentReviewTransaction.eur_amount)}
                </div>
                <div className="text-lg font-medium text-center">{currentReviewTransaction.counterparty}</div>
                <div className="text-xs text-muted-foreground mt-2">
                  {format(new Date(currentReviewTransaction.transaction_datetime), "dd MMM yyyy • HH:mm")} • {currentReviewTransaction.source}
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Category</label>
                  <CategorySelector 
                    category={currentReviewTransaction.category}
                    onSelect={(cat) => {
                      handleUpdateTransaction(currentReviewTransaction.id, { 
                        category: cat
                      });
                    }}
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium">Note</label>
                  <Textarea 
                    placeholder="Add a note..." 
                    className="h-20 resize-none"
                    value={currentReviewTransaction.note || ""}
                    onChange={(e) => handleUpdateTransaction(currentReviewTransaction.id, { note: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}

          <DialogFooter className="flex-row justify-between sm:justify-between">
             <Button variant="ghost" onClick={handleReviewNext} className="text-muted-foreground">
               <SkipForward className="mr-2 h-4 w-4" /> Skip
             </Button>
             <Button onClick={handleReviewNext}>
               Next <ArrowRight className="ml-2 h-4 w-4" />
             </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ImportModal open={importModalOpen} onOpenChange={setImportModalOpen} />
    </div>
  );
}

interface TransactionRowProps {
  transaction: Transaction;
  onUpdate: (updates: Partial<Transaction>) => void;
}

function TransactionRow({ transaction, onUpdate }: TransactionRowProps) {
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
        <div className="text-[10px] opacity-60">{format(new Date(transaction.transaction_datetime), "HH:mm")}</div>
      </TableCell>
      <TableCell>
        <div className="font-medium text-sm">{transaction.counterparty}</div>
      </TableCell>
      <TableCell>
        <div className={cn(
          "font-mono font-medium",
          transaction.side === "credit" ? "text-emerald-600 dark:text-emerald-400" : ""
        )}>
          {transaction.side === "debit" ? "-" : "+"}{formatCurrency(transaction.eur_amount)}
        </div>
        {transaction.orig_currency !== "EUR" && (
          <div className="text-xs text-muted-foreground font-mono">
            {transaction.orig_amount.toFixed(2)} {transaction.orig_currency}
          </div>
        )}
      </TableCell>
      <TableCell>
        <div className="w-full max-w-[280px]">
          <CategorySelector 
            category={transaction.category}
            onSelect={(cat) => onUpdate({ category: cat })}
          />
        </div>
      </TableCell>
      <TableCell>
        <Popover open={noteOpen} onOpenChange={setNoteOpen}>
          <PopoverTrigger asChild>
            <div className="cursor-pointer min-h-[32px] flex items-center group/note">
              {transaction.note ? (
                <span className="text-sm text-muted-foreground truncate max-w-[150px] block" title={transaction.note}>
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
                <p className="text-sm text-muted-foreground">Add details about this transaction.</p>
              </div>
              <Textarea 
                value={noteTemp} 
                onChange={(e) => setNoteTemp(e.target.value)} 
                placeholder="e.g. Dinner with clients..."
                className="h-24 resize-none"
              />
              <Button size="sm" onClick={handleSaveNote}>Save Note</Button>
            </div>
          </PopoverContent>
        </Popover>
      </TableCell>
      <TableCell>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
}
