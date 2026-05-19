"use client";

import { useEffect, useState } from "react";
import { parseTableContent } from "@/lib/table";
import DataTable from "./DataTable";
import FileCard from "./FileCard";
import MapCard from "./MapCard";

export type Role = "user" | "agent" | "error";
export type ContentType = "text" | "image" | "file" | "table";

export interface Message {
  id: string;
  role: Role;
  content: string;
  contentType: ContentType;
  filename?: string;
  fileFormat?: string;
  // Table data
  headers?: string[];
  rows?: string[][];
  rowCount?: number;
  timestamp: Date;
}

interface Props {
  message: Message;
  onRetry?: () => void;
}

export default function MessageBubble({ message, onRetry }: Props) {
  const isUser  = message.role === "user";
  const isError = message.role === "error";
  const isMap   = !isUser && message.contentType === "file" && message.fileFormat === "map";
  const [time, setTime] = useState("");
  const parsedTable = !isUser && message.contentType === "text"
    ? parseTableContent(message.content)
    : null;
  const tableHeaders = message.contentType === "table" ? message.headers : parsedTable?.headers;
  const tableRows = message.contentType === "table" ? message.rows : parsedTable?.rows;
  const tableRowCount = message.contentType === "table"
    ? message.rowCount
    : parsedTable?.row_count;

  useEffect(() => {
    setTime(message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
  }, [message.timestamp]);

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex flex-col gap-1 ${isUser ? "items-end max-w-[75%]" : "items-start w-full max-w-[95%]"}`}>

        <span className="text-xs text-gray-400 dark:text-gray-500 px-1">
          {isUser ? "You" : "Viz Agent"}{time ? ` \u00b7 ${time}` : ""}
        </span>

        {/* Inline PNG chart */}
        {!isUser && message.contentType === "image" && (
          <div className="rounded-2xl rounded-tl-sm overflow-hidden border border-gray-200 dark:border-gray-700 shadow-md">
            <img
              src={`data:image/png;base64,${message.content}`}
              alt="Generated chart"
              className="max-w-full block"
            />
          </div>
        )}

        {/* Interactive map (iframe) */}
        {isMap && (
          <div className="w-full">
            <MapCard
              downloadUrl={message.content}
              filename={message.filename || "map.html"}
            />
          </div>
        )}

        {/* Tabular data */}
        {!isUser && tableHeaders && tableRows && (
          <div className="w-full">
            <DataTable
              headers={tableHeaders}
              rows={tableRows}
              rowCount={tableRowCount ?? tableRows.length}
            />
          </div>
        )}

        {/* File download — excel / pdf / ppt / csv (not map — handled above) */}
        {!isUser && message.contentType === "file" && !isMap && (
          <div className="w-80">
            <FileCard
              downloadUrl={message.content}
              filename={message.filename || "report"}
              fileFormat={message.fileFormat}
            />
          </div>
        )}

        {/* Text / error / user bubble */}
        {(isUser || (message.contentType === "text" && !parsedTable) || isError) && (
          <div
            className={`
              rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words
              ${isUser
                ? "bg-brand-500 text-white rounded-tr-sm"
                : isError
                ? "bg-red-100 dark:bg-red-900/60 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-700/50 rounded-tl-sm"
                : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700/50 rounded-tl-sm shadow-sm"
              }
            `}
          >
            {message.content}
          </div>
        )}

        {/* Retry button on error bubbles */}
        {isError && onRetry && (
          <button
            onClick={onRetry}
            className="
              flex items-center gap-1.5 mt-0.5 px-3 py-1.5 rounded-lg text-xs font-medium
              text-red-600 dark:text-red-400
              border border-red-300 dark:border-red-700/50
              hover:bg-red-50 dark:hover:bg-red-900/30
              transition-colors
            "
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 .49-3.5" />
            </svg>
            Retry
          </button>
        )}

      </div>
    </div>
  );
}
