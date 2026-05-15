"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { sendMessage } from "@/lib/api";
import ChatInput from "./ChatInput";
import MessageBubble, { Message } from "./MessageBubble";
import ThemeToggle from "./ThemeToggle";

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "agent",
  contentType: "text",
  content:
    "Hello! I am the Viz Agent. Ask me to query hotel data or generate visualizations — for example:\n\n" +
    "- Show me a bar chart of hotel ratings by town\n" +
    "- Which hotels in St Ives have available rooms?\n" +
    "- Generate an Excel report of all hotels with pricing",
  timestamp: new Date(),
};

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [lastUserText, setLastUserText] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async (text: string) => {
    // Abort any in-flight request before starting a new one
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLastUserText(text);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      contentType: "text",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const result = await sendMessage(text, sessionId, abortRef.current.signal);

      if (!sessionId) {
        setSessionId(result.session_id);
      }

      const agentMessage: Message = {
        id: crypto.randomUUID(),
        role: "agent",
        contentType: result.type,
        content: result.content,
        filename: result.filename,
        fileFormat: result.file_format,
        headers: result.headers,
        rows: result.rows,
        rowCount: result.row_count,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      // Ignore abort errors caused by the user sending a new message
      if (err instanceof Error && err.name === "AbortError") return;

      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "error",
        contentType: "text",
        content: err instanceof Error ? err.message : "An unexpected error occurred.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleRetry = useCallback(() => {
    if (!lastUserText) return;
    // Remove the last error message before retrying
    setMessages((prev) => {
      const lastIdx = [...prev].reverse().findIndex((m) => m.role === "error");
      if (lastIdx === -1) return prev;
      const removeIdx = prev.length - 1 - lastIdx;
      return prev.filter((_, i) => i !== removeIdx);
    });
    handleSend(lastUserText);
  }, [lastUserText, handleSend]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-950 transition-colors duration-200">

      {/* Header */}
      <header className="flex-shrink-0 flex items-center gap-3 px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 transition-colors duration-200">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500">
          <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 3h18v2H3V3zm0 4h12v2H3V7zm0 4h18v2H3v-2zm0 4h12v2H3v-2zm0 4h18v2H3v-2z" />
          </svg>
        </div>
        <div>
          <h1 className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-none">Viz Agent</h1>
          <p className="text-xs text-gray-500 mt-0.5">Data visualization assistant</p>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {sessionId && (
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-400 font-mono">{sessionId.slice(0, 8)}</span>
            </div>
          )}
          <ThemeToggle />
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto scrollbar-thin px-6 py-6 space-y-5 bg-gray-50 dark:bg-gray-950 transition-colors duration-200">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onRetry={msg.role === "error" ? handleRetry : undefined}
          />
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/50 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* Input */}
      <footer className="flex-shrink-0 px-6 py-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 transition-colors duration-200">
        <ChatInput onSend={handleSend} disabled={loading} />
        <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-2">
          Press Enter to send &middot; Shift+Enter for new line
        </p>
      </footer>
    </div>
  );
}
