import { useState, useEffect, useRef } from "react";
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
import { ApiError, statementImportAPI } from "@/lib/api";
import type { ImportJobResult, StatementSource, ImportJobStatus } from "@/types/transactions";

interface ImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SUPPORTED_BANKS = [
  { id: "revolut", name: "Revolut", icon: "R" },
  { id: "swedbank", name: "Swedbank LT", icon: "S" },
];

const MAX_POLLING_ATTEMPTS = 200;

export function ImportModal({ open, onOpenChange }: ImportModalProps) {
  const [step, setStep] = useState<"select" | "uploading" | "processing" | "result" | "error">("select");
  const [selectedBank, setSelectedBank] = useState<StatementSource | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [job, setJob] = useState<ImportJobResult | null>(null);
  const [jobStatus, setJobStatus] = useState<ImportJobStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const GENERIC_UPLOAD_FAILURE_MESSAGE = "Upload failed. Please try again.";

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        window.clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const startPollingJobStatus = (jobId: string) => {
    let attempts = 0;

    if (pollingIntervalRef.current) {
      window.clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = window.setInterval(async () => {
      try {
        attempts += 1;

        if (attempts > MAX_POLLING_ATTEMPTS) {
          if (pollingIntervalRef.current) {
            window.clearInterval(pollingIntervalRef.current);
          }
          setErrorMessage("Import is taking longer than expected. Please try again.");
          setStep("error");
          return;
        }

        const current = await statementImportAPI.getImportJobStatus(jobId);
        setJob(current);
        setJobStatus(current.import_job_status);

        if (current.import_job_status === "completed") {
          if (pollingIntervalRef.current) {
            window.clearInterval(pollingIntervalRef.current);
          }
          setStep("result");
        } else if (current.import_job_status === "failed") {
          if (pollingIntervalRef.current) {
            window.clearInterval(pollingIntervalRef.current);
          }
          setErrorMessage("Statement import failed. Please try again.");
          setStep("error");
        }
      } catch (error) {
        if (pollingIntervalRef.current) {
          window.clearInterval(pollingIntervalRef.current);
        }
        setErrorMessage("Failed to fetch import status");
        setStep("error");
      }
    }, 1500);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedBank || !selectedFile) return;

    setErrorMessage(null);
    setUploadProgress(0);
    setStep("uploading");

    // Fake upload progress for nicer UX while the real request runs
    let progress = 0;
    const uploadInterval = window.setInterval(() => {
      progress = Math.min(progress + 10, 95);
      setUploadProgress(progress);
    }, 150);

    try {
      const result = await statementImportAPI.uploadStatement(
        selectedFile,
        selectedBank,
      );

      window.clearInterval(uploadInterval);
      setUploadProgress(100);

      setJob(result);
      setJobStatus(result.import_job_status);
      setStep("processing");

      startPollingJobStatus(result.import_job_id);
    } catch (error) {
      window.clearInterval(uploadInterval);
      if (error instanceof ApiError) {
        setErrorMessage(error.message || GENERIC_UPLOAD_FAILURE_MESSAGE);
      } else if (error instanceof Error) {
        setErrorMessage(error.message || GENERIC_UPLOAD_FAILURE_MESSAGE);
      } else {
        setErrorMessage(GENERIC_UPLOAD_FAILURE_MESSAGE);
      }
      setStep("error");
    }
  };

  const reset = () => {
    setStep("select");
    setSelectedBank(null);
    setSelectedFile(null);
    setUploadProgress(0);
    setJob(null);
    setJobStatus(null);
    setErrorMessage(null);
    if (pollingIntervalRef.current) {
      window.clearInterval(pollingIntervalRef.current);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const effectiveStatus: ImportJobStatus | null = jobStatus ?? job?.import_job_status ?? null;

  const processingTitle =
    effectiveStatus === "pending"
      ? "Scheduling import..."
      : effectiveStatus === "running"
        ? "Parsing transactions..."
        : effectiveStatus === "failed"
          ? "Import failed"
          : "Processing statement...";

  return (
    <Dialog open={open} onOpenChange={(val) => {
      onOpenChange(val);
      if (!val) setTimeout(reset, 300);
    }}>
      <DialogContent className="sm:max-w-[440px] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Import Bank Statement</DialogTitle>
          <DialogDescription>
            Upload your bank statement to import transactions.
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
                      onClick={() =>
                        setSelectedBank(bank.id as StatementSource)
                      }
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
                    "border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center gap-2 transition-colors",
                    selectedBank
                      ? "cursor-pointer hover:bg-muted/30"
                      : "opacity-40 pointer-events-none",
                  )}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <Upload className="h-5 w-5 text-primary" />
                  </div>
                  <div className="text-sm font-medium text-center">
                    {selectedFile ? selectedFile.name : "Click to browse"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Statement file should be up to 2MB
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </div>
                <Button
                  className="w-full"
                  disabled={!selectedBank || !selectedFile}
                  onClick={handleUpload}
                >
                  Start import
                </Button>
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
                  {processingTitle}
                </h3>
                <p className="text-sm text-muted-foreground">
                  We are processing your statement
                </p>
              </div>
              <div className="flex items-center justify-center gap-2 text-xs font-mono text-muted-foreground bg-muted/50 py-2 px-4 rounded-full w-fit mx-auto border">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                Job ID: {job?.import_job_id.slice(0, 8)}...
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
                  <div className="text-2xl font-bold font-mono text-emerald-600">
                    {job?.imported_txn_count ?? 0}
                  </div>
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Imported</div>
                </div>
                <div className="space-y-1 border-l">
                  <div className="text-2xl font-bold font-mono text-amber-600">
                    {job?.duplicate_txn_count ?? 0}
                  </div>
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Duplicates</div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <Button className="w-full" onClick={() => onOpenChange(false)}>
                  Go to Transactions
                </Button>
                <Button
                  variant="ghost"
                  className="w-full text-xs"
                  onClick={reset}
                >
                  Import another statement
                </Button>
              </div>
            </div>
          )}

          {step === "error" && (
            <div className="space-y-6 text-center animate-in fade-in duration-300">
              <div className="h-16 w-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4 border border-red-200 dark:border-red-800">
                <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-foreground">
                  Import failed
                </h3>
                <p className="text-sm text-muted-foreground">
                  {errorMessage || "Your statement could not be processed."}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <Button className="w-full" onClick={reset}>
                  Try again
                </Button>
                <Button
                  variant="ghost"
                  className="w-full text-xs"
                  onClick={() => onOpenChange(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
