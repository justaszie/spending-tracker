import { useState } from "react";
import {
  GetTransactionsParams,
  PeriodPreset,
  TransactionUpdatePayload,
} from "@/types/transactions";
import { useTransactions } from "@/hooks/transactions/use-transactions";
import { useSpendingCategories } from "@/hooks/transactions/use-spending-cateogries";
import { useUpdateTransaction } from "@/hooks/transactions/use-update-transaction";
import { useTransactionsStats } from "@/hooks/transactions/use-transactions-stats";
import { TransactionSearch } from "@/components/transactions/TransactionSearch";
import { UntaggedReviewBanner } from "@/components/transactions/UntaggedReviewBanner";
import { TotalSpendCard } from "@/components/transactions/stats/TotalSpendCard";
import { AvgDailySpendCard } from "@/components/transactions/stats/AvgDailySpendCard";
import { TopCategoriesCard } from "@/components/transactions/stats/TopCategoriesCard";
import ErrorPage from "@/pages/error";
import { FullScreenLoader } from "@/components/FullScreenLoader";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  SortableField,
  TransactionsTable,
} from "@/components/transactions/TransactionsTable";

export default function TransactionsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<SortableField | null>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodPreset>("MTD");

  const itemsPerPage = 50;
  const periodOptions: ReadonlyArray<{ key: PeriodPreset; label: string }> = [
    { key: "MTD", label: "This Month" },
    { key: "L30", label: "Last 30 Days" },
    { key: "YTD", label: "This Year" },
    { key: "ALL_TIME", label: "All Time" },
  ];

  // Builds a UI-friendly header label for currently selected period in the stats.
  const buildPeriodLabel = (selectedPeriod: PeriodPreset): string => {
    const today = new Date();

    switch (selectedPeriod) {
      case "MTD":
        return `${today.toLocaleString("en-US", {
          month: "long",
          year: "numeric",
        })} - Month to Date`;
      case "L30": {
        const startDate = new Date(today);
        startDate.setDate(today.getDate() - 29);

        const isSameYear = startDate.getFullYear() === today.getFullYear();

        if (isSameYear) {
          const startLabel = startDate.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          });
          const endLabel = today.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          });

          return `${startLabel} – ${endLabel} — Last 30 Days`;
        }

        const formatWithYear = (date: Date) =>
          date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          });

        return `${formatWithYear(startDate)} – ${formatWithYear(today)} — Last 30 Days`;
      }
      case "YTD":
        return `${today.getFullYear()} - Year to Date`;
      case "ALL_TIME":
        return "All Time";
      default:
        return "Custom dates";
    }
  };
  const selectedPeriodLabel = buildPeriodLabel(selectedPeriod);

  const statsParams = {
    period: selectedPeriod,
    // dateFrom: "2026-01-10",
    // dateTo: "2026-01-20",
    includePrevious: true,
  };

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
  const { data: statsData, isLoading: statsLoading } =
    useTransactionsStats(statsParams);
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

  const toNumber = (value: number | string | null | undefined): number => {
    if (typeof value === "number") return value;
    if (typeof value === "string") return Number(value);
    return 0;
  };

  const currentSpendGroup = statsData?.current_period?.groups?.spend;
  const previousSpendGroup = statsData?.previous_period?.groups?.spend;
  const spendDeltas = statsData?.deltas?.groups?.spend;

  const totalSpend = toNumber(currentSpendGroup?.total);
  const avgDailySpend = toNumber(currentSpendGroup?.avg_daily);
  const periodDaysCount = statsData?.current_period?.days_count ?? 0;
  const previousTotalSpend = previousSpendGroup
    ? toNumber(previousSpendGroup.total)
    : null;
  const totalDeltaPct =
    spendDeltas?.total?.pct_change === null ||
    spendDeltas?.total?.pct_change === undefined
      ? null
      : toNumber(spendDeltas.total.pct_change);
  const previousPeriodLabel =
    statsData?.previous_period?.date_from && statsData?.previous_period?.date_to
      ? `${statsData.previous_period.date_from} - ${statsData.previous_period.date_to}`
      : null;

  const categorySpending = currentSpendGroup?.by_category ?? [];
  let topCategories = categorySpending
    .sort((t1, t2) => Number(t2.total) - Number(t1.total))
    .slice(0, 6)
    .map((cat) => ({
      name: cat.category ?? "Uncategorized",
      amount: toNumber(cat.total),
    }));
  // If there are > 5 categories in the stats, we lump other categories into "Remaining"
  if (categorySpending.length > 5) {
    const remainingTotal = categorySpending
      .slice(6)
      .reduce((total, cat) => total + toNumber(cat.total), 0);

      topCategories.push({
      name: "Other categories",
      amount: remainingTotal,
    });
  }

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

      {/* Only display stats row if there are transactions */}
      {transactions.length > 0 && (
        <>
          <header className="mb-4">
            <h1 className="text-xl font-semibold tracking-tight">Spending Overview</h1>
          </header>

          <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              {selectedPeriodLabel}
            </p>
            {/* Static for now; later this selection will drive stats query params. */}
            <Tabs
              value={selectedPeriod}
              onValueChange={(value) => setSelectedPeriod(value as PeriodPreset)}
              className="w-full md:w-auto"
            >
              <TabsList className="grid h-auto w-full grid-cols-2 gap-1 md:w-auto md:grid-cols-4">
                {periodOptions.map((option) => (
                  <TabsTrigger
                    key={option.key}
                    value={option.key}
                    className="px-4 py-2"
                  >
                    {option.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          <div className="mb-6 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-12">
            <div className="xl:col-span-3">
              <TotalSpendCard
                total={totalSpend}
                changePercent={totalDeltaPct}
                previousAmount={previousTotalSpend}
                previousPeriodLabel={previousPeriodLabel}
                isLoading={statsLoading && !statsData}
              />
            </div>
            <div className="xl:col-span-3">
              <AvgDailySpendCard
                avgDaily={avgDailySpend}
                overDays={periodDaysCount}
                isLoading={statsLoading && !statsData}
              />
            </div>
            <div className="md:col-span-2 xl:col-span-6">
              <TopCategoriesCard
                total={totalSpend}
                categories={topCategories}
                isLoading={statsLoading && !statsData}
              />
            </div>
          </div>
        </>
      )}

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
