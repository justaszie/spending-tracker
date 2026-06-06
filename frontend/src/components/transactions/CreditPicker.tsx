import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { formatCompactTransaction } from "@/lib/transactions";
import { useTransactions } from "@/hooks/transactions/use-transactions";
import type { Transaction } from "@/types/transactions";

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;
const MIN_SEARCH_LENGTH = 2;

interface CreditPickerProps {
  selectedId: string | null;
  onSelect: (credit: Transaction) => void;
}

export function CreditPicker({ selectedId, onSelect }: CreditPickerProps) {
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS);
  const effectiveSearch =
    debouncedSearch.trim().length >= MIN_SEARCH_LENGTH
      ? debouncedSearch.trim()
      : "";

  const [page, setPage] = useState(1);
  const [accumulated, setAccumulated] = useState<Transaction[]>([]);

  useEffect(() => {
    setPage(1);
    setAccumulated([]);
  }, [effectiveSearch]);

  const query = useTransactions({
    side: ["credit"],
    search: effectiveSearch || undefined,
    page,
    size: PAGE_SIZE,
    sortBy: "transaction_datetime",
    sortOrder: "desc",
  });

  useEffect(() => {
    const pageTxs = query.data?.transactions;
    if (!pageTxs) return;
    if (page === 1) {
      setAccumulated(pageTxs);
      return;
    }
    setAccumulated((prev) => {
      const seen = new Set(prev.map((t) => t.id));
      const novel = pageTxs.filter((t) => !seen.has(t.id));
      return novel.length === 0 ? prev : [...prev, ...novel];
    });
  }, [query.data, page]);

  const total = query.data?.total ?? 0;
  const hasMore = accumulated.length < total;
  const isFiltering = effectiveSearch !== "";
  const isInitialLoading = query.isLoading && accumulated.length === 0;
  const isFetchingMore = query.isFetching && page > 1;

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search by counterparty, note, or category"
          className="pl-9"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      <ScrollArea className="h-64 rounded-md border">
        {isInitialLoading ? (
          <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
            <Spinner className="mr-2 size-4" />
            Loading credits…
          </div>
        ) : accumulated.length === 0 ? (
          <EmptyMessage isFiltering={isFiltering} />
        ) : (
          <ul className="divide-y">
            {accumulated.map((credit) => (
              <CreditRow
                key={credit.id}
                credit={credit}
                selected={credit.id === selectedId}
                onSelect={() => onSelect(credit)}
              />
            ))}
            {hasMore && (
              <li className="p-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={isFetchingMore}
                >
                  {isFetchingMore && <Spinner className="mr-2 size-4" />}
                  Load more
                </Button>
              </li>
            )}
          </ul>
        )}
      </ScrollArea>
    </div>
  );
}

function EmptyMessage({ isFiltering }: { isFiltering: boolean }) {
  return (
    <div className="flex h-64 items-center justify-center px-6 text-center text-sm text-muted-foreground">
      {isFiltering
        ? "No credits match your search."
        : "You don't have any credit transactions yet. Import a statement or add one manually first."}
    </div>
  );
}

function CreditRow({
  credit,
  selected,
  onSelect,
}: {
  credit: Transaction;
  selected: boolean;
  onSelect: () => void;
}) {
  const { primary, secondary } = formatCompactTransaction(credit);
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className={cn(
          "flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left transition-colors hover:bg-muted/50",
          selected && "bg-accent text-accent-foreground hover:bg-accent",
        )}
      >
        <span className="text-sm font-medium">{primary}</span>
        <span
          className={cn(
            "text-xs",
            selected ? "text-accent-foreground/80" : "text-muted-foreground",
          )}
        >
          {secondary}
        </span>
      </button>
    </li>
  );
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}
