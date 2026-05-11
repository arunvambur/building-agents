"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  downloadUrl: string;   // e.g. /download/<file_id>
  filename: string;
}

export default function FileCard({ downloadUrl, filename }: Props) {
  const href = `${API_BASE}${downloadUrl}`;

  return (
    <a
      href={href}
      download={filename}
      target="_blank"
      rel="noopener noreferrer"
      className="
        flex items-center gap-3 px-4 py-3 rounded-xl
        bg-white dark:bg-gray-900
        border border-gray-200 dark:border-gray-700
        hover:border-brand-500 dark:hover:border-brand-500
        shadow-sm hover:shadow-md
        transition-all group no-underline
      "
    >
      {/* Excel file icon */}
      <div className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-lg bg-green-100 dark:bg-green-900/40">
        <svg className="w-5 h-5 text-green-600 dark:text-green-400" viewBox="0 0 24 24" fill="currentColor">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM8.5 19l-2-3h1.2l1.3 2 1.3-2h1.2l-2 3H8.5zm3.5 0v-3h1v3h-1zm2.5 0v-3h1.8c.8 0 1.2.4 1.2 1s-.3.8-.7.9c.5.1.8.5.8 1 0 .7-.5 1.1-1.4 1.1H14.5zm1-1.7h.7c.3 0 .5-.1.5-.4s-.2-.4-.5-.4h-.7v.8zm0 1.3h.8c.3 0 .5-.1.5-.4s-.2-.4-.6-.4h-.7v.8z"/>
        </svg>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{filename}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">Excel spreadsheet &middot; Click to download</p>
      </div>

      {/* Download arrow */}
      <svg
        className="w-4 h-4 text-gray-400 group-hover:text-brand-500 transition-colors flex-shrink-0"
        viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
    </a>
  );
}
