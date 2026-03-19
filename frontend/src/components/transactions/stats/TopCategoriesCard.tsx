import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Sector } from "recharts";
import { Card, CardContent } from "@/components/ui/card";

const STATIC_DATA = {
  total: 487,
  categories: [
    { name: "Groceries", amount: 185.18, color: "#22c55e" },
    { name: "Cafe & Snacks", amount: 87.72, color: "#3b82f6" },
    { name: "Food Delivery", amount: 73.1, color: "#f97316" },
    { name: "Transport", amount: 58.48, color: "#a855f7" },
    { name: "Entertainment", amount: 43.9, color: "#ef4444" },
    { name: "Remaining", amount: 38.94, color: "#9ca3af" },
  ],
};

export function TopCategoriesCard() {
  const { total, categories } = STATIC_DATA;
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const formatAmount = (value: number) =>
    `€${value.toLocaleString("de-DE", { minimumFractionDigits: 2 })}`;

  return (
    <Card className="h-full">
      <CardContent className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm font-medium text-foreground/80">Top categories</span>
        </div>
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <div className="relative mx-auto h-40 w-40 shrink-0 sm:mx-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categories}
                  cx="50%"
                  cy="50%"
                  innerRadius={46}
                  outerRadius={68}
                  dataKey="amount"
                  strokeWidth={2}
                  stroke="var(--background)"
                  rootTabIndex={-1}
                  activeIndex={activeIndex}
                  onClick={(_, index) =>
                    setActiveIndex((current) => (current === index ? undefined : index))
                  }
                  activeShape={(props: any) => (
                    <Sector
                      {...props}
                      outerRadius={(props.outerRadius ?? 68) + 3}
                      stroke="hsl(var(--ring) / 0.45)"
                      strokeWidth={2}
                      style={{
                        outline: "none",
                        filter: "drop-shadow(0 1px 3px rgb(0 0 0 / 0.18))",
                      }}
                    />
                  )}
                >
                  {categories.map((entry, index) => (
                    <Cell key={index} fill={entry.color} style={{ outline: "none" }} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-base font-mono font-semibold leading-none">€{total}</span>
              <span className="text-xs text-muted-foreground mt-0.5">TOTAL</span>
            </div>
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            {categories.map((cat) => (
              <div key={cat.name} className="flex items-center justify-between gap-3 text-sm">
                <div className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: cat.color }}
                  />
                  <span className="truncate text-foreground/85">{cat.name}</span>
                </div>
                <span className="shrink-0 font-mono text-foreground/75">
                  {formatAmount(cat.amount)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
