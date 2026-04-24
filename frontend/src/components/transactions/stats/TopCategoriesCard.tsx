import { PieChart, Pie, Cell, Label } from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { getCategoryLabel } from "@/config/categories";

type TopCategory = {
  name: string;
  amount: number;
};

type TopCategoriesCardProps = {
  total: number;
  categories: TopCategory[];
  isLoading?: boolean;
};

const CATEGORY_COLORS = [
  "#22c55e",
  "#3b82f6",
  "#f97316",
  "#a855f7",
  "#ef4444",
  "#14b8a6",
];
const REMAINING_COLOR = "#9ca3af";

export function TopCategoriesCard({
  total,
  categories,
  isLoading = false,
}: TopCategoriesCardProps) {
  const formatAmount = (value: number) =>
    `€${value.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const chartData = categories.map((category, index) => ({
    name: getCategoryLabel(category.name),
    amount: category.amount,
    fill: CATEGORY_COLORS[index],
  }));
  let remainingCategory = chartData.find((cat) => cat.name == "Other categories");
  if (remainingCategory) {
    remainingCategory.fill = REMAINING_COLOR;
  }
  const hasData = chartData.length > 0;

  return (
    <Card className="h-full">
      <CardContent className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm font-medium text-foreground/80">
            Top categories
          </span>
        </div>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading categories...</p>
        ) : !hasData ? (
          <p className="text-sm text-muted-foreground">
            No spending in this period
          </p>
        ) : (
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
            <div className="relative mx-auto h-40 w-40 shrink-0 sm:mx-0">
              <PieChart responsive style={{ width: "100%", height: "100%" }}>
                <Pie
                  data={chartData}
                  dataKey="amount"
                  innerRadius="60%"
                  outerRadius="80%"
                ></Pie>
                <Label
                  position="center"
                  value={isLoading ? "—" : formatAmount(total)}
                  fill="hsl(var(--foreground))"
                  style={{
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                />
              </PieChart>
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              {chartData.map((cat) => (
                <div
                  key={cat.name}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: cat.fill }}
                    />
                    <span className="truncate text-foreground/85">
                      {cat.name}
                    </span>
                  </div>
                  <span className="shrink-0 font-mono text-foreground/75">
                    {formatAmount(cat.amount)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
