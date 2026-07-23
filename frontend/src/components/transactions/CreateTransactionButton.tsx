import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CreateTransactionModal } from "@/components/transactions/CreateTransactionModal";

export function CreateTransactionButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="mr-2 h-4 w-4" />
        Add Transaction
      </Button>
      <CreateTransactionModal open={open} onOpenChange={setOpen} />
    </>
  );
}