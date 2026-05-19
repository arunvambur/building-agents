"use client";

import { useState } from "react";

// Use the Next.js API proxy — same base as api.ts and FileCard.tsx.
// This ensures map iframes and full-screen links work correctly behind
// any reverse proxy or in production without hardcoding the backend URL.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

interface Props {
  downloadUrl: string;   // /download/<file_id>
  filename: string;
}

export default function MapCard({ downloadUrl, filename }: Props) {
  const src = `${API_BASE}${downloadUrl}`;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="flex flex-col gap-2 w-full">
      {/* Inline iframe map */}
      <div
        className={`
          rounded-2xl rounded-tl-sm overflow-hidden border border-gray-200
          dark:border-gray-700 shadow-md transition-all duration-300
          ${expanded ? "h-[520px]" : "h-72"}
        `}
      >
        <iframe
          src={src}
          title="Hotel Map"
          className="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin"
        />
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between px-1">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="
            flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
            text-gray-600 dark:text-gray-400
            border border-gray-200 dark:border-gray-700
            hover:border-brand-500 hover:text-brand-600 dark:hover:text-brand-400
            transition-colors
          "
        >
          {expanded ? (
            <>
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="4 14 10 14 10 20" />
                <polyline points="20 10 14 10 14 4" />
                <line x1="10" y1="14" x2="3" y2="21" />
                <line x1="21" y1="3" x2="14" y2="10" />
              </svg>
              Collapse
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 3 21 3 21 9" />
                <polyline points="9 21 3 21 3 15" />
                <line x1="21" y1="3" x2="14" y2="10" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
              Expand map
            </>
          )}
        </button>

        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
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
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          Open full screen
        </a>
      </div>
    </div>
  );
}
