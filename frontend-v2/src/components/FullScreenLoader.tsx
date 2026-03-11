import type { FC } from "react";

type FullScreenLoaderProps = {
  open: boolean;
  label?: string;
};

export const FullScreenLoader: FC<FullScreenLoaderProps> = ({ open, label }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-3">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        {label ? <p className="text-sm text-muted-foreground">{label}</p> : null}
      </div>
    </div>
  );
};

