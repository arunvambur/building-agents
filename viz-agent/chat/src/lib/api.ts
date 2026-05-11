const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface VisualizeRequest {
  message: string;
  session_id?: string;
}

export type ResponseType = "text" | "image" | "file";

export interface VisualizeResponse {
  session_id: string;
  type: ResponseType;
  content: string;       // base64 PNG | /download/<id> URL | plain text
  filename?: string;
}

export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<VisualizeResponse> {
  const body: VisualizeRequest = { message, session_id: sessionId };

  const res = await fetch(`${API_BASE}/visualize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<VisualizeResponse>;
}
