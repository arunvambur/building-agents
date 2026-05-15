const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REQUEST_TIMEOUT_MS = 120_000; // 2 minutes — LLM calls can be slow

export interface VisualizeRequest {
  message: string;
  session_id?: string;
}

export type ResponseType = "text" | "image" | "file" | "table";

export interface VisualizeResponse {
  session_id: string;
  type: ResponseType;
  content: string;        // base64 PNG | /download/<id> URL | plain text | "" for table
  filename?: string;
  file_format?: string;   // "excel" | "pdf" | "ppt" | "csv"
  // Populated when type === "table"
  headers?: string[];
  rows?: string[][];
  row_count?: number;
}

export async function sendMessage(
  message: string,
  sessionId?: string,
  signal?: AbortSignal,
): Promise<VisualizeResponse> {
  const body: VisualizeRequest = { message, session_id: sessionId };

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const mergedSignal = signal
    ? anySignal([signal, controller.signal])
    : controller.signal;

  try {
    const res = await fetch(`${API_BASE}/visualize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: mergedSignal,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API error ${res.status}: ${text}`);
    }

    return res.json() as Promise<VisualizeResponse>;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Request timed out. The server is taking too long to respond.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort();
      break;
    }
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return controller.signal;
}
