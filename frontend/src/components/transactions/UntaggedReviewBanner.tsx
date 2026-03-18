import { useEffect, useMemo, useState } from "react";
import { Link } from "wouter";
import { AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function UntaggedReviewBanner({
  untaggedDebitCount,
  refreshedAt,
}: {
  untaggedDebitCount: number;
  refreshedAt: number;
}) {
  const [dismissed, setDismissed] = useState(false);
  const shouldShow = useMemo(() => {
    if (untaggedDebitCount <= 0) return false;
    return !dismissed;
  }, [dismissed, untaggedDebitCount]);

  useEffect(() => {
    setDismissed(false);
  }, [refreshedAt, untaggedDebitCount]);

  if (!shouldShow) return null;

  return (
    <div className="mb-6 rounded-lg border border-amber-600/20 bg-amber-600/10 px-2 py-2 text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-50">
      <div className="flex items-center gap-1">
        <div className="flex h-7 w-7 items-center justify-center rounded-full text-amber-600 dark:text-amber-200">
          <AlertCircle className="h-4 w-4" />
        </div>
        <div className="flex-1 text-sm text-muted-foreground">
          You have{" "}
          <span className="font-semibold text-amber-600 dark:text-amber-200">
            {untaggedDebitCount}
          </span>{" "}
          untagged debit transaction{untaggedDebitCount === 1 ? "" : "s"} that need a spending category.{" "}
          <Button
            asChild
            variant="link"
            className="h-auto p-0 align-baseline font-semibold text-amber-600 underline underline-offset-2 hover:text-amber-800 dark:text-amber-200 dark:hover:text-amber-100"
          >
            <Link href="/review">Review now</Link>
          </Button>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 -mt-1 text-amber-900/70 dark:text-amber-100/70"
          onClick={() => {
            setDismissed(true);
          }}
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

