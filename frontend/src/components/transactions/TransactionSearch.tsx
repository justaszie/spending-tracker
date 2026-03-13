import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface TransactionSearchProps {
  value: string;
  onSearchChange: (value: string) => void;
  debounceMs?: number;
}

export function TransactionSearch({
  value,
  onSearchChange,
  debounceMs = 200,
}: TransactionSearchProps) {
  const [localValue, setLocalValue] = useState(value);

  // Keep local input in sync if parent value changes externally
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounce propagating changes to the parent
  useEffect(() => {
    const debounceTimeout = setTimeout(() => {
      if (localValue !== value) {
        onSearchChange(localValue);
      }
    }, debounceMs);

    return () => clearTimeout(debounceTimeout);
  }, [localValue, value, onSearchChange, debounceMs]);

  return (
    <div className="relative w-full sm:w-72">
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input
        type="search"
        placeholder="Search transactions..."
        className="pl-9 bg-card"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
      />
    </div>
  );
}

