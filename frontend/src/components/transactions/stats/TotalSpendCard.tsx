import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";

type TotalSpendCardProps = {
  total: number;
  changePercent: number | null;
  previousAmount: number | null;
  previousPeriodLabel: string | null;
  isLoading?: boolean;
};

export function TotalSpendCard({
  total,
  changePercent,
  previousAmount,
  previousPeriodLabel,
  isLoading = false,
}: TotalSpendCardProps) {
  const isUp = (changePercent ?? 0) > 0;

  return (
    <Card className="h-full">
      <CardContent className="p-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-sm font-medium text-foreground/80">
            Total spending
          </span>
        </div>
        <p className="mb-2 text-3xl font-mono font-semibold md:text-4xl">
          {isLoading
            ? "—"
            : `€${total.toLocaleString("de-DE", { minimumFractionDigits: 2 })}`}
        </p>
        {total === 0.0 ? (
          <p className="text-sm text-muted-foreground">
            No spending in this period
          </p>
        ) : previousPeriodLabel !== null ? (
          previousAmount === 0 ? (
            <div className="flex items-center justify-between">
               <span className="text-sm text-muted-foreground">
                No spending in previous period
              </span>
              <span className="text-xs text-muted-foreground">
                  {previousPeriodLabel ?? "—"}
              </span>
            </div>

          ) : (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-sm">
                {isLoading || changePercent === null ? (
                  <span className="font-medium text-muted-foreground">
                    + N/A %
                  </span>
                ) : (
                  <span
                    className={`flex items-center gap-1 font-semibold ${
                      isUp ? "text-red-500" : "text-green-500"
                    }`}
                  >
                    {isUp ? (
                      <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    {isUp ? "+" : ""}
                    {changePercent.toLocaleString("de-DE", {
                      minimumFractionDigits: 1,
                    })}
                    %
                  </span>
                )}
                <span className="font-mono font-medium text-foreground/70">
                  {isLoading || previousAmount === null
                    ? "—"
                    : `€${previousAmount.toLocaleString("de-DE", {
                        minimumFractionDigits: 2,
                      })}`}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">vs previous period</span>
                <span className="text-muted-foreground">
                  {previousPeriodLabel ?? "—"}
                </span>
              </div>
            </div>
          )
        ) : ""}
      </CardContent>
    </Card>
  );
}
