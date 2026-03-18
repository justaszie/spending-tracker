import type { ReactNode } from "react";
import { useState } from "react";
import { useLocation } from "wouter";
import { queryClient } from "@/lib/queryClient";
import { AppHeader } from "@/components/layout/AppHeader";
import { ImportModal } from "@/components/transactions/ImportModal";

type AppLayoutProps = {
  children: ReactNode;
};

export function AppLayout({ children }: AppLayoutProps) {
  const [, setLocation] = useLocation();
  const [importModalOpen, setImportModalOpen] = useState(false);

  const handleViewTransactions = () => {
    queryClient.invalidateQueries({ queryKey: ["transactions"] });
    setImportModalOpen(false);
    setLocation("/transactions");
  };

  return (
    <div className="container mx-auto min-h-screen bg-background text-foreground font-sans selection:bg-primary/10">
      <AppHeader setImportModalOpen={setImportModalOpen} />
      {children}
      <ImportModal
        open={importModalOpen}
        onOpenChange={setImportModalOpen}
        onViewTransactions={handleViewTransactions}
      />
    </div>
  );
}

