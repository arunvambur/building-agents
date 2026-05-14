"use client";

import { useRef, useState, KeyboardEvent, useCallback } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const resizeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const handleInput = useCallback(() => {
    if (resizeTimerRef.current) clearTimeout(resizeTimerRef.current);
    resizeTimerRef.current = setTimeout(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }, 40);
  }, []);

  return (
    <div className="
      flex items-end gap-3 px-4 py-3 rounded-2xl shadow-sm
      bg-gray-100 dark:bg-gray-900
      border border-gray-300 dark:border-gray-700/60
      focus-within:border-brand-500 dark:focus-within:border-brand-500
      transition-colors duration-200
    ">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder="Ask about hotels, charts, or visualizations..."
        className="
          flex-1 resize-none bg-transparent outline-none leading-relaxed scrollbar-thin
          text-sm text-gray-900 dark:text-gray-100
          placeholder-gray-400 dark:placeholder-gray-500
          disabled:opacity-50
        "
      />

      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="
          flex-shrink-0 flex items-center justify-center
          w-9 h-9 rounded-xl
          bg-brand-500 hover:bg-brand-600 active:bg-brand-700
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-colors
        "
      >
        {disabled ? (
          <svg className="w-4 h-4 animate-spin text-white" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        )}
      </button>
    </div>
  );
}
