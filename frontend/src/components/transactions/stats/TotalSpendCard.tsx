import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";

const STATIC_DATA = {
  total: 487.32,
  changePercent: 12.4,
  changeDirection: "up" as "up" | "down",
  previousAmount: 433.56,
  previousPeriodLabel: "Feb 1 – Feb 18",
};

export function TotalSpendCard() {
  const {
    total,
    changePercent,
    changeDirection,
    previousAmount,
    previousPeriodLabel,
  } = STATIC_DATA;

  const isUp = changeDirection === "up";

  return (
    <Card className="h-full">
      <CardContent className="p-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-sm font-medium text-foreground/80">Total spending</span>
        </div>
        <p className="mb-2 text-3xl font-mono font-semibold md:text-4xl">
          €{total.toLocaleString("de-DE", { minimumFractionDigits: 2 })}
        </p>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-sm">
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
              {isUp ? "+" : "-"}
              {changePercent.toLocaleString("de-DE", {
                minimumFractionDigits: 1,
              })}
              %
            </span>
            <span className="font-mono font-medium text-foreground/70">
              €
              {previousAmount.toLocaleString("de-DE", {
                minimumFractionDigits: 2,
              })}{" "}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">vs previous period</span>
            <span className="text-muted-foreground">{previousPeriodLabel}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
