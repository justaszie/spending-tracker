import { Card, CardContent } from "@/components/ui/card";

const STATIC_DATA = {
  avgDaily: 27.07,
  overDays: 18,
};

export function AvgDailySpendCard() {
  const { avgDaily, overDays } = STATIC_DATA;

  return (
    <Card className="h-full">
      <CardContent className="p-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-sm font-medium text-foreground/80">Average daily spending</span>
        </div>
        <p className="mb-2 text-3xl font-mono font-semibold md:text-4xl">
          €{avgDaily.toLocaleString("de-DE", { minimumFractionDigits: 2 })}
        </p>
        <p className="text-sm text-muted-foreground">Per day over {overDays} days</p>
      </CardContent>
    </Card>
  );
}
