"use client";

import { useEffect, useState } from "react";
import FileCard from "./FileCard";

export type Role = "user" | "agent" | "error";
export type ContentType = "text" | "image" | "file";

export interface Message {
  id: string;
  role: Role;
  content: string;
  contentType: ContentType;
  filename?: string;
  fileFormat?: string;
  timestamp: Date;
}

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const isError = message.role === "error";
  const [time, setTime] = useState("");

  useEffect(() => {
    setTime(message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
  }, [message.timestamp]);

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex flex-col gap-1 ${isUser ? "items-end max-w-[75%]" : "items-start max-w-[85%]"}`}>

        <span className="text-xs text-gray-400 dark:text-gray-500 px-1">
          {isUser ? "You" : "Viz Agent"}{time ? ` \u00b7 ${time}` : ""}
        </span>

        {/* Image response */}
        {!isUser && message.contentType === "image" && (
          <div className="rounded-2xl rounded-tl-sm overflow-hidden border border-gray-200 dark:border-gray-700 shadow-md">
            <img
              src={`data:image/png;base64,${message.content}`}
              alt="Generated chart"
              className="max-w-full block"
            />
          </div>
        )}

        {/* File download response — excel / pdf / ppt */}
        {!isUser && message.contentType === "file" && (
          <div className="w-80">
            <FileCard
              downloadUrl={message.content}
              filename={message.filename || "report"}
              fileFormat={message.fileFormat}
            />
          </div>
        )}

        {/* Text / error / user bubble */}
        {(isUser || message.contentType === "text" || isError) && (
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

      </div>
    </div>
  );
}
