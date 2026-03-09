import { useState, useEffect } from "react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { 
  Upload, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Building2, 
  FileText,
  ArrowRight,
  ExternalLink
} from "lucide-react";
import { cn } from "@/lib/utils";

type JobStatus = "pending" | "running" | "completed" | "failed";

interface ImportJob {
  id: string;
  status: JobStatus;
  imported: number;
  duplicate: number;
  error?: string;
}

interface ImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SUPPORTED_BANKS = [
  { id: "sparkasse", name: "Sparkasse", icon: "S" },
  { id: "revolut", name: "Revolut", icon: "R" },
  { id: "amex", name: "American Express", icon: "A" },
  { id: "paypal", name: "PayPal", icon: "P" },
];

export function ImportModal({ open, onOpenChange }: ImportModalProps) {
  const [step, setStep] = useState<"select" | "uploading" | "processing" | "result">("select");
  const [selectedBank, setSelectedBank] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [job, setJob] = useState<ImportJob | null>(null);

  // Simulate file upload
  const handleUpload = () => {
    if (!selectedBank) return;
    setStep("uploading");
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      setUploadProgress(progress);
      if (progress >= 100) {
        clearInterval(interval);
        startProcessing();
      }
    }, 150);
  };

  // Simulate background processing
  const startProcessing = () => {
    setStep("processing");
    setJob({ id: crypto.randomUUID(), status: "pending", imported: 0, duplicate: 0 });

    // Status transition simulation
    setTimeout(() => {
      setJob(prev => prev ? { ...prev, status: "running" } : null);
    }, 1000);

    setTimeout(() => {
      setJob(prev => prev ? { 
        ...prev, 
        status: "completed", 
        imported: Math.floor(Math.random() * 45) + 5, 
        duplicate: Math.floor(Math.random() * 10) 
      } : null);
      setStep("result");
    }, 4000);
  };

  const reset = () => {
    setStep("select");
    setSelectedBank("");
    setUploadProgress(0);
    setJob(null);
  };

  return (
    <Dialog open={open} onOpenChange={(val) => {
      onOpenChange(val);
      if (!val) setTimeout(reset, 300);
    }}>
      <DialogContent className="sm:max-w-[440px] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Import Bank Statement</DialogTitle>
          <DialogDescription>
            Upload your statement PDF or CSV to import transactions.
          </DialogDescription>
        </DialogHeader>

        <div className="py-6 min-h-[280px] flex flex-col justify-center">
          {step === "select" && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
              <div className="space-y-3">
                <label className="text-sm font-medium">1. Select your bank</label>
                <div className="grid grid-cols-2 gap-3">
                  {SUPPORTED_BANKS.map((bank) => (
                    <button
                      key={bank.id}
                      onClick={() => setSelectedBank(bank.id)}
                      className={cn(
                        "flex items-center gap-3 p-3 rounded-xl border text-left transition-all hover:bg-muted/50",
                        selectedBank === bank.id ? "border-primary bg-primary/5 ring-1 ring-primary" : "bg-card"
                      )}
                    >
                      <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center font-bold text-xs text-muted-foreground">
                        {bank.icon}
                      </div>
                      <span className="text-sm font-medium">{bank.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-medium">2. Choose file</label>
                <div 
                  className={cn(
                    "border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-2 cursor-pointer hover:bg-muted/30 transition-colors",
                    selectedBank ? "opacity-100" : "opacity-40 pointer-events-none"
                  )}
                  onClick={handleUpload}
                >
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <Upload className="h-5 w-5 text-primary" />
                  </div>
                  <div className="text-sm font-medium text-center">
                    Click to browse or drag and drop
                  </div>
                  <div className="text-xs text-muted-foreground">PDF, CSV or TXT (Max 10MB)</div>
                </div>
              </div>
            </div>
          )}

          {step === "uploading" && (
            <div className="space-y-6 text-center animate-in fade-in duration-300">
              <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-foreground">Uploading statement...</h3>
                <p className="text-sm text-muted-foreground">Securely transferring to cloud storage</p>
              </div>
              <div className="space-y-2">
                <Progress value={uploadProgress} className="h-2" />
                <p className="text-xs font-mono text-muted-foreground">{uploadProgress}%</p>
              </div>
            </div>
          )}

          {step === "processing" && (
            <div className="space-y-6 text-center animate-in fade-in duration-300">
              <div className="relative mx-auto h-20 w-20">
                <div className="absolute inset-0 rounded-full border-4 border-primary/20"></div>
                <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <Building2 className="h-8 w-8 text-primary/60" />
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-foreground">
                  {job?.status === "pending" ? "Scheduling import..." : "Parsing transactions..."}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Our background worker is processing your statement
                </p>
              </div>
              <div className="flex items-center justify-center gap-2 text-xs font-mono text-muted-foreground bg-muted/50 py-2 px-4 rounded-full w-fit mx-auto border">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                Job ID: {job?.id.slice(0, 8)}...
              </div>
            </div>
          )}

          {step === "result" && (
            <div className="space-y-6 text-center animate-in zoom-in-95 duration-500">
              <div className="h-16 w-16 bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center mx-auto mb-4 border border-emerald-200 dark:border-emerald-800">
                <CheckCircle2 className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-foreground">Import Successful</h3>
                <p className="text-sm text-muted-foreground">Your statement has been processed.</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 py-4 border-y">
                <div className="space-y-1">
                  <div className="text-2xl font-bold font-mono text-emerald-600">{job?.imported}</div>
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Imported</div>
                </div>
                <div className="space-y-1 border-l">
                  <div className="text-2xl font-bold font-mono text-amber-600">{job?.duplicate}</div>
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Duplicates</div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <Button className="w-full" onClick={() => onOpenChange(false)}>
                  Go to Transactions
                </Button>
                <Button variant="ghost" className="w-full text-xs" onClick={reset}>
                  Import another statement
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
