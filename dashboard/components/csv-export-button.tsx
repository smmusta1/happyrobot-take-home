"use client";

import { Download } from "lucide-react";
import { cn } from "@/lib/utils";

type Row = {
  id: number;
  mc_number: string | null;
  carrier_name: string | null;
  load_id: string | null;
  outcome: string | null;
  sentiment: string | null;
  final_rate: string | null;
  posted_rate: string | null;
  rounds_used: number | null;
  agreement_reached: boolean | null;
  created_at: string;
};

const HEADERS = [
  "id",
  "created_at",
  "mc_number",
  "carrier_name",
  "load_id",
  "outcome",
  "sentiment",
  "posted_rate",
  "final_rate",
  "rounds_used",
  "agreement_reached",
] as const;

function escapeCsv(v: unknown): string {
  if (v === null || v === undefined) return "";
  const s = String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function CsvExportButton({
  rows,
  className,
}: {
  rows: Row[];
  className?: string;
}) {
  function handleClick() {
    const lines = [HEADERS.join(",")];
    for (const r of rows) {
      lines.push(HEADERS.map((h) => escapeCsv(r[h as keyof Row])).join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const stamp = new Date().toISOString().slice(0, 10);
    a.download = `calls-${stamp}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={rows.length === 0}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border bg-background px-3 py-1.5 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
    >
      <Download className="h-3.5 w-3.5" />
      Export CSV
    </button>
  );
}
