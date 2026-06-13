import { format } from "date-fns";
import type { Transaction } from "@/types/transactions";

const NOTE_MAX_LENGTH = 40;

const amountFormatter = new Intl.NumberFormat("de-DE", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export type CompactTransaction = {
  primary: string;
  secondary: string;
};

export function formatCompactTransaction(
  transaction: Transaction,
): CompactTransaction {
  const sign = transaction.side === "credit" ? "+" : "-";
  const amount = amountFormatter.format(Number(transaction.orig_amount));
  const primary = `${transaction.counterparty}  ${sign}${amount} ${transaction.orig_currency}`;

  const datetime = format(
    new Date(transaction.transaction_datetime),
    "dd MMM yyyy HH:mm",
  );
  const note = transaction.note?.trim();
  const secondary = note
    ? `${datetime} · "${truncateNote(note)}"`
    : datetime;

  return { primary, secondary };
}

function truncateNote(note: string): string {
  if (note.length <= NOTE_MAX_LENGTH) return note;
  return `${note.slice(0, NOTE_MAX_LENGTH - 1).trimEnd()}…`;
}
