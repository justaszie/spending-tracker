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
import { ApiError } from "@/lib/api";
import { formatCompactTransaction } from "@/lib/transactions";
import { toast } from "@/hooks/use-toast";
import { useCreateReimbursement } from "@/hooks/reimbursements/use-create-reimbursement";
import { CreditPicker } from "@/components/transactions/CreditPicker";
import type { Transaction } from "@/types/transactions";

interface ReimbursementModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  debit: Transaction | null;
}

export function ReimbursementModal({
  open,
  onOpenChange,
  debit,
}: ReimbursementModalProps) {
  const [selectedCredit, setSelectedCredit] = useState<Transaction | null>(
    null,
  );
  const [amount, setAmount] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createReimbursement = useCreateReimbursement();

  useEffect(() => {
    if (!open) {
      setSelectedCredit(null);
      setAmount("");
      setErrorMessage(null);
      createReimbursement.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const currencySuffix = selectedCredit?.orig_currency ?? "";
  const amountNumber = Number.parseFloat(amount);
  const canSubmit =
    Boolean(selectedCredit) &&
    Number.isFinite(amountNumber) &&
    amountNumber > 0 &&
    !createReimbursement.isPending;

  const handleCreditSelect = (credit: Transaction) => {
    if (!debit) return;
    setSelectedCredit(credit);
    const debitOrig = Number(debit.orig_amount);
    const creditOrig = Number(credit.orig_amount);
    const defaultAmount =
      credit.orig_currency === debit.orig_currency
        ? Math.min(creditOrig, debitOrig)
        : creditOrig;
    setAmount(String(defaultAmount));
  };

  const handleSubmit = () => {
    if (!debit || !selectedCredit || !canSubmit) return;
    setErrorMessage(null);
    createReimbursement.mutate(
      {
        debit_txn_id: debit.id,
        credit_txn_id: selectedCredit.id,
        orig_reimbursed_amount: amountNumber,
      },
      {
        onSuccess: () => {
          toast({ title: "Reimbursement added" });
          onOpenChange(false);
        },
        onError: (error) => {
          if (error instanceof ApiError) {
            setErrorMessage(error.message);
          } else {
            setErrorMessage(
              error instanceof Error
                ? error.message
                : "Failed to add reimbursement",
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
          <DialogTitle>Add reimbursement</DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Reimbursing
            </div>
            {debit && <DebitSummaryCard debit={debit} />}
          </section>

          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Reimbursed by
            </div>
            <CreditPicker
              selectedId={selectedCredit?.id ?? null}
              onSelect={handleCreditSelect}
            />
          </section>

          <section className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Reimbursed amount
            </div>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                disabled={!selectedCredit}
              />
              <span className="text-sm font-medium text-muted-foreground min-w-[3rem]">
                {currencySuffix || "—"}
              </span>
            </div>
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
            disabled={createReimbursement.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {createReimbursement.isPending && (
              <Spinner className="mr-2 size-4" />
            )}
            Add
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DebitSummaryCard({ debit }: { debit: Transaction }) {
  const { primary, secondary } = formatCompactTransaction(debit);
  return (
    <div className="rounded-lg border bg-muted/30 px-3 py-2">
      <div className="text-sm font-medium">{primary}</div>
      <div className="text-xs text-muted-foreground">{secondary}</div>
    </div>
  );
}
