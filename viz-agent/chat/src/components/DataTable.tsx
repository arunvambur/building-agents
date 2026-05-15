"use client";

import { useState, useMemo } from "react";

interface Props {
  headers: string[];
  rows: string[][];
  rowCount: number;
}

type SortDir = "asc" | "desc" | null;

function downloadCsv(headers: string[], rows: string[][]): void {
  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const lines = [
    headers.map(escape).join(","),
    ...rows.map((r) => r.map(escape).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "cornwall_hotels.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function DataTable({ headers, rows, rowCount }: Props) {
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  const sortedRows = useMemo(() => {
    if (sortCol === null || sortDir === null) return rows;
    return [...rows].sort((a, b) => {
      const av = a[sortCol] ?? "";
      const bv = b[sortCol] ?? "";
      // Numeric sort if both values are numbers
      const an = parseFloat(av);
      const bn = parseFloat(bv);
      const cmp = !isNaN(an) && !isNaN(bn)
        ? an - bn
        : av.localeCompare(bv);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortCol, sortDir]);

  function handleSort(colIdx: number) {
    if (sortCol !== colIdx) {
      setSortCol(colIdx);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSortCol(null);
      setSortDir(null);
    }
  }

  function SortIcon({ colIdx }: { colIdx: number }) {
    if (sortCol !== colIdx) {
      return (
        <svg className="w-3 h-3 opacity-30" viewBox="0 0 24 24" fill="currentColor">
          <path d="M7 10l5-5 5 5H7zm0 4l5 5 5-5H7z" />
        </svg>
      );
    }
    return sortDir === "asc" ? (
      <svg className="w-3 h-3 text-brand-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M7 14l5-5 5 5H7z" />
      </svg>
    ) : (
      <svg className="w-3 h-3 text-brand-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M7 10l5 5 5-5H7z" />
      </svg>
    );
  }

  return (
    <div className="flex flex-col gap-2 w-full">
      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-brand-500">
              {headers.map((h, i) => (
                <th
                  key={i}
                  onClick={() => handleSort(i)}
                  className="
                    px-3 py-2.5 text-left font-semibold text-white
                    cursor-pointer select-none whitespace-nowrap
                    hover:bg-brand-600 transition-colors
                  "
                >
                  <span className="flex items-center gap-1.5">
                    {h}
                    <SortIcon colIdx={i} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, ri) => (
              <tr
                key={ri}
                className={`
                  border-t border-gray-100 dark:border-gray-800
                  ${ri % 2 === 0
                    ? "bg-white dark:bg-gray-900"
                    : "bg-gray-50 dark:bg-gray-800/60"
                  }
                  hover:bg-brand-50 dark:hover:bg-gray-700/50 transition-colors
                `}
              >
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className="px-3 py-2 text-gray-700 dark:text-gray-300 whitespace-nowrap"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer — row count + CSV download */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {rowCount} record{rowCount !== 1 ? "s" : ""}
        </span>
        <button
          onClick={() => downloadCsv(headers, rows)}
          className="
            flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
            text-gray-600 dark:text-gray-400
            border border-gray-200 dark:border-gray-700
            hover:border-brand-500 hover:text-brand-600 dark:hover:text-brand-400
            transition-colors
          "
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download CSV
        </button>
      </div>
    </div>
  );
}
