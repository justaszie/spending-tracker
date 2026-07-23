import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { useCreateTransaction } from "@/hooks/transactions/use-create-transaction";
import { useSpendingCategories } from "@/hooks/transactions/use-spending-cateogries";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import type {
  TransactionSide,
  TransactionType,
} from "@/types/transactions";

interface CreateTransactionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const TRANSACTION_TYPE_LABELS: Record<TransactionType, string> = {
  card_payment: "Card payment",
  cash_withdrawal: "Cash withdrawal",
  cash_payment: "Cash payment",
  transfer: "Transfer",
  card_refund: "Card refund",
  other: "Other",
};

// Local-timezone YYYY-MM-DD (toISOString would shift near midnight)
function todayLocalISODate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

export function CreateTransactionModal({
  open,
  onOpenChange,
}: CreateTransactionModalProps) {
  const [date, setDate] = useState<string>(todayLocalISODate());
  const [counterparty, setCounterparty] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [side, setSide] = useState<TransactionSide>("debit");
  const [type, setType] = useState<TransactionType>("cash_payment");
  const [category, setCategory] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createTransaction = useCreateTransaction();
  const { data: spendingCategories } = useSpendingCategories();

  useEffect(() => {
    if (!open) {
      setDate(todayLocalISODate());
      setCounterparty("");
      setAmount("");
      setCurrency("EUR");
      setSide("debit");
      setType("cash_payment");
      setCategory(null);
      setNote("");
      setErrorMessage(null);
      createTransaction.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const today = todayLocalISODate();
  const amountNumber = Number.parseFloat(amount);
  const canSubmit =
    Boolean(date) &&
    date <= today &&
    counterparty.trim().length > 0 &&
    Number.isFinite(amountNumber) &&
    amountNumber > 0 &&
    currency.trim().length > 0 &&
    !createTransaction.isPending;

  const handleSubmit = () => {
    if (!canSubmit) return;
    setErrorMessage(null);
    createTransaction.mutate(
      {
        // Noon keeps manual transactions sorted mid-day among imported ones
        transaction_datetime: `${date}T12:00:00`,
        counterparty: counterparty.trim(),
        orig_amount: amountNumber,
        orig_currency: currency.trim().toUpperCase(),
        side,
        type,
        spending_category: category,
        note: note.trim() || null,
      },
      {
        onSuccess: () => {
          toast({ title: "Transaction added" });
          onOpenChange(false);
        },
        onError: (error) => {
          if (error instanceof ApiError) {
            setErrorMessage(error.message);
          } else {
            setErrorMessage(
              error instanceof Error
                ? error.message
                : "Failed to add transaction",
            );
          }
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Add transaction</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <section className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Date
              </div>
              <Input
                type="date"
                value={date}
                max={today}
                onChange={(e) => setDate(e.target.value)}
              />
            </section>

            <section className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Side
              </div>
              <Tabs
                value={side}
                onValueChange={(value) => setSide(value as TransactionSide)}
              >
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="debit">Debit</TabsTrigger>
                  <TabsTrigger value="credit">Credit</TabsTrigger>
                </TabsList>
              </Tabs>
            </section>
          </div>

          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Counterparty
            </div>
            <Input
              value={counterparty}
              onChange={(e) => setCounterparty(e.target.value)}
              placeholder="Who was paid, or who paid you"
            />
          </section>

          <div className="grid grid-cols-[1fr_6rem] gap-3">
            <section className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Amount
              </div>
              <Input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
              />
            </section>

            <section className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Currency
              </div>
              <Input
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                maxLength={3}
                placeholder="EUR"
              />
            </section>
          </div>

          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Type
            </div>
            <Select
              value={type}
              onValueChange={(value) => setType(value as TransactionType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(TRANSACTION_TYPE_LABELS).map(
                  ([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </section>

          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Category
            </div>
            <CategorySelector
              category={category}
              existing={spendingCategories ?? []}
              onSelect={setCategory}
            />
          </section>

          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Note
            </div>
            <Input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Optional note"
            />
          </section>

          {errorMessage && (
            <Alert variant="destructive">
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createTransaction.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {createTransaction.isPending && <Spinner className="mr-2 size-4" />}
            Add
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}