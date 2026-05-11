"use client";

import { useEffect, useRef, useState } from "react";
import { sendMessage } from "@/lib/api";
import ChatInput from "./ChatInput";
import MessageBubble, { Message } from "./MessageBubble";
import ThemeToggle from "./ThemeToggle";

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "agent",
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
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(text: string) {
    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const result = await sendMessage(text, sessionId);

      if (!sessionId) {
        setSessionId(result.session_id);
      }

      const agentMessage: Message = {
        id: generateId(),
        role: "agent",
        content: result.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      const errorMessage: Message = {
        id: generateId(),
        role: "error",
        content: err instanceof Error ? err.message : "An unexpected error occurred.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

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
          {/* Session indicator */}
          {sessionId && (
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-400 font-mono">
                {sessionId.slice(0, 8)}
              </span>
            </div>
          )}

          <ThemeToggle />
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto scrollbar-thin px-6 py-6 space-y-5 bg-gray-50 dark:bg-gray-950 transition-colors duration-200">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
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
