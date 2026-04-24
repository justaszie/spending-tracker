import { Card, CardContent } from "@/components/ui/card";

type AvgDailySpendCardProps = {
  avgDaily: number;
  overDays: number;
  isLoading?: boolean;
};

export function AvgDailySpendCard({
  avgDaily,
  overDays,
  isLoading = false,
}: AvgDailySpendCardProps) {
  return (
    <Card className="h-full">
      <CardContent className="p-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-sm font-medium text-foreground/80">Average daily spending</span>
        </div>
        <p className="mb-2 text-3xl font-mono font-semibold md:text-4xl">
          {isLoading
            ? "—"
            : `€${avgDaily.toLocaleString("de-DE", { minimumFractionDigits: 2 })}`}
        </p>
        <p className="text-sm text-muted-foreground">
          {isLoading ? "Loading period..." : `Per day over ${overDays} days`}
        </p>
      </CardContent>
    </Card>
  );
}
